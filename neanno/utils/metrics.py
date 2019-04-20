import pandas as pd

from neanno.utils.dict import merge_dict_sum_child_dicts
from neanno.utils.text import (
    extract_annotations_as_list,
    extract_categories_from_categories_column,
    extract_entity_codes_from_annotated_texts_column,
)


def compute_ner_metrics_on_text_level(
    actual_annotations, predicted_annotations, considered_entity_codes
):
    actual_annotations = [
        annotation
        for annotation in actual_annotations
        if annotation["type"] in ["standalone_named_entity", "parented_named_entity"]
        and annotation["entity_code"] in considered_entity_codes
    ]
    predicted_annotations = [
        annotation
        for annotation in predicted_annotations
        if annotation["type"] in ["standalone_named_entity", "parented_named_entity"]
        and annotation["entity_code"] in considered_entity_codes
    ]
    counters = {
        entity_code: {
            "correct": 0,
            "incorrect": 0,
            "number_predictions": 0,
            "possible": 0,
            "precision": 0,
            "recall": 0,
        }
        for entity_code in considered_entity_codes
    }
    for predicted_annotation in predicted_annotations:
        entity_code = predicted_annotation["entity_code"]
        counters[entity_code]["number_predictions"] += 1
        if any(
            actual_annotation["entity_code"] == predicted_annotation["entity_code"]
            and actual_annotation["start_net"] == predicted_annotation["start_net"]
            and actual_annotation["end_net"] == predicted_annotation["end_net"]
            for actual_annotation in actual_annotations
        ):
            # if predicted_annotation in actual_annotations:
            counters[entity_code]["correct"] += 1
        else:
            counters[entity_code]["incorrect"] += 1
    for actual_annotation in actual_annotations:
        entity_code = actual_annotation["entity_code"]
        counters[entity_code]["possible"] += 1
    for entity_code in considered_entity_codes:
        correct = counters[entity_code]["correct"]
        number_predictions = counters[entity_code]["number_predictions"]
        possible = counters[entity_code]["possible"]
        counters[entity_code]["precision"] = (
            correct / number_predictions if number_predictions > 0 else 0
        )
        counters[entity_code]["recall"] = correct / possible if possible > 0 else 0
    return counters

def compute_category_metrics_on_text_level(
    actual_categories, predicted_categories, considered_categories
):
    actual_categories = [
        category
        for category in actual_categories
        if category in considered_categories
    ]
    predicted_categories = [
        category
        for category in predicted_categories
        if category in considered_categories
    ]
    counters = {
        category: {
            "correct": 0,
            "incorrect": 0,
            "number_predictions": 0,
            "possible": 0,
            "precision": 0,
            "recall": 0,
        }
        for category in considered_categories
    }
    for predicted_category in predicted_categories:
        category = predicted_category
        counters[category]["number_predictions"] += 1
        if any(
            actual_category == predicted_category
            for actual_category in actual_categories
        ):
            counters[category]["correct"] += 1
        else:
            counters[category]["incorrect"] += 1
    for actual_category in actual_categories:
        category = actual_category
        counters[category]["possible"] += 1
    for category in considered_categories:
        correct = counters[category]["correct"]
        number_predictions = counters[category]["number_predictions"]
        possible = counters[category]["possible"]
        counters[category]["precision"] = (
            correct / number_predictions if number_predictions > 0 else 0
        )
        counters[category]["recall"] = correct / possible if possible > 0 else 0
    return counters

def aggregate_ner_metrics(ner_metrics1, ner_metrics2):
    result = merge_dict_sum_child_dicts(ner_metrics1, ner_metrics2)
    for entity_code in result:
        correct = result[entity_code]["correct"]
        actual = result[entity_code]["number_predictions"]
        possible = result[entity_code]["possible"]
        result[entity_code]["precision"] = correct / actual if actual > 0 else 0
        result[entity_code]["recall"] = correct / possible if possible > 0 else 0
    return result

def aggregate_category_metrics(category_metrics1, category_metrics2):
    result = merge_dict_sum_child_dicts(category_metrics1, category_metrics2)
    for category in result:
        correct = result[category]["correct"]
        actual = result[category]["number_predictions"]
        possible = result[category]["possible"]
        result[category]["precision"] = correct / actual if actual > 0 else 0
        result[category]["recall"] = correct / possible if possible > 0 else 0
    return result

def compute_ner_metrics(
    actual_annotated_texts_pandas_series,
    predicted_annotated_texts_pandas_series,
    considered_entity_codes=None,
):
    """ Computes some metrics incl. precision and recall on entity code level, given a text column with the true annotations and a column with the predicted annotations."""

    actual_annotations_series = actual_annotated_texts_pandas_series.map(
        lambda text: extract_annotations_as_list(
            text, types_to_extract=["standalone_named_entity", "parented_named_entity"]
        )
    )
    predicted_annotations_series = predicted_annotated_texts_pandas_series.map(
        lambda text: extract_annotations_as_list(
            text, types_to_extract=["standalone_named_entity", "parented_named_entity"]
        )
    )
    if considered_entity_codes is None:
        considered_entity_codes = extract_entity_codes_from_annotated_texts_column(
            actual_annotated_texts_pandas_series
        )

    result = {}
    for (index, actual_annotations) in actual_annotations_series.iteritems():
        predicted_annotations = predicted_annotations_series[index]
        ner_metrics_on_text_level = compute_ner_metrics_on_text_level(
            actual_annotations, predicted_annotations, considered_entity_codes
        )
        result = aggregate_ner_metrics(result, ner_metrics_on_text_level)
    return result


def compute_category_metrics(
    actual_categories_pandas_series,
    predicted_categories_pandas_series,
    considered_categories=None,
):
    """ Computes precision and recall for predicted text categories."""
    actual_categories_series = actual_categories_pandas_series.map(
        lambda text: text.split("|")
    )
    predicted_categories_series = predicted_categories_pandas_series.map(
        lambda text: text.split("|")
    )
    if considered_categories is None:
        considered_categories = extract_categories_from_categories_column(
            actual_categories_pandas_series
        )

    result = {}
    for (index, actual_categories) in actual_categories_series.iteritems():
        predicted_categories = predicted_categories_series[index]
        category_metrics_on_text_level = compute_category_metrics_on_text_level(
            actual_categories, predicted_categories, considered_categories
        )
        result = aggregate_category_metrics(result, category_metrics_on_text_level)
    return result
