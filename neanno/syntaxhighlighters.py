import config
from PyQt5.QtCore import QRegularExpression, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
)


class TextEditHighlighter(QSyntaxHighlighter):
    """Used to highlight the entities in the text field."""

    highlighting_rules = []

    def __init__(self, parent, named_definitions):
        super(TextEditHighlighter, self).__init__(parent)
        postfix_format = self.get_text_char_format(QColor("lightgrey"), Qt.black)
        postfix_format.setFontFamily("Segoe UI")
        postfix_format.setFontWeight(QFont.Bold)
        postfix_format.setFontPointSize(9)
        postfix_format_blank = self.get_text_char_format(
            QColor("lightgrey"), QColor("lightgrey")
        )

        # append highlighting rules
        term_text_format = self.get_text_char_format(
            config.key_terms_backcolor, config.key_terms_forecolor
        )
        term_text_format_blank = self.get_text_char_format(
            config.key_terms_backcolor, config.key_terms_backcolor
        )
        # standalone key terms
        self.highlighting_rules.append(
            (
                QRegularExpression(
                    r"(?<openParen>\()"
                    + r"(?<text>[^|()]+?)"
                    + r"(?<pipeAndType>\|SK)"
                    + r"(?<closingParen>\))"
                ),
                term_text_format,
                term_text_format_blank,
                term_text_format_blank,
                term_text_format_blank,
            )
        )
        # parented key terms
        self.highlighting_rules.append(
            (
                QRegularExpression(
                    r"(?<openParen>\()"
                    + r"(?<text>[^|()]+?)"
                    + r"(?<pipeAndType>\|PK)"
                    + r"(?<postfix> "
                    + r".*?"
                    + r")(?<closingParen>\))"
                ),
                term_text_format,
                term_text_format_blank,
                postfix_format,
                postfix_format_blank,
            )
        )
        # named entities
        for named_definition in named_definitions:
            entity_text_format = self.get_text_char_format(
                named_definition.backcolor, named_definition.forecolor
            )
            entity_text_format_blank = self.get_text_char_format(
                named_definition.backcolor, named_definition.backcolor
            )
            self.highlighting_rules.append(
                (
                    QRegularExpression(
                        r"(?<openParen>\()"
                        + r"(?<text>[^|()]+?)"
                        + r"(?<pipeAndType>\|NE)"
                        + r"(?<postfix> "
                        + named_definition.code
                        + r")(?<closingParen>\))"
                    ),
                    entity_text_format,
                    entity_text_format_blank,
                    postfix_format,
                    postfix_format_blank,
                )
            )

    def get_text_char_format(self, backcolor, forecolor):
        result = QTextCharFormat()
        result.setBackground(QColor(backcolor))
        result.setForeground(QColor(forecolor))
        return result

    def highlightBlock(self, text):
        for (
            pattern,
            text_format,
            text_format_blank,
            postfix_format,
            postfix_format_blank,
        ) in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            offset = 0
            while offset >= 0:
                match = expression.match(text, offset)
                self.setFormat(match.capturedStart("openParen"), 1, text_format_blank)
                self.setFormat(
                    match.capturedStart("text"),
                    match.capturedLength("text"),
                    text_format,
                )
                self.setFormat(
                    match.capturedStart("pipeAndType"),
                    match.capturedLength("pipeAndType"),
                    text_format_blank,
                )
                self.setFormat(
                    match.capturedStart("postfix"),
                    match.capturedLength("postfix"),
                    postfix_format,
                )
                self.setFormat(
                    match.capturedStart("closingParen"), 1, postfix_format_blank
                )
                offset = match.capturedEnd("closingParen")
