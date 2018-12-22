from PyQt5.QtWidgets import QMessageBox

ABOUT_TEXT = """neanno is yet another text annotation tool.

There are already several other annotation tools out there but none
of them really matched my requirements. Hence, I created my own.

This is NOT an official Microsoft product, hence does not come with
any support or obligations for Microsoft.

Feel free to use but don't blame me if things go wrong.

Get the most updated version from GitHub.

Written in 2018 by Timo Klimmer, timo.klimmer@microsoft.com.
"""


def show_about_dialog(parent):
    QMessageBox.information(parent, "About neanno", ABOUT_TEXT, QMessageBox.Ok)
