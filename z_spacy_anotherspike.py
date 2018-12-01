import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QListWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidgetItem,
    QHBoxLayout,
    QAbstractItemView
)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()

    list = QListWidget()

    list.addItem("Option 1")
    list.addItem("Option 2")
    list.addItem("Option 3")
    list.addItem("Option 4")
    list.addItem("Option 5")

    list.setSelectionMode(QAbstractItemView.ExtendedSelection)

    
    def on_change():
        print([item.text() for item in list.selectedItems()])
    list.itemSelectionChanged.connect(on_change) 

    window_layout = QVBoxLayout(window)
    window_layout.addWidget(list)
    window.setLayout(window_layout)

    window.show()

    sys.exit(app.exec_())
