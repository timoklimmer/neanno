"""Initializes the neanno package before it can be used."""

import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

import neanno
from neanno.configuration.configmanager import ConfigManager
from neanno.ui.maindialog import MainDialog

__version__ = '0.1'

def main():
    """Main function for neanno's user interface."""

    def _print_startup_banner():
        """Prints neanno's startup banner."""

        print(" _ __   ___  __ _ _ __  _ __   ___")
        print("| '_ \\ / _ \\/ _` | '_ \\| '_ \\ / _ \\")
        print("| | | |  __/ (_| | | | | | | | (_) |")
        print("|_| |_|\___|\__,_|_| |_|_| |_|\___/")
        print("====================================")
        print("Version: {}".format(neanno.__version__))
        print("")

    try:
        # set some settings for high DPI screens
        if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

        if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

        # print the startup banner
        _print_startup_banner()

        # run the main dialog
        MainDialog()
    except SystemExit:
        pass
    except:
        if sys.exc_info()[0] != "<class 'SystemExit'>":
            print("An unhandled error occured: ", sys.exc_info()[0])
        raise
