import pathlib
import random
import spacy
from spacy.util import compounding, minibatch
from neanno.utils.text import (
    extract_annotations_for_spacy_ner,
    mask_annotations,
    replace_from_to,
)
from neanno.utils.threading import ParallelWorker
from PyQt5.QtCore import QThreadPool


class NamedEntitiesFromSpacyPredictor:
    """ Trains and uses a spacy model to predict named entities. """

    configured_named_entities = None
    model_source = None
    dataset = None
    text_column = None
    is_annotated_column = None
    model_target = None
    model_target_name = None
    spacy_model = None
    threadpool = QThreadPool()

    def __init__(
        self,
        configured_named_entities,
        model_source,
        text_column,
        is_annotated_column,
        model_target,
        model_target_name,
    ):
        self.configured_named_entities = configured_named_entities
        self.model_source = model_source
        self.text_column = text_column
        self.is_annotated_column = is_annotated_column
        self.model_target = model_target
        self.model_target_name = model_target_name
        self.spacy_model = (
            spacy.blank(model_source.replace("blank:", "", 1))
            if model_source.startswith("blank:")
            else spacy.load(model_source)
        )

    def learn_from_annotated_dataset(self, dataset):
        # ensure and get the ner pipe
        if "ner" not in self.spacy_model.pipe_names:
            self.spacy_model.add_pipe(self.spacy_model.create_pipe("ner"), last=True)
        ner = self.spacy_model.get_pipe("ner")
        # ensure we have all configured named entities also configured in the model
        for configured_named_entity in self.configured_named_entities:
            ner.add_label(configured_named_entity.code)
        # prepare the training set
        entity_codes_to_train = [
            configured_named_entity.code
            for configured_named_entity in self.configured_named_entities
        ]
        trainset = (
            dataset[dataset[self.is_annotated_column] == True][self.text_column]
            .map(
                lambda annotated_text: extract_annotations_for_spacy_ner(
                    annotated_text, entity_codes_to_train
                )
            )
            .tolist()
        )
        # do the training (in a parallel thread to avoid blocking the GUI)
        model_trainer = ParallelWorker(self.train_model, trainset)
        model_trainer.signals.message.connect(self.train_model_message)
        model_trainer.signals.success.connect(self.train_model_succeeded)
        model_trainer.signals.failure.connect(self.train_model_failed)
        # model_trainer.signals.finished.connect(self.thread_complete)
        # model_trainer.signals.progress.connect(self.progress_fn)
        self.threadpool.start(model_trainer)

    def train_model(self, trainset, progress_callback, message_callback):
        # note: there is certainly room for improvement, maybe switching to spacy's CLI
        #       which seems the recommendation by the spacy authors
        message_callback.emit("Training NER model...")
        n_iter = 10
        # note: this removes the unnamed vectors warning, TBD if needs changes
        self.spacy_model.vocab.vectors.name = "spacy_pretrained_vectors"
        optimizer = self.spacy_model.begin_training()
        other_pipes = [pipe for pipe in self.spacy_model.pipe_names if pipe != "ner"]
        with self.spacy_model.disable_pipes(*other_pipes):
            for itn in range(n_iter):
                random.shuffle(trainset)
                losses = {}
                batches = minibatch(trainset, size=compounding(4.0, 32.0, 1.001))
                for batch in batches:
                    texts, annotations = zip(*batch)
                    self.spacy_model.update(
                        texts, annotations, sgd=optimizer, drop=0.35, losses=losses
                    )
                message_callback.emit("Iteration: {}, losses: {}".format(itn, losses))

    def train_model_message(self, message):
        print(message)

    def train_model_succeeded(self, result):
        print("NER model training succeeded!")
        # save model to output directory
        if self.model_target is not None:
            output_dir = pathlib.Path(self.model_target)
            print()
            if not output_dir.exists():
                output_dir.mkdir()
            self.spacy_model.meta["name"] = self.model_target_name
            self.spacy_model.to_disk(output_dir)
            print(
                "Saved model to folder '{}'. Enjoy your new model!".format(output_dir)
            )

        # test the trained model
        # TODO: complete, precision/recall statistics
        # test_text = "Guten Morgen, bei uns gibt es heute Bifteki mit Schafkäsesoße, dazu Reis und Salat. Schönen Freitag,"
        # doc = self.spacy_model(test_text)
        # print("Entities in '%s'" % test_text)
        # for ent in doc.ents:
        #    print(ent.label_, ent.text)

    def train_model_failed(self, exception_info):
        print("NER model training failed.")
        print(exception_info[0])
        print(exception_info[1])
        print(exception_info[2])

    def predict_inline_annotations(self, text, mask_annotations_before_return=False):
        if self.spacy_model:
            # TODO: add parent terms
            result = text
            doc = self.spacy_model(result)
            shift = 0
            for ent in doc.ents:
                print("NER model predicted: {} {}".format(ent.label_, ent.text))
                old_result_length = len(result)
                result = replace_from_to(
                    result,
                    ent.start_char + shift,
                    ent.end_char + shift,
                    "`{}``SN``{}`´".format(ent.text, ent.label_),
                )
                shift += len(result) - old_result_length
            if mask_annotations_before_return:
                result = mask_annotations(result)
            return result
