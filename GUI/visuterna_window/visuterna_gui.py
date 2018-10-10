# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'visuterna.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_visuterna_dialog(object):
    def setupUi(self, visuterna_dialog):
        visuterna_dialog.setObjectName("visuterna_dialog")
        self.verticalLayout = QtWidgets.QVBoxLayout(visuterna_dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lane_group = QtWidgets.QHBoxLayout()
        self.lane_group.setObjectName("lane_group")
        self.verticalLayout.addLayout(self.lane_group)
        self.nps_group = QtWidgets.QHBoxLayout()
        self.nps_group.setObjectName("nps_group")
        self.verticalLayout.addLayout(self.nps_group)
        self.dial_group = QtWidgets.QHBoxLayout()
        self.dial_group.setObjectName("dial_group")
        self.verticalLayout.addLayout(self.dial_group)
        self.progress_group = QtWidgets.QHBoxLayout()
        self.progress_group.setObjectName("progress_group")
        self.control_group = QtWidgets.QVBoxLayout()
        self.control_group.setObjectName("control_group")
        self.pause_btn = QtWidgets.QPushButton(visuterna_dialog)
        self.pause_btn.setObjectName("pause_btn")
        self.control_group.addWidget(self.pause_btn)
        self.unpause_btn = QtWidgets.QPushButton(visuterna_dialog)
        self.unpause_btn.setObjectName("unpause_btn")
        self.control_group.addWidget(self.unpause_btn)
        self.stop_btn = QtWidgets.QPushButton(visuterna_dialog)
        self.stop_btn.setObjectName("stop_btn")
        self.control_group.addWidget(self.stop_btn)
        self.progress_group.addLayout(self.control_group)
        self.scroll_group = QtWidgets.QHBoxLayout()
        self.scroll_group.setObjectName("scroll_group")
        self.progress_label = QtWidgets.QLabel(visuterna_dialog)
        self.progress_label.setObjectName("progress_label")
        self.scroll_group.addWidget(self.progress_label)
        self.progress_slider = QtWidgets.QSlider(visuterna_dialog)
        self.progress_slider.setSingleStep(4410)
        self.progress_slider.setPageStep(44100)
        self.progress_slider.setOrientation(QtCore.Qt.Horizontal)
        self.progress_slider.setObjectName("progress_slider")
        self.scroll_group.addWidget(self.progress_slider)
        self.progress_group.addLayout(self.scroll_group)
        self.verticalLayout.addLayout(self.progress_group)
        self.progress_label.setBuddy(self.progress_slider)

        self.retranslateUi(visuterna_dialog)
        self.pause_btn.clicked.connect(self.pause_btn.hide)
        self.unpause_btn.clicked.connect(self.unpause_btn.hide)
        self.unpause_btn.clicked.connect(self.pause_btn.show)
        self.pause_btn.clicked.connect(self.unpause_btn.show)
        self.progress_slider.valueChanged['int'].connect(visuterna_dialog.rewind)
        self.stop_btn.clicked.connect(visuterna_dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(visuterna_dialog)

    def retranslateUi(self, visuterna_dialog):
        _translate = QtCore.QCoreApplication.translate
        visuterna_dialog.setWindowTitle(_translate("visuterna_dialog", "Visuterna"))
        self.pause_btn.setText(_translate("visuterna_dialog", "Pause"))
        self.unpause_btn.setText(_translate("visuterna_dialog", "Unpause"))
        self.stop_btn.setText(_translate("visuterna_dialog", "Stop"))
        self.progress_label.setText(_translate("visuterna_dialog", "Progress:"))

