from PyQt5.QtCore import QObject, QThreadPool

from neanno.utils.list import get_set_of_list_and_keep_sequence, not_none
from neanno.utils.signals import emit_top_header, emit_message, emit_new_line
from neanno.utils.text import annotate_text, extract_annotations_as_list
from neanno.utils.threading import ConsoleSignalsHandler, ParallelWorker


class PredictionPipeline(QObject):
    """ Predicts different annotations for a text."""

    _predictors = {}
    _threadpool = QThreadPool()

    def add_predictor(self, predictor):
        """Adds a predictor to the pipeline."""
        self._predictors[predictor.name] = predictor

    def remove_predictor(self, name):
        """Removes a predictor from the pipeline."""
        del self._predictors[name]

    def has_predictor(self, name):
        """Checks if the pipeline has a predictor with the given name."""
        return name in self._predictors

    def has_predictors(self):
        """Checks if the pipeline has any predictor."""
        return len(self._predictors) > 0

    def get_predictor(self, name):
        """Returns the predictor with the specified name."""
        return self._predictors[name]

    def get_all_predictors(self):
        """Returns all predictors."""
        return self._predictors.values()

    def get_all_prediction_enabled_predictors(self):
        """Returns all predictors which are enabled for prediction."""
        return [
            predictor
            for predictor in self._predictors.values()
            if predictor.is_prediction_enabled
        ]

    def invoke_predictors(self, function_name, condition_function, *args, **kwargs):
        """Invokes the given function on any predictor where the given condition function returns true for the predictor."""
        for predictor in self.get_all_predictors():
            if hasattr(predictor, function_name) and condition_function(predictor):
                getattr(predictor, function_name)(*args, **kwargs)

    def collect_from_predictors(
        self, function_name, make_result_distinct, filter_none_values, *args, **kwargs
    ):
        """Invokes the specified function on all predictors and collects the individual results in a list."""
        result = []
        for predictor in self.get_all_predictors():
            if hasattr(predictor, function_name):
                predictor_response = getattr(predictor, function_name)(*args, **kwargs)
                if predictor_response:
                    result = result.extend(
                        getattr(predictor, function_name)(*args, **kwargs)
                    )
        if filter_none_values:
            result = not_none(result)
        if make_result_distinct:
            result = get_set_of_list_and_keep_sequence(result)
        return result

    def train_from_annotated_text(self, annotated_text, language):
        """Passes the given text to all predictors which are enabled for online training so these can learn from the annotations."""
        self.invoke_predictors(
            "train_from_annotated_text",
            lambda predictor: predictor.is_online_training_enabled,
            annotated_text,
            language,
        )

    def train_from_trainset_async(
        self,
        trainset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals_handler=ConsoleSignalsHandler(),
    ):
        """Trains all predictors which are enabled for batch training with the given trainset (async version)."""

        def _train_from_trainset_inner(*args, **kwargs):
            signals = kwargs["signals"]

            # emit header
            emit_top_header("Training Batch Models...", signals)
            emit_message(
                "NOTE: You can continue annotating while the models are trained.",
                signals,
            )
            emit_new_line(signals)

            # train all predictors that are enabled for batch training
            self.invoke_predictors(
                "train_from_trainset",
                lambda predictor: predictor.is_batch_training_enabled,
                trainset,
                text_column,
                is_annotated_column,
                language_column,
                categories_column,
                categories_to_train,
                entity_codes_to_train,
                signals=signals,
            )

        # start the parallel training
        self._threadpool.start(
            ParallelWorker(_train_from_trainset_inner, signals_handler)
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
        signals_handler=ConsoleSignalsHandler(),
    ):
        """Trains all predictors which are enabled for batch training with the given trainset (sync version)."""

        # call the async version of this method
        self.train_from_trainset_async(
            trainset,
            text_column,
            is_annotated_column,
            language_column,
            categories_column,
            categories_to_train,
            entity_codes_to_train,
            signals_handler,
        )
        # wait for done
        # note: this waits until the entire threadpool is done
        # TODO: check if there is a way to wait only for this worker
        self._threadpool.waitForDone()

    def predict_inline_annotations(self, text, language="en-US"):
        """Predicts the contained named entities on the given text."""

        if not text:
            return ""
        annotations = []
        for predictor in self.get_all_prediction_enabled_predictors():
            annotations_by_predictor = extract_annotations_as_list(
                predictor.predict_inline_annotations(text, language)
            )
            annotations.extend(annotations_by_predictor)
        return annotate_text(text, annotations)

    def predict_text_categories(self, text, language="en-US"):
        """Predicts the text categories of the given text."""

        if not text:
            return ""
        result = []
        for predictor in self.get_all_prediction_enabled_predictors():
            new_text_categories = predictor.predict_text_categories(text, language)
            result.extend(new_text_categories)
            result = get_set_of_list_and_keep_sequence(result)
        return result

    def get_parent_terms_for_named_entity(self, term, entity_code):
        return ", ".join(
            not_none(
                self.collect_from_predictors(
                    "get_parent_terms_for_named_entity", True, True, term, entity_code
                )
            )
        )

    def mark_key_term_for_removal(self, key_term):
        self.invoke_predictors(
            "mark_key_term_for_removal",
            lambda predictor: predictor.is_online_training_enabled,
            key_term,
        )

    def reset_key_terms_marked_for_removal(self):
        self.invoke_predictors(
            "reset_key_terms_marked_for_removal",
            lambda predictor: predictor.is_online_training_enabled,
        )

    def mark_named_entity_term_for_removal(self, term, entity_code):
        self.invoke_predictors(
            "mark_named_entity_term_for_removal",
            lambda predictor: predictor.is_online_training_enabled,
            term,
            entity_code,
        )

    def reset_named_entity_terms_marked_for_removal(self):
        self.invoke_predictors(
            "reset_named_entity_terms_marked_for_removal",
            lambda predictor: predictor.is_online_training_enabled,
        )

    def test_models_async(
        self,
        testset,
        testset_size,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals_handler=ConsoleSignalsHandler(),
    ):
        """Tests the models of all predictors which are enabled for testing (async version)."""

        def _test_models_inner(*args, **kwargs):
            signals = kwargs["signals"]

            # emit header
            emit_top_header("Testing Models...", signals)
            emit_message(
                "NOTE: You can continue annotating while the models are tested.",
                signals,
            )
            emit_new_line(signals)
            emit_message(
                "Total size of test set: {} ({:.0%})".format(testset.shape[0], testset_size),
                signals,
            )
            emit_new_line(signals)

            # test all predictors that are enabled for testing
            self.invoke_predictors(
                "test_model",
                lambda predictor: predictor.is_testing_enabled,
                testset,
                text_column,
                is_annotated_column,
                language_column,
                categories_column,
                categories_to_train,
                entity_codes_to_train,
                signals=signals,
            )

        # start the testing
        self._threadpool.start(ParallelWorker(_test_models_inner, signals_handler))

    def test_models(
        self,
        testset,
        testset_size,   
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals_handler=ConsoleSignalsHandler(),
    ):
        """Tests the models of all predictors which are enabled for testing (sync version)."""

        # call the async version of this method
        self.test_models_async(
            testset,
            testset_size,
            text_column,
            is_annotated_column,
            language_column,
            categories_column,
            categories_to_train,
            entity_codes_to_train,
            signals_handler,
        )
        # wait for done
        # note: this waits until the entire threadpool is done
        # TODO: check if there is a way to wait only for this worker
        self._threadpool.waitForDone()
