class CategoryDefinition:
    """ Defines a category for labeling texts."""

    def __init__(self, name):
        self.name = name


class NamedEntityDefinition:
    """ Defines a named entity for annotating texts."""

    def __init__(self, code, key_sequence = None, maincolor = None, backcolor = None, forecolor= None):
        self.code = code
        self.key_sequence = key_sequence
        self.maincolor = maincolor
        self.backcolor = backcolor
        self.forecolor = forecolor
