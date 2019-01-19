from neanno.utils.list import get_set_of_list_and_keep_sequence, not_none
from neanno.utils.text import unmask_annotations


class AnnotationPredictor:
    """ Predicts different annotations for a text."""

    # TODO: finalize category predictor

    predictors = {}

    def add_predictor(self, name, predictor):
        self.predictors[name] = predictor

    def remove_predictor(self, name):
        del self.predictors[name]

    def has_predictor(self, name):
        return name in self.predictors

    def get_predictor(self, name):
        return self.predictors[name]

    def invoke_predictors(self, function_name, *args):
        for predictor in self.predictors.values():
            if hasattr(predictor, function_name):
                getattr(predictor, function_name)(*args)

    def collect_from_predictors(
        self, function_name, make_result_distinct, filter_none_values, *args
    ):
        result = []
        for predictor in self.predictors.values():
            if hasattr(predictor, function_name):
                predictor_response = getattr(predictor, function_name)(*args)
                if predictor_response:
                    result = result.extend(getattr(predictor, function_name)(*args))
        if filter_none_values:
            result = not_none(result)
        if make_result_distinct:
            result = get_set_of_list_and_keep_sequence(result)
        return result

    def learn_from_annotated_text(self, annotated_text):
        self.invoke_predictors("learn_from_annotated_text", annotated_text)

    def learn_from_annotated_dataset(self, dataset):
        self.invoke_predictors("learn_from_annotated_dataset", dataset)

    def predict_inline_annotations(self, text):
        result = text
        for predictor in self.predictors.values():
            if hasattr(predictor, "predict_inline_annotations"):
                result = predictor.predict_inline_annotations(result, True)
        result = unmask_annotations(result)
        return result

    def predict_categories(self, text):
        result = []
        for predictor in self.predictors.values():
            if hasattr(predictor, "predict_categories"):
                result = result.extend(predictor.predict_categories(text))
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
