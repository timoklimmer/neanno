import re

def extract_entities_from_nerded_text(text, allowed_entities=None):
    """ Returns all entities and their positions from a "nerded" text, eg. This is an (example entity|E SOME_ENTITY_TYPE)."""
    # get "empty" result without having entity positions
    result = (re.sub("\((?P<text>.+?)\|E .+?\)", "\g<text>", text), {"entities": []})
    # add entity positions
    working_text = text
    while True:
        find_entities_pattern = "\((?P<text>.+?)\|E (?P<label>.+?)\)"
        match = re.search(find_entities_pattern, working_text)
        if match is not None:
            entity_text = match.group(1)
            entity_label = match.group(2)
            if allowed_entities is None or (
                allowed_entities is not None and entity_label in allowed_entities
            ):
                result[1]["entities"].append(
                    (match.start(1) - 1, match.end(1) - 1, entity_label)
                )
            working_text = re.sub("\(.+?\|E .+?\)", entity_text, working_text, 1)
        else:
            break
    return result

def extract_entities_distribution(text):
    """ Computes the types and frequencies of entities in the specified text."""
    result = {}
    find_entities_pattern = "\((?P<text>.+?)\|E (?P<label>.+?)\)"
    for entity in re.findall(find_entities_pattern, text):
        entity_code = entity[1]
        if entity_code not in result:
            result[entity_code] = 0
        result[entity_code] += 1
    return result