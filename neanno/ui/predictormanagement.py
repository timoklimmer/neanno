import config
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ManagePredictorsDialog(QDialog):
    """ A dialog to enable/disable predictors."""

    PREDICTOR_NAME_COLUMN_INDEX = 0
    IS_ONLINE_TRAINING_ENABLED_COLUMN_INDEX = 1
    IS_BATCH_TRAINING_ENABLED_COLUMN_INDEX = 2
    IS_PREDICTION_ENABLED_COLUMN_INDEX = 3

    def __init__(self, parent=None):
        super(ManagePredictorsDialog, self).__init__(parent)
        self.setWindowTitle("Manage Predictors")
        self.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout(self)

        # predictor table
        self.predictor_table = QTableWidget()
        self.predictor_table.setFocusPolicy(Qt.NoFocus)
        self.predictor_table.setRowCount(
            len(config.prediction_pipeline.get_all_predictors())
        )
        self.predictor_table.setColumnCount(4)
        self.predictor_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.predictor_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.predictor_table.verticalHeader().hide()
        self.predictor_table.setHorizontalHeaderLabels(
            ("Predictor", "Online Training", "Batch Training", "Predictions")
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
            # is online training enabled
            self.predictor_table.setCellWidget(
                row,
                self.IS_ONLINE_TRAINING_ENABLED_COLUMN_INDEX,
                ManagePredictorsDialog.get_centered_checkbox_widget(
                    predictor.is_online_training_enabled
                ),
            )
            # is batch training enabled
            self.predictor_table.setCellWidget(
                row,
                self.IS_BATCH_TRAINING_ENABLED_COLUMN_INDEX,
                ManagePredictorsDialog.get_centered_checkbox_widget(
                    predictor.is_batch_training_enabled
                ),
            )
            # is prediction enabled item
            # note: we have to create our own widgets here because PyQt5 does not center the checkboxes for us
            self.predictor_table.setCellWidget(
                row,
                self.IS_PREDICTION_ENABLED_COLUMN_INDEX,
                ManagePredictorsDialog.get_centered_checkbox_widget(
                    predictor.is_prediction_enabled
                ),
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
    def get_centered_checkbox_widget(is_checked):
        result = QWidget()
        checkbox = QCheckBox()
        checkbox.setObjectName("checkbox")
        checkbox.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
        layout = QHBoxLayout(result)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)
        return result

    @staticmethod
    def get_checkstate_from_checkbox_widget(centered_checkbox_widget):
        return (
            centered_checkbox_widget.findChild(QCheckBox, "checkbox").checkState()
            == Qt.Checked
        )

    @staticmethod
    def show(parent=None):
        # show the dialog
        dialog = ManagePredictorsDialog(parent)
        result = dialog.exec_()
        # process the new settings
        if result == QDialog.Accepted:
            # update the predictor instances
            for row in range(dialog.predictor_table.rowCount()):
                predictor_name = dialog.predictor_table.item(
                    row, dialog.PREDICTOR_NAME_COLUMN_INDEX
                ).text()
                predictor = config.prediction_pipeline.get_predictor(predictor_name)
                # is online training enabled
                predictor.is_online_training_enabled = ManagePredictorsDialog.get_checkstate_from_checkbox_widget(
                    dialog.predictor_table.cellWidget(
                        row, dialog.IS_ONLINE_TRAINING_ENABLED_COLUMN_INDEX
                    )
                )
                # is batch training enabled
                predictor.is_batch_training_enabled = ManagePredictorsDialog.get_checkstate_from_checkbox_widget(
                    dialog.predictor_table.cellWidget(
                        row, dialog.IS_BATCH_TRAINING_ENABLED_COLUMN_INDEX
                    )
                )
                # is prediction enabled
                predictor.is_prediction_enabled = ManagePredictorsDialog.get_checkstate_from_checkbox_widget(
                    dialog.predictor_table.cellWidget(
                        row, dialog.IS_PREDICTION_ENABLED_COLUMN_INDEX
                    )
                )
