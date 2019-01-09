from neanno.configuration.configmanager import ConfigManager
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication


if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


ConfigManager()
