import re

TERM_TYPE_TINY_TO_LONG_MAPPING = {
    "S": "standalone_keyterm",
    "P": "parented_keyterm",
    "N": "named_entity",
}


def extract_annotations_as_text_and_ranges(
    annotated_text, types_to_extract=None, entity_names_to_extract=None
):
    """ Returns all annotations and their position ranges from an annotated text.
    
        - Valid types to extract: 'standalone_keyterm', 'parented_keyterm', 'named_entity'.        
        - If types_to_extract and/or entity_names_to_extract are None, all types/entities are extracted.
        - The returned position ranges ignore other annotations, ie. as if the other annotations did not exist.
        - Beware that the returned positions are meant to be used as ranges. annotated_text[5:14] might return
          the desired result while annotated_text[14] may encounter an index out of range exception."""

    # ensure that types_to_extract has valid entries
    for type_to_extract in types_to_extract:
        if type_to_extract not in [
            "standalone_keyterm",
            "parented_keyterm",
            "named_entity",
        ]:
            raise ValueError(
                "At least one entry in param 'types_to_extract' is invalid. Ensure that only valid types are used."
            )

    # get plain text without annotations
    plain_text = remove_all_annotations(annotated_text)

    # match all annotations and assemble the relevant annotations
    annotations = {}
    standalone_keyterms = []
    parented_keyterms = []
    named_entities = []
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(S|P|N))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        start_position = len(remove_all_annotations(annotated_text[: match.start()]))
        end_position = start_position + len(
            remove_all_annotations(annotated_text[match.start() : match.end()])
        )
        if match.group("term_type_tiny") == "S" and (
            types_to_extract is None or "standalone_keyterm" in types_to_extract
        ):
            standalone_keyterms.append((start_position, end_position))
        if match.group("term_type_tiny") == "P" and (
            types_to_extract is None or "parented_keyterm" in types_to_extract
        ):
            parented_keyterms.append(
                (start_position, end_position, match.group("postfix"))
            )
        if (
            match.group("term_type_tiny") == "N"
            and (types_to_extract is None or "named_entity" in types_to_extract)
            and (
                entity_names_to_extract is None
                or match.group("postfix") in entity_names_to_extract
            )
        ):
            named_entities.append(
                (start_position, end_position, match.group("postfix"))
            )
    if len(standalone_keyterms) > 0:
        annotations["standalone_keyterms"] = standalone_keyterms
    if len(parented_keyterms) > 0:
        annotations["parented_keyterms"] = parented_keyterms
    if len(named_entities) > 0:
        annotations["named_entities"] = named_entities

    # return result
    return (plain_text, annotations)


def extract_annotations_as_dictlist(
    annotated_text, types_to_extract=None, entity_names_to_extract=None
):

    """ Returns all annotations from an annotated text as a list of dictionaries.
    
        - Valid types to extract: 'standalone_keyterm', 'parented_keyterm', 'named_entity'.        
        - If types_to_extract and/or entity_names_to_extract are None, all types/entities are extracted.
        - The returned position ranges ignore other annotations, ie. as if the other annotations did not exist.
        - Beware that the returned positions are meant to be used as ranges. annotated_text[5:14] might return
          the desired result while annotated_text[14] may encounter an index out of range exception.
    """

    # ensure that types_to_extract has valid entries
    for type_to_extract in types_to_extract:
        if type_to_extract not in [
            "standalone_keyterm",
            "parented_keyterm",
            "named_entity",
        ]:
            raise ValueError(
                "At least one entry in param 'types_to_extract' is invalid. Ensure that only valid types are used."
            )

    result = []
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(S|P|N))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        # compute full result
        term = match.group("term")
        term_type_long = TERM_TYPE_TINY_TO_LONG_MAPPING.get(
            match.group("term_type_tiny")
        )
        postfix = match.group("postfix")
        start_position = len(remove_all_annotations(annotated_text[: match.start()]))
        end_position = start_position + len(
            remove_all_annotations(annotated_text[match.start() : match.end()])
        )
        dict_to_add = {
            "term": term,
            "start": start_position,
            "end": end_position,
            "term_type_long": term_type_long,
        }
        if term_type_long == "parented_keyword":
            dict_to_add["parent_terms"] = postfix
        if term_type_long == "named_entity":
            dict_to_add["entity_name"] = postfix
        result.append(dict_to_add)
        # apply filters if needed
        if types_to_extract:
            result = [
                item for item in result if item["term_type_long"] in types_to_extract
            ]
        if entity_names_to_extract:
            result = [
                item
                for item in result
                if item["term_type_long"] != "named_entity"
                or (
                    item["term_type_long"] == "named_entity"
                    and "entity_name" in item
                    and item["entity_name"] in entity_names_to_extract
                )
            ]
    return result


