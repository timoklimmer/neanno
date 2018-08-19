from neanno.ui import _AnnotationDialog

class NamedEntityDefinition:
    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor

def annotate_entities(named_entity_definitions):
    
    _AnnotationDialog(named_entity_definitions)
