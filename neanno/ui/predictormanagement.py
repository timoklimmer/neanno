import config
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
)


class PredictorManagementDialog(QDialog):
    """ A dialog to enable/disable predictors."""

    PREDICTOR_NAME_COLUMN_INDEX = 0
    IS_PREDICTION_ENABLED_COLUMN_INDEX = 1

    def __init__(self, parent=None):
        super(PredictorManagementDialog, self).__init__(parent)
        self.setWindowTitle("Manage Predictors")
        self.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout(self)

        # predictor table
        self.predictor_table = QTableWidget()
        self.predictor_table.setFocusPolicy(Qt.NoFocus)
        self.predictor_table.setRowCount(
            len(config.prediction_pipeline.get_all_predictors())
        )
        self.predictor_table.setColumnCount(2)
        self.predictor_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.predictor_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.predictor_table.verticalHeader().hide()
        self.predictor_table.setHorizontalHeaderLabels(
            ("Predictor", "Prediction on/off")
        )

        row = 0
        for predictor in config.prediction_pipeline.get_all_predictors():
            # predictor item
            predictor_name_item = QTableWidgetItem(predictor.name)
            predictor_name_item.setFlags(
                predictor_name_item.flags() ^ Qt.ItemIsEditable
            )
            self.predictor_table.setItem(
                row, self.PREDICTOR_NAME_COLUMN_INDEX, predictor_name_item
            )
            # is prediction enabled item
            is_prediction_enabled_item = QTableWidgetItem()
            is_prediction_enabled_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
            )
            is_prediction_enabled_item.setCheckState(
                Qt.Checked if predictor.is_prediction_enabled else Qt.Unchecked
            )
            self.predictor_table.setItem(
                row, self.IS_PREDICTION_ENABLED_COLUMN_INDEX, is_prediction_enabled_item
            )

            row += 1

        self.predictor_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.predictor_table.resizeRowsToContents()
        self.predictor_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.predictor_table.resizeColumnsToContents()
        self.setMinimumHeight(self.predictor_table.height())
        self.setMinimumWidth(self.predictor_table.width())
        layout.addWidget(self.predictor_table)

        # buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def show(parent=None):
        # show the dialog
        dialog = PredictorManagementDialog(parent)
        result = dialog.exec_()
        # update the predictor objects if user has clicked OK
        if result == QDialog.Accepted:
            for row in range(dialog.predictor_table.rowCount()):
                predictor_name = dialog.predictor_table.item(
                    row, dialog.PREDICTOR_NAME_COLUMN_INDEX
                ).text()
                predictor = config.prediction_pipeline.get_predictor(predictor_name)
                predictor.is_prediction_enabled = (
                    dialog.predictor_table.item(
                        row, dialog.IS_PREDICTION_ENABLED_COLUMN_INDEX
                    ).checkState()
                    == Qt.Checked
                )
