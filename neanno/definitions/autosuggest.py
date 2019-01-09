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