class CategoryDefinition:
    def __init__(self, name):
        self.name = name


class NamedEntityDefinition:
    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor
