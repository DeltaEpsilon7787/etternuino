# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'etternuino.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtWidgets


class Ui_etternuino_window(object):
    def setupUi(self, etternuino_window):
        etternuino_window.setObjectName("etternuino_window")
        etternuino_window.resize(630, 751)
        etternuino_window.setWindowTitle("Etternuino")
        self.main_widget = QtWidgets.QWidget(etternuino_window)
        self.main_widget.setObjectName("main_widget")
        self.vboxlayout = QtWidgets.QVBoxLayout(self.main_widget)
        self.vboxlayout.setObjectName("vboxlayout")
        self.checkbox_group = QtWidgets.QWidget(self.main_widget)
        self.checkbox_group.setObjectName("checkbox_group")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.checkbox_group)
        self.verticalLayout.setObjectName("verticalLayout")
        self.play_music_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.play_music_checkbox.setChecked(True)
        self.play_music_checkbox.setObjectName("play_music_checkbox")
        self.verticalLayout.addWidget(self.play_music_checkbox)
        self.signal_arduino_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.signal_arduino_checkbox.setObjectName("signal_arduino_checkbox")
        self.verticalLayout.addWidget(self.signal_arduino_checkbox)
        self.add_claps_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.add_claps_checkbox.setObjectName("add_claps_checkbox")
        self.verticalLayout.addWidget(self.add_claps_checkbox)
        self.vboxlayout.addWidget(self.checkbox_group)
        self.play_button = QtWidgets.QPushButton(self.main_widget)
        self.play_button.setObjectName("play_button")
        self.vboxlayout.addWidget(self.play_button)
        etternuino_window.setCentralWidget(self.main_widget)

        self.retranslateUi(etternuino_window)
        self.play_music_checkbox.toggled['bool'].connect(etternuino_window.play_music)
        self.signal_arduino_checkbox.toggled['bool'].connect(etternuino_window.signal_arduino)
        self.add_claps_checkbox.toggled['bool'].connect(etternuino_window.add_claps)
        self.play_button.clicked.connect(etternuino_window.play_file)
        QtCore.QMetaObject.connectSlotsByName(etternuino_window)

    def retranslateUi(self, etternuino_window):
        _translate = QtCore.QCoreApplication.translate
        self.play_music_checkbox.setText(_translate("etternuino_window", "Play music"))
        self.signal_arduino_checkbox.setText(_translate("etternuino_window", "Signal Arduino"))
        self.add_claps_checkbox.setText(_translate("etternuino_window", "Add claps"))
        self.play_button.setText(_translate("etternuino_window", "Play file"))
