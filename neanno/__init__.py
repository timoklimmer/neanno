import pandas as pd

from neanno.models import _TextModel
from neanno.ui import _AnnotationDialog


class NamedEntityDefinition:
    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor


def annotate_entities(
    dataframe_to_edit,
    text_column_name,
    is_annotated_column_name,
    named_entity_definitions,
    save_callback,
    ner_model_source_spacy,
    ner_model_target_spacy,
    dataset_source_friendly,
    dataset_target_friendly,
):
    # TODO: ensure that input variable are proper

    text_model = _TextModel(
        pandas_data_frame=dataframe_to_edit,
        text_column_name=text_column_name,
        is_annotated_column_name=is_annotated_column_name,
        save_callback=save_callback,
        ner_model_source_spacy=ner_model_source_spacy,
        ner_model_target_spacy=ner_model_target_spacy,
        dataset_source_friendly=dataset_source_friendly,
        dataset_target_friendly=dataset_target_friendly,
    )
    _AnnotationDialog(text_model, named_entity_definitions)
