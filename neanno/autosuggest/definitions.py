class KeyTermRegex:
    """ Defines a regex for autosuggesting key terms."""

    def __init__(self, name, pattern, parent_terms=[]):
        self.name = name
        self.pattern = pattern
        self.parent_terms = parent_terms


class NamedEntityRegex:
    """ Defines a regex for autosuggesting entities."""

    def __init__(self, entity, pattern, parent_terms=[]):
        self.entity = entity
        self.pattern = pattern
        self.parent_terms = parent_terms
