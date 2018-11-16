import spacy
from spacy.gold import GoldParse
from spacy.scorer import Scorer


def evaluate(ner_model, examples):
    scorer = Scorer()
    for input_, annot in examples:
        doc_gold_text = ner_model.make_doc(input_)
        gold = GoldParse(doc_gold_text, entities=annot)
        pred_value = ner_model(input_)
        scorer.score(pred_value, gold)
    return scorer.scores


# example run

examples = [
    ("Who is Shaka Khan?", [(7, 17, "PERSON")]),
    ("I like London and Berlin.", [(7, 13, "LOC"), (18, 24, "LOC")]),
]

ner_model = spacy.load("en_core_web_sm")  # for spaCy's pretrained use 'en_core_web_sm'
results = evaluate(ner_model, examples)
print(results)

text = u"Bill Clinton and Barack Obama met yesterday in the White House."
someDoc = ner_model(text)
result = text
shift = 0
for e in someDoc.ents:
    oldResultLength = len(result)
    result = "{}{}{}".format(
        result[: e.start_char + shift],
        "({}| {})".format(e.text, e.label_),
        result[e.end_char + shift :],
    )
    shift += len(result) - oldResultLength

print(result)

