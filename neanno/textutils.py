import re


def extract_annotations(
    annotated_text, types_to_extract=None, named_entities_to_extract=None
):
    """ Returns all annotations and their position ranges from an annotated text.
    
        - Valid types to extract: 'standalone keywords', 'parented_keywords', 'named_entities'.        
        - If types_to_extract and/or named_entities_to_extract are None, all types/entities are extracted.
        - The returned position ranges ignore other annotations, ie. as if the other annotations did not exist.
        - Beware that the returned positions are meant to be used as ranges. annotated_text[5:14] might return
          the desired result while annotated_text[14] may encounter an index out of range exception."""

    # get plain text without annotations
    plain_text = remove_all_annotations(annotated_text)

    # match all annotations and assemble the relevant annotations
    annotations = {}
    standalone_keywords = []
    parented_keywords = []
    named_entities = []
    for match in re.finditer(
        r"\((?P<text>[^()]+?)\|(?P<type>(S|P|N))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        start_position = len(remove_all_annotations(annotated_text[: match.start()]))
        end_position = start_position + len(
            remove_all_annotations(annotated_text[match.start() : match.end()])
        )
        if match.group("type") == "S" and (
            types_to_extract is None or "standalone_keywords" in types_to_extract
        ):
            standalone_keywords.append((start_position, end_position))
        if match.group("type") == "P" and (
            types_to_extract is None or "parented_keywords" in types_to_extract
        ):
            parented_keywords.append(
                (start_position, end_position, match.group("postfix"))
            )
        if (
            match.group("type") == "N"
            and (types_to_extract is None or "named_entities" in types_to_extract)
            and (
                named_entities_to_extract is None
                or match.group("postfix") in named_entities_to_extract
            )
        ):
            named_entities.append(
                (start_position, end_position, match.group("postfix"))
            )
    if len(standalone_keywords) > 0:
        annotations["standalone_keywords"] = standalone_keywords
    if len(parented_keywords) > 0:
        annotations["parented_keywords"] = parented_keywords
    if len(named_entities) > 0:
        annotations["named_entities"] = named_entities

    # return result
    return (plain_text, annotations)


def remove_annotation_at_position(text, position):
    current_cursor_pos = position
    new_text = re.sub(
        r"\((.*?)\|(((P|N) .+?)|(S))\)",
        lambda match: match.group(1)
        if match.start() < current_cursor_pos < match.end()
        else match.group(0),
        text,
        flags=re.DOTALL,
    )
    return new_text


def remove_all_annotations(text):
    new_text = re.sub(
        r"\((.*?)\|(((P|N) .+?)|(S))\)",
        lambda match: match.group(1),
        text,
        flags=re.DOTALL,
    )
    return new_text


def extract_named_entities_distribution(text):
    """ Computes the types and frequencies of named entities in the specified text."""
    result = {}
    find_entities_pattern = "\((?P<text>.+?)\|N (?P<label>.+?)\)"
    for entity in re.findall(find_entities_pattern, text):
        entity_code = entity[1]
        if entity_code not in result:
            result[entity_code] = 0
        result[entity_code] += 1
    return result