def extract_annotations_as_text(annotated_text, external_annotations_to_add=[]):
    result_list = []
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(S|P|N))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        term = match.group("term")
        term_type_long = TERM_TYPE_TINY_TO_LONG_MAPPING.get(
            match.group("term_type_tiny")
        )
        postfix = match.group("postfix")
        # standalone key term
        if term_type_long == "standalone_keyterm":
            annotation_to_add = term
            if annotation_to_add.lower() not in [
                annotation.lower() for annotation in result_list
            ] and annotation_to_add.lower() not in [
                annotation.lower() for annotation in external_annotations_to_add
            ]:
                result_list.append(annotation_to_add)
        # parented key terms
        if term_type_long == "parented_keyterm":
            parent_terms = []
            for parent_term in set(
                [parent_term.strip() for parent_term in postfix.split(",")]
            ):
                annotation_to_add = parent_term
                if annotation_to_add.lower() not in [
                    annotation.lower() for annotation in result_list
                ] and annotation_to_add.lower() not in [
                    annotation.lower() for annotation in external_annotations_to_add
                ]:
                    parent_terms.append(annotation_to_add)
            result_list.extend(sorted(parent_terms))
        # named entity
        if term_type_long == "named_entity":
            annotation_to_add = "{}:{}".format(postfix.lower(), term)
            if annotation_to_add.lower() not in [
                annotation.lower() for annotation in result_list
            ] and annotation_to_add.lower() not in [
                annotation.lower() for annotation in external_annotations_to_add
            ]:
                result_list.append(annotation_to_add)

    # external annotations
    result_list.extend(external_annotations_to_add)

    # return result
    return ", ".join(result_list)


def get_annotation_at_position(annotated_text, position):
    result = None
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(S|P|N))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        if not (match.start() < position < match.end()):
            continue
        term = match.group("term")
        term_type_long = TERM_TYPE_TINY_TO_LONG_MAPPING.get(
            match.group("term_type_tiny")
        )
        postfix = match.group("postfix")
        start_position = len(remove_all_annotations(annotated_text[: match.start()]))
        end_position = start_position + len(
            remove_all_annotations(annotated_text[match.start() : match.end()])
        )
        result = {
            "term": term,
            "start": start_position,
            "end": end_position,
            "term_type_long": term_type_long,
        }
        if term_type_long == "parented_keyword":
            result["parent_terms"] = postfix
        if term_type_long == "named_entity":
            result["entity_name"] = postfix
    return result


def remove_annotations_by_position(annotated_text, position):
    annotation_at_position = get_annotation_at_position(annotated_text, position)
    if annotation_at_position is not None:
        # remove annotation from text
        new_text = re.sub(
            r"\((.*?)\|(((P|N) .+?)|(S))\)",
            lambda match: match.group(1)
            if match.start() < position < match.end()
            else match.group(0),
            annotated_text,
            flags=re.DOTALL,
        )

        # remove all other occurences of the same key term as well
        if annotation_at_position["term_type_long"] in [
            "standalone_keyterm",
            "parented_keyterm",
        ]:
            term = annotation_at_position["term"]
            new_text = re.sub(
                r"(?i)\(({})\|(((P) .+?)|(S))\)".format(re.escape(term)),
                term,
                new_text,
                flags=re.DOTALL,
            )

    return (new_text, annotation_at_position)


def remove_all_annotations(annotated_text):
    new_text = re.sub(
        r"\((.*?)\|(((P|N) .+?)|(S))\)",
        lambda match: match.group(1),
        annotated_text,
        flags=re.DOTALL,
    )
    return new_text


def extract_named_entities_distribution(annotated_text):
    """ Computes the types and frequencies of named entities in the specified text."""
    result = {}
    find_entities_pattern = "\((?P<term>.+?)\|N (?P<label>.+?)\)"
    for entity in re.findall(find_entities_pattern, annotated_text):
        entity_code = entity[1]
        if entity_code not in result:
            result[entity_code] = 0
        result[entity_code] += 1
    return result
