# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'chart_selection.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtWidgets

from definitions import capture_exceptions


class ChartSelectionDialog(QtWidgets.QDialog):
    on_selection = QtCore.pyqtSignal('int')
    on_cancel = QtCore.pyqtSignal()

    @capture_exceptions
    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        self.setup_ui()

        self.dialog_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
            lambda: (
                self.on_selection.emit(self.chart_list.selectedIndexes()[0].row())
                if self.chart_list.selectedIndexes() else
                self.on_selection.emit(-1)
            )
        )
        self.dialog_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.close)
        self.dialog_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.chart_list.setSelectionMode(QtWidgets.QListWidget.SingleSelection)

    def setup_ui(self):
        self.setObjectName("ChartSelectionDialog")
        self.resize(400, 300)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.chart_list = QtWidgets.QListWidget(self)
        self.chart_list.setObjectName("chart_list")
        self.verticalLayout.addWidget(self.chart_list)
        self.dialog_box = QtWidgets.QDialogButtonBox(self)
        self.dialog_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.dialog_box.setObjectName("dialog_box")
        self.verticalLayout.addWidget(self.dialog_box)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslate_ui()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslate_ui(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("ChartSelectionDialog", "Chart selection"))
