# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dial_group.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtWidgets


class Ui_dial_group(object):
    def setupUi(self, dial_group):
        dial_group.setObjectName("dial_group")
        self.horizontalLayout = QtWidgets.QHBoxLayout(dial_group)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.splitter = QtWidgets.QSplitter(dial_group)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.meaning_label = QtWidgets.QLabel(self.splitter)
        self.meaning_label.setObjectName("meaning_label")
        self.slider = QtWidgets.QSlider(self.splitter)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.setObjectName("slider")
        self.value_out = QtWidgets.QLabel(self.splitter)
        self.value_out.setObjectName("value_out")
        self.horizontalLayout.addWidget(self.splitter)
        self.meaning_label.setBuddy(self.slider)

        self.retranslateUi(dial_group)
        self.slider.valueChanged['int'].connect(dial_group.valueChanged)
        QtCore.QMetaObject.connectSlotsByName(dial_group)

    def retranslateUi(self, dial_group):
        _translate = QtCore.QCoreApplication.translate
        dial_group.setWindowTitle(_translate("dial_group", "Frame"))
