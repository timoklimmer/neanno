import base64
import re

from neanno.utils.list import ensure_items_within_set, get_set_of_list_keep_sequence

ANNOTATION_TYPES = [
    "standalone_key_term",
    "parented_key_term",
    "standalone_named_entity",
    "parented_named_entity",
]

TINY_TO_LONG_ANNOTATION_TYPE_MAPPING = {
    "SK": "standalone_key_term",
    "PK": "parented_key_term",
    "SN": "standalone_named_entity",
    "PN": "parented_named_entity",
}

ANNOTATION_REGEX = re.compile(
    r"""(?xs)
        `
        (?P<term>[^`]*?)
        ``
        (?P<type_tiny>(
              (?P<standalone_key_term>SK)
            | (?P<parented_key_term>PK)
            | (?P<standalone_named_entity>SN)
            | (?P<parented_named_entity>PN))
        )
        (?(parented_key_term)``(?P<parent_terms_pk>.*?))
        (?(standalone_named_entity)``(?P<entity_name_sn>.*?))
        (?(parented_named_entity)``(?P<entity_name_pn>.*?)``(?P<parent_terms_pn>.*?))
        `´
    """
)


def extract_annotations_as_generator(
    annotated_text, types_to_extract=None, entity_names_to_extract=None
):
    """ Yields all annotations from an annotated text as a list."""

    def extract_normalized_parent_terms(parent_terms):
        result = []
        for parent_term in ((parent_terms or "").strip()).split(","):
            parent_term = parent_term.strip()
            if parent_term and parent_term not in result:
                result.append(parent_term)
        return ", ".join(result)

    # ensure that types_to_extract has valid entries
    ensure_items_within_set(types_to_extract, ANNOTATION_TYPES, True)

    result = []
    for match in re.finditer(ANNOTATION_REGEX, annotated_text):
        # assemble annotation and do the filtering in parallel
        annotation = {}
        annotation["term"] = match.group("term")
        annotation["type"] = TINY_TO_LONG_ANNOTATION_TYPE_MAPPING.get(
            match.group("type_tiny")
        )
        if types_to_extract is not None and annotation["type"] not in types_to_extract:
            continue
        if annotation["type"] == "standalone_named_entity":
            annotation["entity_name"] = match.group("entity_name_sn")
            if (
                entity_names_to_extract is not None
                and annotation["entity_name"] not in entity_names_to_extract
            ):
                continue
        if annotation["type"] == "parented_named_entity":
            annotation["entity_name"] = match.group("entity_name_pn")
            if (
                entity_names_to_extract is not None
                and annotation["entity_name"] not in entity_names_to_extract
            ):
                continue
            annotation["parent_terms_raw"] = match.group("parent_terms_pn")
            annotation["parent_terms"] = extract_normalized_parent_terms(
                annotation["parent_terms_raw"]
            )
        if annotation["type"] == "parented_key_term":
            annotation["parent_terms_raw"] = match.group("parent_terms_pk")
            annotation["parent_terms"] = extract_normalized_parent_terms(
                annotation["parent_terms_raw"]
            )
        annotation["start_net"] = len(
            remove_all_annotations_from_text(annotated_text[: match.start()])
        )
        annotation["end_net"] = annotation["start_net"] + len(
            remove_all_annotations_from_text(
                annotated_text[match.start() : match.end()]
            )
        )
        annotation["start_gross"] = match.start()
        annotation["end_gross"] = match.end()

        # yield annotation
        yield annotation


def extract_annotations_as_list(
    annotated_text, types_to_extract=None, entity_names_to_extract=None
):
    """ Extracts a list of annotations in the specified text."""
    return [
        annotation
        for annotation in extract_annotations_as_generator(
            annotated_text, types_to_extract=None, entity_names_to_extract=None
        )
    ]


