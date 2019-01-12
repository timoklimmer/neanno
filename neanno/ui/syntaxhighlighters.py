import config
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from neanno.utils.text import extract_annotations_as_generator


class TextEditHighlighter(QSyntaxHighlighter):
    """Used to highlight annotations in a text field."""

    format_info = {}

    ENTITY_NAME_BACKGROUND_COLOR = "lightgrey"
    ENTITY_NAME_FOREGROUND_COLOR = "black"
    PARENT_TERMS_FOREGROUND_COLOR = "darkgrey"
    PARENT_TERMS_BACKGROUND_COLOR = "black"

    def __init__(self, parent, named_definitions):
        super(TextEditHighlighter, self).__init__(parent)

        # populate format infos
        self.format_info = {
            "standalone_key_term": {
                "main_backcolor": config.key_terms_backcolor,
                "main_forecolor": config.key_terms_forecolor,
                "show_entity_name": False,
                "show_key_terms": False
            },
            "parented_key_term": {
                "main_backcolor": config.key_terms_backcolor,
                "main_forecolor": config.key_terms_forecolor,
                "show_entity_name": False,
                "show_key_terms": True
            },
            "standalone_named_entity": {},
            "parented_named_entity": {},
        }
        for named_definition in named_definitions:
            self.format_info["standalone_named_entity"][named_definition.code] = {
                "main_backcolor": named_definition.backcolor,
                "main_forecolor": named_definition.forecolor,
                "show_entity_name": True,
                "show_key_terms": False
            }
            self.format_info["parented_named_entity"][named_definition.code] = {
                "main_backcolor": named_definition.backcolor,
                "main_forecolor": named_definition.forecolor,
                "show_entity_name": True,
                "show_key_terms": True
            }

    def highlightBlock(self, text):
        for annotation in extract_annotations_as_generator(text):
            # get common format infos
            format_info_to_apply = (
                self.format_info[annotation["type"]]
                if "named_entity" not in annotation["type"]
                else self.format_info[annotation["type"]][annotation["entity_name"]]
            )
            main_backcolor = format_info_to_apply["main_backcolor"]
            main_forecolor = format_info_to_apply["main_forecolor"]
            show_entity_name = format_info_to_apply["show_entity_name"]
            show_parent_terms = format_info_to_apply["show_parent_terms"]

            term_text_char_format = self.get_text_char_format(main_backcolor, main_forecolor)
            




            # set formats
            # opening parenthesis
            open_paren_format = self.get_text_char_format(
                main_backcolor, main_backcolor, int(100 / 3)
            )
            from_position = annotation["start_gross"]
            length = len("´<`")
            self.setFormat(from_position, length, open_paren_format)
            # term
            term_format = self.get_text_char_format(main_backcolor, main_forecolor)
            from_position += length
            length = len(annotation["term"])
            self.setFormat(from_position, length, term_format)
            # pipe
            pipe_format = self.get_text_char_format(
                main_backcolor, main_backcolor, int(100 / 3)
            )
            from_position += length
            length = len("´|`")
            self.setFormat(from_position, length, pipe_format)
            # type
            type_color = "red"
            type_format = self.get_text_char_format(type_color, type_color, int(100 / 4))
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

    def get_hide_chars_format(self, text_char_format):
        result = text_char_format
        result.setForeground(result.background())
        return result
