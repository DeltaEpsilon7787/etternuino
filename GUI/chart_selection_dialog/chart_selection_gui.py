# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'chart_selection.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ChartSelectionDialog(object):
    def setupUi(self, ChartSelectionDialog):
        ChartSelectionDialog.setObjectName("ChartSelectionDialog")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(ChartSelectionDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.chart_list = QtWidgets.QListView(ChartSelectionDialog)
        self.chart_list.setObjectName("chart_list")
        self.verticalLayout_2.addWidget(self.chart_list)
        self.dialog_box = QtWidgets.QDialogButtonBox(ChartSelectionDialog)
        self.dialog_box.setOrientation(QtCore.Qt.Horizontal)
        self.dialog_box.setStandardButtons(QtWidgets.QDialogButtonBox.Abort|QtWidgets.QDialogButtonBox.Open)
        self.dialog_box.setObjectName("dialog_box")
        self.verticalLayout_2.addWidget(self.dialog_box)

        self.retranslateUi(ChartSelectionDialog)
        self.dialog_box.rejected.connect(ChartSelectionDialog.reject)
        self.dialog_box.accepted.connect(ChartSelectionDialog.accept)
        QtCore.QMetaObject.connectSlotsByName(ChartSelectionDialog)

    def retranslateUi(self, ChartSelectionDialog):
        _translate = QtCore.QCoreApplication.translate
        ChartSelectionDialog.setWindowTitle(_translate("ChartSelectionDialog", "Chart selection"))