def extract_annotations_as_text(
    annotated_text,
    external_annotations_to_add=[],
    entity_names_to_extract=None,
    include_entity_names=True,
):
    """Extracts all annotations from the specified text and returns a string describing the set of contained annotations."""

    result_list = []
    for annotation in extract_annotations_as_generator(
        annotated_text, entity_names_to_extract=entity_names_to_extract
    ):
        # standalone key term
        if annotation["type"] == "standalone_key_term":
            annotation_to_add = annotation["term"]
            if annotation_to_add.lower() not in [
                annotation.lower() for annotation in result_list
            ] and annotation_to_add.lower() not in [
                annotation.lower() for annotation in external_annotations_to_add
            ]:
                result_list.append(annotation_to_add)
        # parented key term
        if annotation["type"] == "parented_key_term":
            parent_terms = []
            for parent_term in get_set_of_list_keep_sequence(
                annotation["parent_terms"].split(", ")
            ):
                annotation_to_add = parent_term
                if annotation_to_add.lower() not in [
                    annotation.lower() for annotation in result_list
                ] and annotation_to_add.lower() not in [
                    annotation.lower() for annotation in external_annotations_to_add
                ]:
                    parent_terms.append(annotation_to_add)
            result_list.extend(sorted(parent_terms))
        # standalone named entity
        if annotation["type"] == "standalone_named_entity":
            annotation_to_add = (
                "{}:{}".format(annotation["entity_name"].lower(), annotation["term"])
                if include_entity_names
                else annotation["term"]
            )
            if annotation_to_add.lower() not in [
                annotation.lower() for annotation in result_list
            ] and annotation_to_add.lower() not in [
                annotation.lower() for annotation in external_annotations_to_add
            ]:
                result_list.append(annotation_to_add)
        # parented named entity
        if annotation["type"] == "parented_named_entity":
            for parent_term in get_set_of_list_keep_sequence(
                annotation["parent_terms"].split(", ")
            ):
                annotation_to_add = (
                    "{}:{}".format(annotation["entity_name"].lower(), parent_term)
                    if include_entity_names
                    else parent_term
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


def extract_annotations_by_type(
    annotated_text,
    types_to_extract=None,
    entity_names_to_extract=None,
    list_aliases={
        "standalone_key_terms": "standalone_key_terms",
        "parented_key_terms": "parented_key_terms",
        "standalone_named_entities": "standalone_named_entities",
        "parented_named_entities": "parented_named_entities",
    },
):
    """ Returns all annotations and their position ranges from an annotated text."""

    # get plain text without annotations
    plain_text = remove_all_annotations_from_text(annotated_text)

    # get the annotations dictionary
    annotations = {}
    # standalone key terms
    if "standalone_key_term" in types_to_extract:
        annotations[list_aliases["standalone_key_terms"]] = extract_annotations_as_list(
            annotated_text, types_to_extract=["standalone_key_term"]
        )
    # parented key terms
    if "parented_key_term" in types_to_extract:
        annotations[list_aliases["parented_key_terms"]] = extract_annotations_as_list(
            annotated_text, types_to_extract=["parented_key_term"]
        )
    # standalone named entities
    if "standalone_named_entity" in types_to_extract:
        annotations[
            list_aliases["standalone_named_entities"]
        ] = extract_annotations_as_list(
            annotated_text, types_to_extract=["standalone_named_entity"]
        )
    # parented named entities
    if "parented_named_entity" in types_to_extract:
        annotations[
            list_aliases["parented_named_entities"]
        ] = extract_annotations_as_list(
            annotated_text, types_to_extract=["parented_named_entity"]
        )

    # return result
    return (plain_text, annotations)


def extract_annotations_for_spacy_ner(annotated_text, entity_names_to_extract=None):
    """ Returns a tuple which for the specified text that can be used to train a named entity recognition (NER) with spacy."""

    # get plain text without annotations
    plain_text = remove_all_annotations_from_text(annotated_text)

    # get the annotations dictionary
    annotations = []
    for annotation in extract_annotations_as_generator(
        annotated_text,
        types_to_extract=["standalone_named_entity", "parented_named_entity"],
        entity_names_to_extract=entity_names_to_extract,
    ):
        annotations.append(
            (annotation["start_net"], annotation["end_net"], annotation["entity_name"])
        )

    # return result
    return (plain_text, annotations)


def get_annotation_at_position(annotated_text, position):
    """ Gets the annotation which is at the specified position. Returns None if that position is not an annotation."""

    result = None
    for annotation in extract_annotations_as_generator(annotated_text):
        if not (annotation["start_gross"] < position < annotation["end_gross"]):
            continue
        else:
            return annotation


def remove_all_annotations_from_text(annotated_text):
    """Removes all annotations from the specified text."""

    new_text = re.sub(
        ANNOTATION_REGEX, lambda match: match.group("term"), annotated_text
    )
    return new_text


def mask_annotations(text):
    """Masks all annotations, eg. to avoid that terms which are already annotated are annotated again."""

    return re.sub(
        ANNOTATION_REGEX,
        lambda match: "@neanno_masked_annotation:{}@".format(
            base64.b64encode(match.group().encode("utf-8")).decode()
        ),
        text,
    )


def unmask_annotations(text_with_masked_annotations):
    """Reverts a previous masking of all annotations."""

    return re.sub(
        r"@neanno_masked_annotation:(?P<base64string>.*?)@",
        lambda match: base64.b64decode(match.group("base64string")).decode(),
        text_with_masked_annotations,
    )


def extract_named_entities_distribution(annotated_text):
    """ Computes the types and frequencies of named entities in the specified text."""

    result = {}
    for entity_annotation in extract_annotations_as_generator(
        annotated_text,
        types_to_extract=["standalone_named_entity", "parented_named_entity"],
    ):
        entity_code = entity_annotation["entity_name"]
        if entity_code not in result:
            result[entity_code] = 0
        result[entity_code] += 1
    return result
