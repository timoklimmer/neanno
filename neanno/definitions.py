class CategoryDefinition:
    """ Defines a category for labeling texts."""

    def __init__(self, name):
        self.name = name

class NamedEntityDefinition:
    """ Defines a named entity for annotating texts."""

    def __init__(self, code, key_sequence, maincolor, backcolor, forecolor):
        self.code = code
        self.key_sequence = key_sequence
        self.maincolor = maincolor
        self.backcolor = backcolor
        self.forecolor = forecolor

class AutoSuggestKeyTermRegex:
    """ Defines a regex for autosuggesting key terms."""

    def __init__(self, pattern, parent_terms = []):
        self.pattern = pattern
        self.parent_terms = parent_terms

class AutoSuggestEntityRegex:
    """ Defines a regex for autosuggesting entities."""

    def __init__(self, entity, pattern):
        self.entity = entity
        self.pattern = pattern