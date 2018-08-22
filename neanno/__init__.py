import pandas as pd

from neanno.models import _TextModel
from neanno.ui import _AnnotationDialog


class NamedEntityDefinition:
    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor


def annotate_entities(
    pandas_data_frame,
    input_text_column_name,
    annotated_text_column_name,
    named_entity_definitions,
    save_callback,
):
    # TODO: ensure that input variable are proper

    text_model = _TextModel(
        pandas_data_frame=pandas_data_frame,
        input_text_column_name=input_text_column_name,
        annotated_text_column_name=annotated_text_column_name,
        save_callback=save_callback
    )
    _AnnotationDialog(text_model, named_entity_definitions)
