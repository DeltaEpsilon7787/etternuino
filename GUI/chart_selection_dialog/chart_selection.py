# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from GUI.chart_selection_dialog.chart_selection_gui import Ui_ChartSelectionDialog


class ChartSelectionDialog(QtWidgets.QDialog, Ui_ChartSelectionDialog):
    on_selection = QtCore.pyqtSignal('int')
    on_cancel = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setupUi(self)

    @QtCore.pyqtSlot()
    def accept(self):
        selected = self.chart_list.selectedIndexes()
        if selected:
            self.on_selection.emit(selected[0].row())
            super().accept()
        else:
            self.on_selection.emit(-1)
            super().reject()

    @QtCore.pyqtSlot()
    def reject(self):
        self.on_cancel.emit()
