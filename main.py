import pandas as pd

from neanno import NamedEntityDefinition, annotate_entities


def main():
    # load pandas data frame
    some_dataframe_with_texts = pd.DataFrame.from_records(
        [
            (
                "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",
            ),
            (
                "Auch gibt es niemanden, der den Schmerz an sich liebt, sucht oder wünscht, nur, weil er Schmerz ist, es sei denn, es kommt zu zufälligen Umständen, in denen Mühen und Schmerz ihm große Freude bereiten können. Um ein triviales Beispiel zu nehmen, wer von uns unterzieht sich je anstrengender körperlicher Betätigung, außer um Vorteile daraus zu ziehen?",
            ),
            (
                "Weit hinten, hinter den Wortbergen, fern der Länder Vokalien und Konsonantien leben die Blindtexte. Abgeschieden wohnen sie in Buchstabhausen an der Küste des Semantik, eines großen Sprachozeans. Ein kleines Bächlein namens Duden fließt durch ihren Ort und versorgt sie mit den nötigen Regelialien. Es ist ein paradiesmatisches Land, in dem einem gebratene Satzteile in den Mund fliegen.",
            ),
            (
                "Überall dieselbe alte Leier. Das Layout ist fertig, der Text lässt auf sich warten. Damit das Layout nun nicht nackt im Raume steht und sich klein und leer vorkommt, springe ich ein: der Blindtext. Genau zu diesem Zwecke erschaffen, immer im Schatten meines großen Bruders »Lorem Ipsum«, freue ich mich jedes Mal, wenn Sie ein paar Zeilen lesen. Denn esse est percipi - Sein ist wahrgenommen werden.",
            ),
            (
                "Er hörte leise Schritte hinter sich. Das bedeutete nichts Gutes. Wer würde ihm schon folgen, spät in der Nacht und dazu noch in dieser engen Gasse mitten im übel beleumundeten Hafenviertel? Gerade jetzt, wo er das Ding seines Lebens gedreht hatte und mit der Beute verschwinden wollte! Hatte einer seiner zahllosen Kollegen dieselbe Idee gehabt, ihn beobachtet und abgewartet, um ihn nun um die Früchte seiner Arbeit zu erleichtern?",
            ),
        ],
        columns=["Text"],
    )

    # declare the named entities to annotate
    named_entity_definitions = [
        NamedEntityDefinition("BLU", "Alt+B", "#153465"),
        NamedEntityDefinition("RED", "Alt+R", "#67160e"),
        NamedEntityDefinition("GRN", "Alt+G", "#135714"),
        NamedEntityDefinition("PRP", "Alt+P", "#341b4d"),
        NamedEntityDefinition("ORG", "Alt+O", "#b45c18"),
        NamedEntityDefinition("YLW", "Alt+Y", "#b0984f"),
    ]

    # run the annotation UI
    annotate_entities(
        some_dataframe_with_texts,
        named_entity_definitions,
        save_callback=lambda df: df.to_csv(
            "annotated_texts.csv", index=False, header=True
        ),
    )


if __name__ == "__main__":
    main()
