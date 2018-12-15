class CategoryDefinition:
    """ Defines a category for labeling texts."""

    def __init__(self, name):
        self.name = name


class NamedEntityDefinition:
    """ Defines a named entity for annotating texts."""

    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor

class AutoSuggestRegex:
    """ Defines a regex for autosuggesting entities."""

    def __init__(self, entity, pattern):
        self.entity = entity
        self.pattern = pattern