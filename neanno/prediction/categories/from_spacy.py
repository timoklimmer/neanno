import pathlib

import pandas as pd
import spacy
import yaml
from sklearn.model_selection import train_test_split
from spacy.util import compounding, minibatch

from neanno.prediction.predictor import Predictor
from neanno.utils.metrics import compute_category_metrics
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
        # ensure and get the textcat pipe from the spacy model
        if "textcat" not in self.spacy_model.pipe_names:
            textcat_pipe = self.spacy_model.create_pipe("textcat")
            self.spacy_model.add_pipe(textcat_pipe, last=True)
        textcat_pipe = self.spacy_model.get_pipe("textcat")
        # ensure we have all categories in the model
        for category_to_train in categories_to_train:
            textcat_pipe.add_label(category_to_train)
        # prepare training and test set
        annotated_data = dataset[dataset[is_annotated_column] == True]
        trainset, testset = train_test_split(annotated_data, test_size=0.3)
        if trainset.size == 0 or testset.size == 0:
            raise ValueError(
                "There is no annotated data, hence no training/test data. Annotate some texts to get training/test data."
            )
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
        signals.message.emit(
            "Training categories model with predictor '{}'...".format(self.name)
        )
        n_iterations = 20
        # get names of other pipes to disable them during training
        other_pipes = [
            pipe for pipe in self.spacy_model.pipe_names if pipe != "textcat"
        ]
        with self.spacy_model.disable_pipes(*other_pipes):  # only train textcat
            optimizer = self.spacy_model.begin_training()
            for iteration in range(n_iterations):
                signals.message.emit("Iteration {}...".format(iteration))
                losses = {}
                batches = minibatch(
                    trainset_for_spacy, size=compounding(4.0, 32.0, 1.001)
                )
                for batch in batches:
                    texts, annotations = zip(*batch)
                    self.spacy_model.update(
                        texts, annotations, sgd=optimizer, drop=0.2, losses=losses
                    )

        # compute precision/recall values
        signals.message.emit("Computing precision/recall matrix...")
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
        signals.message.emit(pd.DataFrame(category_metrics).T.to_string())

        # save model to output directory
        if self.target_model_directory is not None:
            output_dir = pathlib.Path(self.target_model_directory)
            signals.message.emit("Saving model to folder '{}'...".format(output_dir))
            if not output_dir.exists():
                output_dir.mkdir()
            self.spacy_model.meta["name"] = self.target_model_name
            self.spacy_model.to_disk(output_dir)

    def predict_text_categories(self, text, language="en-US"):
        if self.spacy_model:
            doc = self.spacy_model(remove_all_annotations_from_text(text))
            return [
                category for category in doc.cats.keys() if doc.cats[category] >= 0.5
            ]
        else:
            return []
