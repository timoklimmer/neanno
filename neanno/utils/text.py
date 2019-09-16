import base64
import re
from collections import Counter
from functools import reduce

import pandas as pd

from neanno.utils.dict import merge_dict_sum_numbers
from neanno.utils.list import ensure_items_within_set, get_set_of_list_and_keep_sequence

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
        (?(standalone_named_entity)``(?P<entity_code_sn>.*?))
        (?(parented_named_entity)``(?P<entity_code_pn>.*?)``(?P<parent_terms_pn>.*?))
        `´
    """
)


def extract_annotations_as_generator(
    annotated_text, types_to_extract=None, entity_codes_to_extract=None
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
            annotation["entity_code"] = match.group("entity_code_sn")
            if (
                entity_codes_to_extract is not None
                and annotation["entity_code"] not in entity_codes_to_extract
            ):
                continue
        if annotation["type"] == "parented_named_entity":
            annotation["entity_code"] = match.group("entity_code_pn")
            if (
                entity_codes_to_extract is not None
                and annotation["entity_code"] not in entity_codes_to_extract
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
    annotated_text, types_to_extract=None, entity_codes_to_extract=None
):
    """ Extracts a list of annotations in the specified text."""
    return [
        annotation
        for annotation in extract_annotations_as_generator(
            annotated_text,
            types_to_extract=types_to_extract,
            entity_codes_to_extract=entity_codes_to_extract,
        )
    ]


def extract_annotations_as_text(
    annotated_text,
    external_annotations_to_add=[],
    entity_codes_to_extract=None,
    include_entity_codes=True,
):
    """Extracts all annotations from the specified text and returns a string describing the set of contained annotations."""

    result_list = []
    for annotation in extract_annotations_as_generator(
        annotated_text, entity_codes_to_extract=entity_codes_to_extract
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
            for parent_term in get_set_of_list_and_keep_sequence(
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
                "{}:{}".format(annotation["entity_code"].lower(), annotation["term"])
                if include_entity_codes
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
            for parent_term in get_set_of_list_and_keep_sequence(
                annotation["parent_terms"].split(", ")
            ):
                annotation_to_add = (
                    "{}:{}".format(annotation["entity_code"].lower(), parent_term)
                    if include_entity_codes
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
    entity_codes_to_extract=None,
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


def extract_entity_codes_from_annotated_texts_column(annotated_texts_column):
    """ Extracts the set of all entity codes that appear in the texts of the specified column (pandas series)."""
    result = []
    for (index, annotated_text) in annotated_texts_column.iteritems():
        for annotation in extract_annotations_as_generator(
            annotated_text,
            types_to_extract=["standalone_named_entity", "parented_named_entity"],
        ):
            if annotation["entity_code"] not in result:
                result.append(annotation["entity_code"])
    result.sort()
    return result


def extract_categories_from_categories_column(categories_column):
    """ Extracts the set of all categories that appear in the specified categories column (pandas series)."""
    result = []
    for (index, categories_column_text) in categories_column.iteritems():
        for category in categories_column_text.split("|"):
            if category not in result:
                result.append(category)
    result.sort()
    return result


def extract_annotations_for_spacy_ner(annotated_text, entity_codes_to_extract=None):
    """ Returns a tuple which for the specified text that can be used to train a named entity recognition (NER) with spacy."""

    # get plain text without annotations
    plain_text = remove_all_annotations_from_text(annotated_text)

    # get the annotations dictionary
    annotations = []
    for annotation in extract_annotations_as_generator(
        annotated_text,
        types_to_extract=["standalone_named_entity", "parented_named_entity"],
        entity_codes_to_extract=entity_codes_to_extract,
    ):
        annotations.append(
            (annotation["start_net"], annotation["end_net"], annotation["entity_code"])
        )

    # return result
    return (plain_text, {"entities": annotations})


def get_annotation_at_position(annotated_text, position):
    """ Gets the annotation which is at the specified position. Returns None if that position is not an annotation."""

    result = None
    for annotation in extract_annotations_as_generator(annotated_text):
        if not (annotation["start_gross"] < position < annotation["end_gross"]):
            continue
        else:
            return annotation


def has_annotation_within_range(annotated_text, start_position, end_position):
    """ Checks if the specified range overlaps with an annotation. """

    for annotation in extract_annotations_as_generator(annotated_text):
        if not (
            (
                start_position < annotation["start_gross"]
                and end_position < annotation["start_gross"]
            )
            or (
                start_position > annotation["start_gross"]
                and start_position > annotation["end_gross"]
            )
        ):
            # there is an overlap => return True
            return True
    # no overlap found => return False
    return False


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


def compute_named_entities_distribution_from_text(annotated_text):
    """ Computes the types and frequencies of named entities in the specified text."""

    result = {}
    for entity_annotation in extract_annotations_as_generator(
        annotated_text,
        types_to_extract=["standalone_named_entity", "parented_named_entity"],
    ):
        entity_code = entity_annotation["entity_code"]
        if entity_code not in result:
            result[entity_code] = 0
        result[entity_code] += 1
    return result


def compute_named_entities_distribution_from_column(pandas_series):
    """ Computes the distribution over all named entities in the specified text column."""

    distribution_candidate = pandas_series.map(
        lambda text: compute_named_entities_distribution_from_text(text)
    ).agg(
        lambda series: reduce(
            lambda dist1, dist2: merge_dict_sum_numbers(dist1, dist2), series
        )
    )
    return (
        distribution_candidate
        if not isinstance(distribution_candidate, pd.Series)
        else {}
    )


def compute_categories_distribution_from_column(pandas_series):
    """ Computes the distribution over all categories in the specified categories column."""

    distribution_candidate = pandas_series.map(
        lambda categories_text: Counter(categories_text.split("|"))
    ).agg(
        lambda series: reduce(
            lambda dist1, dist2: merge_dict_sum_numbers(dist1, dist2), series
        )
    )
    return (
        dict(distribution_candidate)
        if not isinstance(distribution_candidate, pd.Series)
        else {}
    )


def compute_term_distribution_from_text(
    annotated_text, blacklist_terms=[], include_entity_codes=True
):
    """ Computes all terms and their frequencies from the specified text."""

    def relevant_terms_from_match(match):
        if match.group("type_tiny") == "SK":
            return re.sub(" ", chr(127), match.group("term"))
        if match.group("type_tiny") == "SN":
            return re.sub(
                " ",
                chr(127),
                "{}:{}".format(match.group("entity_code_sn"), match.group("term"))
                if include_entity_codes
                else "{}".format(match.group("term")),
            )
        if match.group("type_tiny") == "PK":
            return " ".join(
                [
                    re.sub(" ", chr(127), parent_term.strip())
                    for parent_term in match.group("parent_terms_pk").split(",")
                ]
            )
        if match.group("type_tiny") == "PN":
            return " ".join(
                [
                    re.sub(
                        " ",
                        chr(127),
                        "{}:{}".format(
                            match.group("entity_code_pn"), parent_term.strip()
                        )
                        if include_entity_codes
                        else "{}".format(parent_term.strip()),
                    )
                    for parent_term in match.group("parent_terms_pn").split(",")
                ]
            )

    cleaned_text = annotated_text.strip()
    cleaned_text = re.sub(r"(?m)\s+", " ", cleaned_text)
    cleaned_text = mask_annotations(cleaned_text)
    cleaned_text = re.sub(r"([.,?!<>\[\]\|\"\(\)\+\-])", "", cleaned_text)
    cleaned_text = unmask_annotations(cleaned_text)
    cleaned_text = re.sub(
        ANNOTATION_REGEX, lambda match: relevant_terms_from_match(match), cleaned_text
    )
    result = {}
    for term in cleaned_text.split(" "):
        term = re.sub(chr(127), " ", term)
        if re.match(r"^\d+$", term):
            continue
        if term in blacklist_terms:
            continue
        if term not in result:
            result[term] = 0
        result[term] += 1
    return result


def compute_term_distribution_from_column(
    pandas_series, blacklist_terms=[], include_entity_codes=True
):
    """ Computes the distribution over all terms in the specified text column."""

    distribution_candidate = pandas_series.map(
        lambda text: compute_term_distribution_from_text(
            text, blacklist_terms, include_entity_codes
        )
    ).agg(
        lambda series: reduce(
            lambda dist1, dist2: merge_dict_sum_numbers(dist1, dist2), series
        )
    )
    return (
        distribution_candidate
        if not isinstance(distribution_candidate, pd.Series)
        else {}
    )


def replace_from_to(text, start_position, end_position, new_text):
    """ Replaces the substring within the given range against another text."""
    return "{}{}{}".format(text[:start_position], new_text, text[end_position:])


def add_standalone_key_term(text, start_position, end_position):
    """ Annotates the given range as a standalone key term (as long as there is no other annotation yet)."""
    if not has_annotation_within_range(text, start_position, end_position):
        return replace_from_to(
            text,
            start_position,
            end_position,
            "`{}``SK`´".format(text[start_position:end_position]),
        )
    else:
        return text


def add_parented_key_term(text, start_position, end_position, parent_terms):
    """ Annotates the given range as a parented key term (as long as there is no other annotation yet)."""
    if not has_annotation_within_range(text, start_position, end_position):
        return replace_from_to(
            text,
            start_position,
            end_position,
            "`{}``PK``{}`´".format(text[start_position:end_position], parent_terms),
        )
    else:
        return text


def add_standalone_named_entity(text, start_position, end_position, entity_code):
    """ Annotates the given range as a standalone named entity (as long as there is no other annotation yet)."""
    if not has_annotation_within_range(text, start_position, end_position):
        return replace_from_to(
            text,
            start_position,
            end_position,
            "`{}``SN``{}`´".format(text[start_position:end_position], entity_code),
        )
    else:
        return text


def add_parented_named_entity(
    text, start_position, end_position, entity_code, parent_terms
):
    """ Annotates the given range as a parented named entity (as long as there is no other annotation yet)."""

    if not has_annotation_within_range(text, start_position, end_position):
        return replace_from_to(
            text,
            start_position,
            end_position,
            "`{}``PN``{}``{}`´".format(
                text[start_position:end_position], entity_code, parent_terms
            ),
        )
    else:
        return text


def annotate_text(text, annotations):
    """ Annotates the given text with the given annotations."""

    # sort all annotations to make the algorithm below work
    sorted_annotations = sorted(
        annotations, key=lambda annotation: int(annotation["start_gross"])
    )

    # iterate through all (sorted) annotations and add the annotations to the text
    shift = 0
    for annotation in sorted_annotations:
        start_net = int(annotation["start_net"])
        end_net = int(annotation["end_net"])
        old_text_length = len(text)

        # standalone_key_term
        if annotation["type"] == "standalone_key_term":
            text = add_standalone_key_term(text, shift + start_net, shift + end_net)
        # parented_key_term
        if annotation["type"] == "parented_key_term":
            text = add_parented_key_term(
                text, shift + start_net, shift + end_net, annotation["parent_terms"]
            )
        # standalone_named_entity
        if annotation["type"] == "standalone_named_entity":
            text = add_standalone_named_entity(
                text, shift + start_net, shift + end_net, annotation["entity_code"]
            )
        # parented_named_entity
        if annotation["type"] == "parented_named_entity":
            text = add_parented_named_entity(
                text,
                shift + start_net,
                shift + end_net,
                annotation["entity_code"],
                annotation["parent_terms"],
            )

        # update shift
        shift += len(text) - old_text_length

    # return the result
    return text


def normalize_labels_values(pandas_series):
    """Normalizes the labels in the passed column so multiple label columns can be compared."""
    return pandas_series.map(lambda labels: "|".join(sorted(labels.split("|"))))

