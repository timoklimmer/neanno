import pandas as pd

from neanno.models import TextModel
from neanno.ui import AnnotationDialog


class CategoryDefinition:
    def __init__(self, name):
        self.name = name


class NamedEntityDefinition:
    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor


def ask_for_annotations(
    dataframe_to_edit,
    dataset_source_friendly,
    text_column,
    is_annotated_column,
    named_entity_defs,
    category_defs,
    categories_column,
    save_callback,
    dataset_target_friendly,
    spacy_model_source,
    spacy_model_target,
):
    # TODO: ensure valid parameters

    # compute the named entity definition collection
    named_entity_definitions = []
    default_colors = [
        "#153465",
        "#67160e",
        "#135714",
        "#341b4d",
        "#b45c18",
        "#b0984f",
        "#838b83",
        "#2f4f4f",
    ]
    index = 0
    if named_entity_defs:
        for definition in named_entity_defs.split("/"):
            items = definition.split(" ")
            code = items[0]
            shortcut = items[1]
            color = (
                items[2] if len(items) >= 3 else default_colors[index % len(default_colors)]
            )
            named_entity_definitions.append(NamedEntityDefinition(code, shortcut, color))
            index += 1

    # assemble the category definition collection
    category_definitions = []
    if category_defs:
        for definition in category_defs.split("/"):
            name = definition
            category_definitions.append(CategoryDefinition(name))

    # run the annotation dialog with respective text model
    AnnotationDialog(
        TextModel(
            pandas_data_frame=dataframe_to_edit,
            dataset_source_friendly=dataset_source_friendly,
            text_column=text_column,
            is_annotated_column=is_annotated_column,
            category_definitions=category_definitions,
            categories_column=categories_column,
            named_entity_definitions=named_entity_definitions,
            save_callback=save_callback,
            dataset_target_friendly=dataset_target_friendly,
            spacy_model_source=spacy_model_source,
            spacy_model_target=spacy_model_target,
        )
    )
