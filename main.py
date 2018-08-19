# pylint: disable=E0611

from neanno import (AnnotationDialog, NamedEntityDefinition)
from PyQt5.QtWidgets import QApplication

def main():
    named_entity_definitions = [
        NamedEntityDefinition("BLU", "Alt+B", "#153465"),
        NamedEntityDefinition("RED", "Alt+R", "#67160e"),
        NamedEntityDefinition("GRN", "Alt+G", "#135714"),
        NamedEntityDefinition("PRP", "Alt+P", "#341b4d"),
        NamedEntityDefinition("ORG", "Alt+O", "#b45c18"),
        NamedEntityDefinition("YLW", "Alt+Y", "#b0984f")
    ]
    annotation_dialog = AnnotationDialog(named_entity_definitions)

if __name__ == '__main__':
    main()
