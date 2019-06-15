import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from neanno.configuration.configmanager import ConfigManager
from neanno.models.textmodel import TextModel
from neanno.ui.maindialog import MainDialog

from .version import __version__


def main():
    try:
        # set some settings for high DPI screens
        if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

        if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

        # print the neanno banner
        print_banner()

        # process the configuration file
        ConfigManager()

        # run the main dialog
        MainDialog(TextModel())
    except SystemExit:
        pass
    except:
        if sys.exc_info()[0] != "<class 'SystemExit'>":
            print("An unhandled error occured: ", sys.exc_info()[0])
        raise


def print_banner():
    print(" _ __   ___  __ _ _ __  _ __   ___")
    print("| '_ \\ / _ \\/ _` | '_ \\| '_ \\ / _ \\")
    print("| | | |  __/ (_| | | | | | | | (_) |")
    print("|_| |_|\___|\__,_|_| |_|_| |_|\___/")
    print("====================================")
    print("Version: {}".format(__version__))
    print("")
