from PyQt5.QtCore import QObject, QThreadPool

from neanno.utils.list import get_set_of_list_and_keep_sequence, not_none
from neanno.utils.threading import ParallelWorker, ParallelWorkerSignals
from neanno.utils.text import extract_annotations_as_list, annotate_text


class PredictionPipeline(QObject):
    """ Predicts different annotations for a text."""

    _predictors = {}
    _threadpool = QThreadPool()

    def add_predictor(self, predictor):
        self._predictors[predictor.name] = predictor

    def remove_predictor(self, name):
        del self._predictors[name]

    def has_predictor(self, name):
        return name in self._predictors

    def has_predictors(self):
        return len(self._predictors) > 0

    def get_predictor(self, name):
        return self._predictors[name]

    def get_all_predictors(self):
        return self._predictors.values()

    def get_all_prediction_enabled_predictors(self):
        return [
            predictor
            for predictor in self._predictors.values()
            if predictor.is_prediction_enabled
        ]

    def invoke_predictors(self, function_name, *args, **kwargs):
        for predictor in self.get_all_predictors():
            if hasattr(predictor, function_name):
                getattr(predictor, function_name)(*args, **kwargs)

    def collect_from_predictors(
        self, function_name, make_result_distinct, filter_none_values, *args, **kwargs
    ):
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

    def learn_from_annotated_text(self, annotated_text):
        self.invoke_predictors("learn_from_annotated_text", annotated_text)

    def learn_from_annotated_dataset_async(
        self,
        dataset,
        text_column,
        is_annotated_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signal_slots=ParallelWorkerSignals.default_slots(),
    ):
        parallel_worker = ParallelWorker(
            self.invoke_predictors,
            signal_slots,
            "learn_from_annotated_dataset",
            dataset,
            text_column,
            is_annotated_column,
            categories_column,
            categories_to_train,
            entity_codes_to_train,
        )
        self._threadpool.start(parallel_worker)

    def learn_from_annotated_dataset(
        self,
        dataset,
        text_column,
        is_annotated_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signal_slots=ParallelWorkerSignals.default_slots(),
    ):
        # call the async version of this method
        self.learn_from_annotated_dataset_async(
            dataset,
            text_column,
            is_annotated_column,
            categories_column,
            categories_to_train,
            entity_codes_to_train,
            signal_slots,
        )
        # wait for done
        # note: this waits until the entire threadpool is done
        # TODO: check if there is a way to wait only for this worker
        self._threadpool.waitForDone()

    def predict_inline_annotations(self, text):
        if not text:
            return ""
        annotations = []
        for predictor in self.get_all_prediction_enabled_predictors():
            annotations_by_predictor = extract_annotations_as_list(
                predictor.predict_inline_annotations(text)
            )
            annotations.extend(annotations_by_predictor)
        return annotate_text(text, annotations)

    def predict_text_categories(self, text):
        if not text:
            return ""
        result = []
        for predictor in self.get_all_prediction_enabled_predictors():
            new_text_categories = predictor.predict_text_categories(text)
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
        self.invoke_predictors("mark_key_term_for_removal", key_term)

    def reset_key_terms_marked_for_removal(self):
        self.invoke_predictors("reset_key_terms_marked_for_removal")

    def mark_named_entity_term_for_removal(self, term, entity_code):
        self.invoke_predictors("mark_named_entity_term_for_removal", term, entity_code)

    def reset_named_entity_terms_marked_for_removal(self):
        self.invoke_predictors("reset_named_entity_terms_marked_for_removal")
