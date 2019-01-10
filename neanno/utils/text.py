import base64
import re

TINY_TO_LONG_ANNOTATION_TYPE_MAPPING = {
    "SK": "standalone_keyterm",
    "PK": "parented_keyterm",
    "SN": "standalone_named_entity",
}


def extract_annotations_as_list(
    annotated_text, term_types_to_extract=None, entity_names_to_extract=None
):

    """ Returns all annotations from an annotated text as a list of dictionaries.
    
        - Valid types to extract: 'standalone_keyterm', 'parented_keyterm', 'named_entity'.        
        - If types_to_extract and/or entity_names_to_extract are None, all types/entities are extracted.
        - The returned position ranges ignore other annotations, ie. as if the other annotations did not exist.
        - Beware that the returned positions are meant to be used as ranges. annotated_text[5:14] might return
          the desired result while annotated_text[14] may encounter an index out of range exception.
    """

    # ensure that types_to_extract has valid entries
    if term_types_to_extract:
        for type_to_extract in term_types_to_extract:
            if type_to_extract not in [
                "standalone_keyterm",
                "parented_keyterm",
                "standalone_named_entity",
            ]:
                raise ValueError(
                    "At least one entry in param 'types_to_extract' is invalid. Ensure that only valid types are used."
                )

    result = []
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(SK|PK|SN))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        # compute full result
        term = match.group("term")
        term_type_long = TINY_TO_LONG_ANNOTATION_TYPE_MAPPING.get(
            match.group("term_type_tiny")
        )
        postfix = match.group("postfix")
        start_position = len(
            remove_all_annotations_from_text(annotated_text[: match.start()])
        )
        end_position = start_position + len(
            remove_all_annotations_from_text(
                annotated_text[match.start() : match.end()]
            )
        )
        dict_to_add = {
            "term": term,
            "start": start_position,
            "end": end_position,
            "term_type_long": term_type_long,
        }
        if term_type_long == "parented_keyterm":
            dict_to_add["parent_terms"] = postfix
        if term_type_long == "standalone_named_entity":
            dict_to_add["entity_name"] = postfix
        result.append(dict_to_add)
        # apply filters if needed
        if term_types_to_extract:
            result = [
                item
                for item in result
                if item["term_type_long"] in term_types_to_extract
            ]
        if entity_names_to_extract:
            result = [
                item
                for item in result
                if item["term_type_long"] != "standalone_named_entity"
                or (
                    item["term_type_long"] == "standalone_named_entity"
                    and "entity_name" in item
                    and item["entity_name"] in entity_names_to_extract
                )
            ]
    return result


