import config
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from neanno.utils.text import extract_annotations_as_generator


class TextEditHighlighter(QSyntaxHighlighter):
    """Used to highlight annotations in a text field."""

    text_char_formats = {}

    ENTITY_CODE_BACKGROUND_COLOR = "white"
    ENTITY_CODE_FOREGROUND_COLOR = "black"
    PARENT_TERMS_BACKGROUND_COLOR = "lightgrey"
    PARENT_TERMS_FOREGROUND_COLOR = "black"

    def __init__(self, parent, named_definitions):
        super(TextEditHighlighter, self).__init__(parent)

        # populate formats
        self.text_char_formats = {
            "key_term": {
                "term": self.get_text_char_format(
                    config.key_terms_backcolor, config.key_terms_forecolor
                ),
                "parent_terms": self.get_text_char_format(
                    self.PARENT_TERMS_BACKGROUND_COLOR,
                    self.PARENT_TERMS_FOREGROUND_COLOR,
                    None,
                    "Segoe UI",
                    QFont.Bold,
                    9,
                ),
            },
            "named_entity": {},
        }
        for named_definition in named_definitions:
            self.text_char_formats["named_entity"][named_definition.code] = {
                "term": self.get_text_char_format(
                    named_definition.backcolor, named_definition.forecolor
                ),
                "entity_code": self.get_text_char_format(
                    self.ENTITY_CODE_BACKGROUND_COLOR,
                    self.ENTITY_CODE_FOREGROUND_COLOR,
                    None,
                    "Segoe UI",
                    QFont.Bold,
                    9,
                ),
                "parent_terms": self.get_text_char_format(
                    self.PARENT_TERMS_BACKGROUND_COLOR,
                    self.PARENT_TERMS_FOREGROUND_COLOR,
                    None,
                    "Segoe UI",
                    QFont.Bold,
                    9,
                ),
            }

    def highlightBlock(self, text):
        for annotation in extract_annotations_as_generator(
            text, entity_codes_to_extract=config.named_entity_codes
        ):
            # get common format infos
            format_to_apply = (
                self.text_char_formats["key_term"]
                if "key_term" in annotation["type"]
                else self.text_char_formats["named_entity"][annotation["entity_code"]]
            )
            # set formats
            # space before term
            start_pos = annotation["start_gross"]
            length = 1
            format = self.no_chars(format_to_apply["term"])
            self.setFormat(start_pos, length, format)
            # term
            start_pos += length
            length = len(annotation["term"])
            format = format_to_apply["term"]
            self.setFormat(start_pos, length, format)
            # space after term
            start_pos += length
            length = 1
            format = self.no_chars(format_to_apply["term"])
            self.setFormat(start_pos, length, format)
            # type
            start_pos += length
            length = 4
            format = self.as_invisible_as_possible(
                self.no_chars(format_to_apply["term"])
            )
            self.setFormat(start_pos, length, format)
            if "named_entity" in annotation["type"]:
                # space before named entity
                start_pos += length
                length = 1
                format = self.no_chars(format_to_apply["entity_code"])
                self.setFormat(start_pos, length, format)
                # named entity
                start_pos += length
                length = len(annotation["entity_code"])
                format = format_to_apply["entity_code"]
                self.setFormat(start_pos, length, format)
                # space after named entity
                start_pos += length
                length = 1
                format = self.no_chars(format_to_apply["entity_code"])
                self.setFormat(start_pos, length, format)
            if "parented" in annotation["type"]:
                # space before parent terms
                start_pos += length
                length = 1
                format = self.no_chars(format_to_apply["parent_terms"])
                self.setFormat(start_pos, length, format)
                # parent terms
                start_pos += length
                length = len(annotation["parent_terms_raw"])#annotation["end_gross"] - (start_pos + len("`´"))
                format = format_to_apply["parent_terms"]
                self.setFormat(start_pos, length, format)
                # space after parent terms
                start_pos += length
                length = 1
                format = self.no_chars(format_to_apply["parent_terms"])
                self.setFormat(start_pos, length, format)
            # terminal char
            start_pos += length
            length = 1
            format = self.as_invisible_as_possible(self.no_chars(format))
            self.setFormat(start_pos, length, format)

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

    def no_chars(self, text_char_format):
        result = QTextCharFormat(text_char_format)
        result.setForeground(result.background())
        return result

    def as_invisible_as_possible(self, text_char_format):
        result = QTextCharFormat(text_char_format)
        result.setFontStretch(1)
        return result
