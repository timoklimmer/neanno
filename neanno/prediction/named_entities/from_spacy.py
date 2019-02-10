import pathlib
import random

import spacy
from PyQt5.QtCore import QThreadPool
from spacy.util import compounding, minibatch

from neanno.prediction.predictor import Predictor
from neanno.utils.text import (
    extract_annotations_for_spacy_ner,
    mask_annotations,
    replace_from_to,
)
from neanno.utils.threading import ParallelWorker


class FromSpacyNamedEntitiesPredictor(Predictor):
    """ Trains and uses a spacy model to predict named entities. """

    source_model = None
    target_model_directory = None
    target_model_name = None
    spacy_model = None
    threadpool = QThreadPool()

    def __init__(self, predictor_config):
        super().__init__(predictor_config)
        self.source_model = predictor_config["source_model"]
        if "target_model_directory" in predictor_config:
            self.target_model_directory = predictor_config["target_model_directory"]
        if "target_model_name" in predictor_config:
            self.target_model_name = predictor_config["target_model_name"]
        self.spacy_model = (
            spacy.blank(self.source_model.replace("blank:", "", 1))
            if self.source_model.startswith("blank:")
            else spacy.load(self.source_model)
        )

    def learn_from_annotated_dataset(
        self, dataset, text_column, is_annotated_column, entity_codes_to_train
    ):
        # ensure and get the ner pipe
        if "ner" not in self.spacy_model.pipe_names:
            self.spacy_model.add_pipe(self.spacy_model.create_pipe("ner"), last=True)
        ner = self.spacy_model.get_pipe("ner")
        # ensure we have all relevant named entities in the model
        for entity_code_to_train in entity_codes_to_train:
            ner.add_label(entity_code_to_train)
        # prepare the training set
        trainset = (
            dataset[dataset[is_annotated_column] == True][text_column]
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
        if self.target_model_directory is not None:
            output_dir = pathlib.Path(self.target_model_directory)
            print()
            if not output_dir.exists():
                output_dir.mkdir()
            self.spacy_model.meta["name"] = self.target_model_name
            self.spacy_model.to_disk(output_dir)
            print(
                "Saved model to folder '{}'. Enjoy your new model!".format(output_dir)
            )

        # compute precision/recall for each entity code
        # TODO: dataset might have changed meanwhile, need to use a frozen dataset for evaluation
        # TODO: consider using a common eval, not only in this class
        # TODO: think about if this is the right place (esp. for on-the-fly training)
        # use compute_ner_metrics_from_actual_predicted_columns() function from neanno.utils.metrics

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
