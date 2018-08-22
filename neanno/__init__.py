import pandas as pd

from neanno.models import _TextModel
from neanno.ui import _AnnotationDialog


class NamedEntityDefinition:
    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor


def annotate_entities(pandas_data_frame, named_entity_definitions):
    text_model = _TextModel(df=pandas_data_frame)
    _AnnotationDialog(text_model, named_entity_definitions)
