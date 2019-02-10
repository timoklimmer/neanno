import config
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class PredictorSelectionDialog(QDialog):
    """ A dialog to enable/disable predictors."""

    def __init__(self, parent=None):
        super(PredictorSelectionDialog, self).__init__(parent)
        self.setWindowTitle("Enable/Disable Predictors for Annotation Prediction")
        self.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout(self)

        # predictor list
        self.predictor_list = QListWidget()
        self.predictor_list.setSelectionMode(QAbstractItemView.NoSelection)
        for predictor in config.prediction_pipeline.get_all_predictors():
            item = QListWidgetItem(predictor.name, self.predictor_list, 0)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if predictor.is_prediction_enabled else Qt.Unchecked
            )
            self.predictor_list.addItem(item)
        layout.addWidget(self.predictor_list)

        # buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def show(parent=None):
        dialog = PredictorSelectionDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            for index in range(dialog.predictor_list.count()):
                predictor_item = dialog.predictor_list.item(index)
                predictor_item_checkstate = predictor_item.checkState()
                predictor_name = predictor_item.text()
                predictor = config.prediction_pipeline.get_predictor(predictor_name)
                predictor.is_prediction_enabled = (
                    predictor_item_checkstate == Qt.Checked
                )
