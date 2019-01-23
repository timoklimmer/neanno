import pandas as pd
from neanno.utils.text import merge_dict_sum_child_dicts


def compute_ner_metrics_at_text_level(
    actual_annotations, predicted_annotations, all_entity_codes
):
    actual_annotations = [
        annotation
        for annotation in actual_annotations
        if annotation["type"] in ["standalone_named_entity", "parented_named_entity"]
    ]
    predicted_annotations = [
        annotation
        for annotation in predicted_annotations
        if annotation["type"] in ["standalone_named_entity", "parented_named_entity"]
    ]
    counters = {
        entity_code: {
            "correct": 0,
            "incorrect": 0,
            "actual": 0,
            "possible": 0,
            "precision": 0,
            "recall": 0,
        }
        for entity_code in all_entity_codes
    }
    for predicted_annotation in predicted_annotations:
        entity_code = predicted_annotation["entity_code"]
        counters[entity_code]["actual"] += 1
        if predicted_annotation in actual_annotations:
            counters[entity_code]["correct"] += 1
        else:
            counters[entity_code]["incorrect"] += 1
    for actual_annotation in actual_annotations:
        entity_code = actual_annotation["entity_code"]
        counters[entity_code]["possible"] += 1
    for entity_code in all_entity_codes:
        correct = counters[entity_code]["correct"]
        actual = counters[entity_code]["correct"]
        possible = counters[entity_code]["possible"]
        counters[entity_code]["precision"] = correct / actual if actual > 0 else 0
        counters[entity_code]["recall"] = correct / possible if possible > 0 else 0
    return counters


def aggregate_ner_metrics(ner_metrics1, ner_metrics2):
    result = merge_dict_sum_child_dicts(ner_metrics1, ner_metrics2)
    for entity_code in result:
        correct = result[entity_code]["correct"]
        actual = result[entity_code]["actual"]
        possible = result[entity_code]["possible"]
        result[entity_code]["precision"] = correct / actual if actual > 0 else 0
        result[entity_code]["recall"] = correct / possible if possible > 0 else 0
    return result


def compute_ner_metrics_from_actual_predicted_columns(
    actual_annotations_as_pandas_series,
    predicted_annotations_as_pandas_series,
    all_entity_codes,
):
    """ Computes some metrics incl. precision and recall on entity code level."""

    result = {}
    for (index, actual_annotations) in actual_annotations_as_pandas_series.iteritems():
        predicted_annotations = predicted_annotations_as_pandas_series[index]
        ner_metrics_on_text_level = compute_ner_metrics_at_text_level(
            actual_annotations, predicted_annotations, all_entity_codes
        )
        result = aggregate_ner_metrics(result, ner_metrics_on_text_level)
    return result
