import argparse

import pandas as pd

from neanno import NamedEntityDefinition, annotate_entities


def main():
    parser = argparse.ArgumentParser(
        description="Yet another named entity annotation tool."
    )
    parser.add_argument(
        "--filename", "-f", help="Path to a CSV file containing the data to annotate."
    )
    parser.add_argument(
        "--output_file",
        "-o",
        help="Path to the CSV output file which will contain the annotations.",
    )
    parser.add_argument(
        "--source_column_name",
        "-s",
        help="Name of the column containing the texts to annotate.",
    )
    parser.add_argument(
        "--target_column_name",
        "-t",
        help="Name of the column containing the annotated texts. Must be different from source column name.",
    )
    parser.add_argument(
        "--named_entity_defs",
        "-n",
        help='Defines the entities available for annotation incl. shortcuts. Eg. "BLUE Alt+B/RED Alt+R/GREEN Alt+G"',
    )
    args = parser.parse_args()

    filename = args.filename  # "sample_texts.csv"
    output_file = args.output_file  # "sample_texts.annotated.csv"
    source_column_name = args.source_column_name  # "Text"
    target_column_name = args.target_column_name  # "Annotated Text"
    named_entity_defs_string = (
        args.named_entity_defs
    )  # "BLUE Alt+B/RED Alt+R/GREEN Alt+G"

    # ensure that source_column_name and target_column_name are not the same
    # TODO: throw exception
    assert source_column_name != target_column_name

    # load pandas data frame
    dataframe_to_edit = pd.read_csv(filename)

    # declare the named entities to annotate
    named_entity_definitions = []
    colors = ["#153465", "#67160e", "#135714", "#341b4d", "#b45c18", "#b0984f"]
    index = 0
    for definition in named_entity_defs_string.split("/"):
        items = definition.split(" ")
        code = items[0]
        shortcut = items[1]
        color = colors[index % len(colors)]
        named_entity_definitions.append(NamedEntityDefinition(code, shortcut, color))
        index += 1

    # run the annotation UI
    annotate_entities(
        dataframe_to_edit=dataframe_to_edit,
        source_text_column_name=source_column_name,
        annotated_text_column_name=target_column_name,
        named_entity_definitions=named_entity_definitions,
        save_callback=lambda df: df.to_csv(output_file, index=False, header=True),
    )


if __name__ == "__main__":
    main()
