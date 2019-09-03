import pathlib

import pandas as pd
import spacy
import yaml
from spacy.util import compounding, minibatch

from neanno.prediction.predictor import Predictor
from neanno.utils.list import is_majority_of_last_n_items_decreasing
from neanno.utils.metrics import compute_category_metrics
from neanno.utils.signals import *
from neanno.utils.text import remove_all_annotations_from_text


class FromSpacyCategoriesPredictor(Predictor):
    """ Trains and uses a spacy model to predict text categories. """

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
    def supports_online_training(self):
        return False

    @property
    def supports_batch_training(self):
        return True

    @property
    def project_config_validation_schema_custom_part(self):
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

    def train_from_trainset(
        self,
        trainset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        """ Trains the model from the given trainset."""

        # ensure and get the textcat pipe from the spacy model
        if "textcat" not in self.spacy_model.pipe_names:
            textcat_pipe = self.spacy_model.create_pipe("textcat")
            self.spacy_model.add_pipe(textcat_pipe, last=True)
        textcat_pipe = self.spacy_model.get_pipe("textcat")
        # ensure we have all categories in the model
        for category_to_train in categories_to_train:
            textcat_pipe.add_label(category_to_train)
        # prepare trainset for spacy
        trainset_for_spacy = trainset.apply(
            lambda row: (
                row[text_column],
                {
                    "cats": {
                        category: category in row[categories_column].split("|")
                        for category in categories_to_train
                    }
                },
            ),
            axis=1,
        ).tolist()
        # do the training
        # note: there is certainly room for improvement, maybe switching to spacy's CLI
        #       which seems the recommendation by the spacy authors
        emit_sub_header(self.name, signals)
        start_time = emit_start_time(signals)

        max_iterations = 100
        other_pipes = [
            pipe for pipe in self.spacy_model.pipe_names if pipe != "textcat"
        ]
        iteration_losses = []
        with self.spacy_model.disable_pipes(*other_pipes):
            optimizer = self.spacy_model.begin_training()
            for iteration in range(max_iterations):
                emit_partial_message("Iteration {}...".format(iteration), signals)
                losses = {}
                batches = minibatch(
                    trainset_for_spacy, size=compounding(4.0, 32.0, 1.001)
                )
                for batch in batches:
                    texts, annotations = zip(*batch)
                    self.spacy_model.update(
                        texts, annotations, sgd=optimizer, drop=0.2, losses=losses
                    )
                iteration_loss = losses["textcat"]
                emit_message(" => loss: {}".format(iteration_loss), signals)

                # stop training when the majority of the last {last_iterations_window_size} trainings did not decrease
                iteration_losses.append(iteration_loss)
                last_iterations_window_size = 7
                if len(iteration_losses) > (
                    last_iterations_window_size + 1
                ) and not is_majority_of_last_n_items_decreasing(
                    iteration_losses, last_iterations_window_size
                ):
                    break

        # save model to output directory
        if self.target_model_directory is not None:
            output_dir = pathlib.Path(self.target_model_directory)
            emit_message("Saving model to folder '{}'...".format(output_dir), signals)
            if not output_dir.exists():
                output_dir.mkdir()
            self.spacy_model.meta["name"] = self.target_model_name
            self.spacy_model.to_disk(output_dir)

        # compute and tell training times
        emit_end_time_duration(start_time, "Training", signals)

        # emit a new line to improve readability of output
        emit_new_line(signals)

    def predict_text_categories(self, text, language="en-US"):
        """Predicts the text categories of the given text."""

        if self.spacy_model:
            doc = self.spacy_model(remove_all_annotations_from_text(text))
            return [
                category for category in doc.cats.keys() if doc.cats[category] >= 0.5
            ]
        else:
            return []

    def test_model(
        self,
        testset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        """Tests the model using the given testset."""

        # inform about this predictor
        emit_sub_header(self.name, signals)

        # compute precision/recall values
        actual_categories_series = testset[categories_column]
        predicted_categories_series = testset.apply(
            lambda row: (
                "|".join(
                    self.predict_text_categories(
                        row[text_column],
                        row[language_column] if language_column else "en-US",
                    )
                )
            ),
            axis=1,
        )
        category_metrics = compute_category_metrics(
            actual_categories_series, predicted_categories_series, categories_to_train
        )

        # emit result
        emit_message(pd.DataFrame(category_metrics).T.to_string(), signals)

        # emit a new line to improve readability of output
        emit_new_line(signals)
