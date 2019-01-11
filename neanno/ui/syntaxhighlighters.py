import config
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from neanno.utils.text import extract_annotations_as_generator


class TextEditHighlighter(QSyntaxHighlighter):
    """Used to highlight annotations in a text field."""

    format_info = {}

    def __init__(self, parent, named_definitions):
        super(TextEditHighlighter, self).__init__(parent)

        # populate format infos
        self.format_info = {
            "standalone_key_term": {
                "backcolor": config.key_terms_backcolor,
                "forecolor": config.key_terms_forecolor,
                "show_postfix": False,
            },
            "parented_key_term": {
                "backcolor": config.key_terms_backcolor,
                "forecolor": config.key_terms_forecolor,
                "show_postfix": True,
            },
            "standalone_named_entity": {},
        }
        for named_definition in named_definitions:
            self.format_info["standalone_named_entity"][named_definition.code] = {
                "backcolor": named_definition.backcolor,
                "forecolor": named_definition.forecolor,
                "show_postfix": True,
            }

    def highlightBlock(self, text):
        for annotation in extract_annotations_as_generator(text):
            # get formats
            format_info_to_apply = (
                self.format_info[annotation["type"]][annotation["entity_name"]]
                if annotation["type"] == "standalone_named_entity"
                else self.format_info[annotation["type"]]
            )
            backcolor = format_info_to_apply["backcolor"]
            forecolor = format_info_to_apply["forecolor"]
            show_postfix = format_info_to_apply["show_postfix"]
            
            open_paren_format = self.get_text_char_format(backcolor, backcolor, 100 / 3)
            term_format = self.get_text_char_format(backcolor, forecolor)
            pipe_format = self.get_text_char_format(backcolor, backcolor, 100 / 3)
            postfix_background_color = "lightgrey"
            postfix_foreground_color = "black"
            type_format = self.get_text_char_format(
                postfix_background_color if show_postfix else backcolor,
                postfix_background_color if show_postfix else backcolor,
                100 / 4,
                "Segoe UI",
                QFont.Bold,
                9,
            )
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
                    postfix_background_color, postfix_background_color, 100 / 4
                )
                if show_postfix
                else self.get_text_char_format(backcolor, backcolor, 1)
            )

            # set formats
            # opening parenthesis
            from_position = annotation["start_gross"]
            length = len("´<`")
            self.setFormat(from_position, length, open_paren_format)
            # term
            from_position += length
            length = len(annotation["term"])
            self.setFormat(from_position, length, term_format)
            # pipe
            from_position += length
            length = len("´|`")
            self.setFormat(from_position, length, pipe_format)
            # type
            from_position += length
            length = len("XX ")
            self.setFormat(from_position, length, type_format)
            # postfix
            from_position += length
            length = annotation["end_gross"] - (from_position + length)
            self.setFormat(from_position, length, postfix_text_format)
            # closing parenthesis
            from_position += length
            length = len("´>`")
            self.setFormat(from_position, length, closing_paren_format)

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
