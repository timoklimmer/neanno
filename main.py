# pylint: disable=E0611
from neanno import NamedEntityDefinition, annotate_entities


def main():
    named_entity_definitions = [
        NamedEntityDefinition("BLU", "Alt+B", "#153465"),
        NamedEntityDefinition("RED", "Alt+R", "#67160e"),
        NamedEntityDefinition("GRN", "Alt+G", "#135714"),
        NamedEntityDefinition("PRP", "Alt+P", "#341b4d"),
        NamedEntityDefinition("ORG", "Alt+O", "#b45c18"),
        NamedEntityDefinition("YLW", "Alt+Y", "#b0984f"),
    ]
    annotate_entities(named_entity_definitions)


if __name__ == "__main__":
    main()
