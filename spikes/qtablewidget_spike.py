import sys

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QFrame
)


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = "PyQt5 table - pythonspot.com"
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)

        self.createTable()

        # Add box layout, add table to box layout and add box layout to widget
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tableWidget)
        self.setLayout(self.layout)
        # Show widget
        self.show()

    def createTable(self):
        # Create table
        self.tableWidget = QTableWidget()
        self.tableWidget.setFrameStyle(QFrame.NoFrame)
        #self.tableWidget.setRowCount(1)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.setFocusPolicy(Qt.NoFocus)
        #self.tableWidget.setHorizontalHeaderLabels(('Category', 'Frequency'))
        self.tableWidget.verticalHeader().setDefaultSectionSize(self.tableWidget.verticalHeader().minimumSectionSize())
        self.tableWidget.horizontalHeader().hide()
        self.tableWidget.verticalHeader().hide()
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setSelectionMode(QAbstractItemView.MultiSelection)
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.tableWidget.setRowCount(1)
        self.tableWidget.setItem(0, 0, QTableWidgetItem("Ticketing"))
        item = QTableWidgetItem("4")
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tableWidget.setItem(0, 1,item)
        
        self.tableWidget.setRowCount(2)
        self.tableWidget.setItem(1, 0, QTableWidgetItem("Complaints"))
        self.tableWidget.setItem(1, 1, QTableWidgetItem("2"))
        self.tableWidget.setRowCount(3)
        self.tableWidget.setItem(2, 0, QTableWidgetItem("Misc"))
        self.tableWidget.setItem(2, 1, QTableWidgetItem("49"))
        self.tableWidget.setRowCount(4)
        self.tableWidget.setItem(3, 0, QTableWidgetItem("Other"))
        self.tableWidget.setItem(3, 1, QTableWidgetItem("1"))
        # table selection change
        self.tableWidget.doubleClicked.connect(self.on_click)

    @pyqtSlot()
    def on_click(self):
        print("\n")
        for currentQTableWidgetItem in self.tableWidget.selectedItems():
            print(
                currentQTableWidgetItem.row(),
                currentQTableWidgetItem.column(),
                currentQTableWidgetItem.text(),
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
