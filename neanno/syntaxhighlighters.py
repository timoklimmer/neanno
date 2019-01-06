import config
from PyQt5.QtCore import QRegularExpression, Qt
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class TextEditHighlighter(QSyntaxHighlighter):
    """Used to highlight the entities in the text field."""

    highlighting_rules = []

    def __init__(self, parent, named_definitions):
        super(TextEditHighlighter, self).__init__(parent)

        # append highlighting rules
        if config.is_key_terms_enabled:
            # standalone key terms
            self.highlighting_rules.append(
                (
                    QRegularExpression(
                        r"(?<openParen>\()"
                        + r"(?<term>[^|()]+?)"
                        + r"(?<pipeAndType>\|SK)"
                        + r"(?<closingParen>\))"
                    ),
                    config.key_terms_backcolor,
                    config.key_terms_forecolor,
                    False,
                )
            )
            # parented key terms
            self.highlighting_rules.append(
                (
                    QRegularExpression(
                        r"(?<openParen>\()"
                        + r"(?<term>[^|()]+?)"
                        + r"(?<pipeAndType>\|PK)"
                        + r"(?<postfix> "
                        + r".*?"
                        + r")(?<closingParen>\))"
                    ),
                    config.key_terms_backcolor,
                    config.key_terms_forecolor,
                    True,
                )
            )
        # named entities
        for named_definition in named_definitions:
            self.highlighting_rules.append(
                (
                    QRegularExpression(
                        r"(?<openParen>\()"
                        + r"(?<term>[^|()]+?)"
                        + r"(?<pipeAndType>\|SN)"
                        + r"(?<postfix> "
                        + named_definition.code
                        + r")(?<closingParen>\))"
                    ),
                    named_definition.backcolor,
                    named_definition.forecolor,
                    True,
                )
            )

    def highlightBlock(self, text):
        for (pattern, backcolor, forecolor, show_postfix) in self.highlighting_rules:
            open_paren_format = self.get_text_char_format(backcolor, backcolor)
            text_format = self.get_text_char_format(backcolor, forecolor)
            pipeAndType_format = self.get_text_char_format(
                backcolor, backcolor, 10 if not show_postfix else 50
            )
            postfix_background_color = "lightgrey"
            postfix_foreground_color = "black"
            postfix_text_format = self.get_text_char_format(
                postfix_background_color,
                postfix_foreground_color,
                None,
                "Segoe UI",
                QFont.Bold,
                9,
            )
            closing_paren_format = (
                self.get_text_char_format(
                    postfix_background_color, postfix_background_color
                )
                if show_postfix
                else self.get_text_char_format(backcolor, backcolor)
            )

            expression = QRegularExpression(pattern)
            offset = 0
            while offset >= 0:
                match = expression.match(text, offset)
                self.setFormat(match.capturedStart("openParen"), 1, open_paren_format)
                self.setFormat(
                    match.capturedStart("term"),
                    match.capturedLength("term"),
                    text_format,
                )
                self.setFormat(
                    match.capturedStart("pipeAndType"),
                    match.capturedLength("pipeAndType"),
                    pipeAndType_format,
                )
                self.setFormat(
                    match.capturedStart("postfix"),
                    match.capturedLength("postfix"),
                    postfix_text_format,
                )
                self.setFormat(
                    match.capturedStart("closingParen"), 1, closing_paren_format
                )
                offset = match.capturedEnd("closingParen")

    def get_text_char_format(
        self,
        backcolor,
        forecolor,
        font_stretch=None,
        font_family=None,
        font_weight=None,
        font_size=None,
    ):
        result = QTextCharFormat()
        result.setBackground(QColor(backcolor))
        result.setForeground(QColor(forecolor))
        if font_stretch is not None:
            result.setFontStretch(font_stretch)
        if font_family is not None:
            result.setFontFamily(font_family)
        if font_weight is not None:
            result.setFontWeight(font_weight)
        if font_size is not None:
            result.setFontPointSize(font_size)
        return result
