import pathlib
import random

import pandas as pd
import spacy
import yaml
from sklearn.model_selection import train_test_split
from spacy.util import compounding, minibatch

from neanno.prediction.predictor import Predictor
from neanno.utils.metrics import (
    compute_ner_metrics_from_actual_predicted_annotated_text_columns,
)
from neanno.utils.text import (
    extract_annotations_for_spacy_ner,
    remove_all_annotations_from_text,
    replace_from_to,
)


class FromSpacyNamedEntitiesPredictor(Predictor):
    """ Trains and uses a spacy model to predict named entities. """

    source_model = None
    target_model_directory = None
    target_model_name = None
    spacy_model = None

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

    @property
    def config_validation_schema_custom_part(self):
        return yaml.load(
            """
            source_model:
                type: string
                required: True
            target_model_directory:
                type: string
                required: False
            target_model_name:
                type: string
                required: False
            """,
            Loader=yaml.FullLoader,
        )

    def learn_from_annotated_dataset(
        self,
        dataset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        # ensure and get the ner pipe from the spacy model
        if "ner" not in self.spacy_model.pipe_names:
            self.spacy_model.add_pipe(self.spacy_model.create_pipe("ner"), last=True)
        ner_pipe = self.spacy_model.get_pipe("ner")
        # ensure we have all relevant named entities in the model
        for entity_code_to_train in entity_codes_to_train:
            ner_pipe.add_label(entity_code_to_train)
        # prepare training and test set
        annotated_data = dataset[dataset[is_annotated_column] == True]
        trainset, testset = train_test_split(annotated_data, test_size=0.3)
        trainset_for_spacy = (
            trainset[text_column]
            .map(
                lambda annotated_text: extract_annotations_for_spacy_ner(
                    annotated_text, entity_codes_to_train
                )
            )
            .tolist()
        )

        # do the training
        # note: there is certainly room for improvement, maybe switching to spacy's CLI
        #       which seems the recommendation by the spacy authors
        signals.message.emit(
            "Training NER model with predictor '{}'...".format(self.name)
        )
        n_iterations = 10
        # note: this removes the unnamed vectors warning, TBD if needs changes
        self.spacy_model.vocab.vectors.name = "spacy_pretrained_vectors"
        optimizer = self.spacy_model.begin_training()
        other_pipes = [pipe for pipe in self.spacy_model.pipe_names if pipe != "ner"]
        with self.spacy_model.disable_pipes(*other_pipes):
            for iteration in range(n_iterations):
                random.shuffle(trainset_for_spacy)
                losses = {}
                batches = minibatch(
                    trainset_for_spacy, size=compounding(4.0, 32.0, 1.001)
                )
                for batch in batches:
                    texts, annotations = zip(*batch)
                    self.spacy_model.update(
                        texts, annotations, sgd=optimizer, drop=0.35, losses=losses
                    )
                signals.message.emit("Iteration: {}...".format(iteration))

        # compute precision/recall values
        signals.message.emit("Computing precision/recall matrix...")
        signals.message.emit("Note: the eval algorithm currently tests on strict positions, hence precision/recall are low although performance is good. needs rework to better reflect reality.")

        def predict_annotations(text, language):
            return self.predict_inline_annotations(
                remove_all_annotations_from_text(text), language
            )

        actual_annotations = testset[text_column]
        predicted_annotations = testset.apply(
            lambda row: (
                predict_annotations(
                    row[text_column],
                    row[language_column] if language_column else "en-US",
                )
            ),
            axis=1,
        )
        ner_metrics = compute_ner_metrics_from_actual_predicted_annotated_text_columns(
            actual_annotations, predicted_annotations, entity_codes_to_train
        )
        signals.message.emit(pd.DataFrame(ner_metrics).T.to_string())

        # save model to output directory
        if self.target_model_directory is not None:
            output_dir = pathlib.Path(self.target_model_directory)
            signals.message.emit("Saving model to folder '{}'...".format(output_dir))
            if not output_dir.exists():
                output_dir.mkdir()
            self.spacy_model.meta["name"] = self.target_model_name
            self.spacy_model.to_disk(output_dir)

    def predict_inline_annotations(self, text, language="en-US"):
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
            return result