def extract_annotations_as_text(
    annotated_text, external_annotations_to_add=[], include_entity_names=True
):

    # TODO: reuse extract_annotations_as_list to support once and only once

    result_list = []
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(SK|PK|SN))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        term = match.group("term")
        term_type_tiny = match.group("term_type_tiny")
        term_type_long = TINY_TO_LONG_ANNOTATION_TYPE_MAPPING.get(term_type_tiny)
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
            parent_terms_str = match.group("postfix") or ""
            for parent_term in set(
                [parent_term.strip() for parent_term in parent_terms_str.split(",")]
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
        if term_type_long == "standalone_named_entity":
            entity_name = match.group("postfix")
            annotation_to_add = (
                "{}:{}".format(entity_name.lower(), term)
                if include_entity_names
                else term
            )
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


def extract_annotations_by_term_type(
    annotated_text,
    term_types_to_extract=None,
    entity_names_to_extract=None,
    list_aliases={
        "standalone_keyterms": "standalone_keyterms",
        "parented_keyterms": "parented_keyterms",
        "standalone_named_entities": "standalone_named_entities",
    },
):
    """ Returns all annotations and their position ranges from an annotated text.
    
        - Valid types to extract: 'standalone_keyterm', 'parented_keyterm', 'named_entity'.        
        - If types_to_extract and/or entity_names_to_extract are None, all types/entities are extracted.
        - The returned position ranges ignore other annotations, ie. as if the other annotations did not exist.
        - Beware that the returned positions are meant to be used as ranges. annotated_text[5:14] might return
          the desired result while annotated_text[14] may encounter an index out of range exception.
        - Use parameter list_aliases to control the name(s) of the lists in the result."""

    # TODO: reuse extract_annotations_as_list to support once and only once

    # ensure that types_to_extract has valid entries
    if term_types_to_extract:
        for type_to_extract in term_types_to_extract:
            if type_to_extract not in [
                "standalone_keyterm",
                "parented_keyterm",
                "standalone_named_entity",
            ]:
                raise ValueError(
                    "At least one entry in param 'types_to_extract' is invalid. Ensure that only valid types are used."
                )

    # get plain text without annotations
    plain_text = remove_all_annotations_from_text(annotated_text)

    # match all annotations and assemble the relevant annotations
    annotations = {}
    standalone_keyterms = []
    parented_keyterms = []
    named_entities = []
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(SK|PK|SN))( (?P<postfix>[^()]+?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        start_position = len(
            remove_all_annotations_from_text(annotated_text[: match.start()])
        )
        end_position = start_position + len(
            remove_all_annotations_from_text(
                annotated_text[match.start() : match.end()]
            )
        )
        if match.group("term_type_tiny") == "SK" and (
            term_types_to_extract is None
            or "standalone_keyterm" in term_types_to_extract
        ):
            standalone_keyterms.append((start_position, end_position))
        if match.group("term_type_tiny") == "PK" and (
            term_types_to_extract is None or "parented_keyterm" in term_types_to_extract
        ):
            parented_keyterms.append(
                (start_position, end_position, match.group("postfix"))
            )
        if (
            match.group("term_type_tiny") == "SN"
            and (
                term_types_to_extract is None
                or "standalone_named_entity" in term_types_to_extract
            )
            and (
                entity_names_to_extract is None
                or match.group("postfix") in entity_names_to_extract
            )
        ):
            named_entities.append(
                (start_position, end_position, match.group("postfix"))
            )
    if len(standalone_keyterms) > 0:
        annotations[list_aliases["standalone_keyterms"]] = standalone_keyterms
    if len(parented_keyterms) > 0:
        annotations[list_aliases["parented_keyterms"]] = parented_keyterms
    if len(named_entities) > 0:
        annotations[list_aliases["standalone_named_entities"]] = named_entities

    # return result
    return (plain_text, annotations)


def get_annotation_at_position(annotated_text, position):
    result = None
    for match in re.finditer(
        r"\((?P<term>[^()]+?)\|(?P<term_type_tiny>(SK|PK|SN))( (?P<postfix>[^()]*?))?\)",
        annotated_text,
        flags=re.DOTALL,
    ):
        if not (match.start() < position < match.end()):
            continue
        term = match.group("term")
        term_type_long = TINY_TO_LONG_ANNOTATION_TYPE_MAPPING.get(
            match.group("term_type_tiny")
        )
        postfix = match.group("postfix") or ""
        start_position = len(
            remove_all_annotations_from_text(annotated_text[: match.start()])
        )
        end_position = start_position + len(
            remove_all_annotations_from_text(
                annotated_text[match.start() : match.end()]
            )
        )
        result = {
            "term": term,
            "start": start_position,
            "end": end_position,
            "term_type_long": term_type_long,
        }
        if term_type_long == "parented_keyterm":
            result["parent_terms"] = postfix
        if term_type_long == "standalone_named_entity":
            result["entity_name"] = postfix
    return result


def remove_all_annotations_from_text(annotated_text):
    new_text = re.sub(
        r"\((.*?)\|(((PK|SN) .+?)|(SK))\)",
        lambda match: match.group(1),
        annotated_text,
        flags=re.DOTALL,
    )
    return new_text


def mask_annotations(text):
    return re.sub(
        r"\(.*?\|(SK|PK .*?|SN .*?)\)",
        lambda match: "@neanno_masked_annotation:{}@".format(
            base64.b64encode(match.group().encode("utf-8")).decode()
        ),
        text,
    )


def unmask_annotations(text_with_masked_annotations):
    return re.sub(
        r"@neanno_masked_annotation:(?P<base64string>.*?)@",
        lambda match: base64.b64decode(match.group("base64string")).decode(),
        text_with_masked_annotations,
    )


def extract_named_entities_distribution(annotated_text):
    """ Computes the types and frequencies of named entities in the specified text."""
    result = {}
    find_entities_pattern = r"\((?P<term>.+?)\|SN (?P<label>.+?)\)"
    for entity in re.findall(find_entities_pattern, annotated_text):
        entity_code = entity[1]
        if entity_code not in result:
            result[entity_code] = 0
        result[entity_code] += 1
    return result
