# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'arduino_virtual.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtWidgets

from definitions import capture_exceptions


class VirtualArduino(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(self, *args, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("Dialog")
        self.resize(400, 339)
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.l1 = QtWidgets.QFrame(self)
        self.l1.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l1.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l1.setObjectName("l1")
        self.gridLayout.addWidget(self.l1, 0, 0, 1, 1)
        self.l3 = QtWidgets.QFrame(self)
        self.l3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l3.setObjectName("l3")
        self.gridLayout.addWidget(self.l3, 0, 2, 1, 1)
        self.l2 = QtWidgets.QFrame(self)
        self.l2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l2.setObjectName("l2")
        self.gridLayout.addWidget(self.l2, 0, 1, 1, 1)
        self.l4 = QtWidgets.QFrame(self)
        self.l4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l4.setObjectName("l4")
        self.gridLayout.addWidget(self.l4, 0, 3, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame_6 = QtWidgets.QFrame(self)
        self.frame_6.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_6.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_6.setObjectName("frame_6")
        self.horizontalLayout.addWidget(self.frame_6)
        self.s24 = QtWidgets.QFrame(self)
        self.s24.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.s24.setFrameShadow(QtWidgets.QFrame.Raised)
        self.s24.setObjectName("s24")
        self.horizontalLayout.addWidget(self.s24)
        self.s24_2 = QtWidgets.QFrame(self)
        self.s24_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.s24_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.s24_2.setObjectName("s24_2")
        self.horizontalLayout.addWidget(self.s24_2)
        self.s12 = QtWidgets.QFrame(self)
        self.s12.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.s12.setFrameShadow(QtWidgets.QFrame.Raised)
        self.s12.setObjectName("s12")
        self.horizontalLayout.addWidget(self.s12)
        self.s12_2 = QtWidgets.QFrame(self)
        self.s12_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.s12_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.s12_2.setObjectName("s12_2")
        self.horizontalLayout.addWidget(self.s12_2)
        self.frame = QtWidgets.QFrame(self)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout.addWidget(self.frame)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.s8 = QtWidgets.QFrame(self)
        self.s8.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.s8.setFrameShadow(QtWidgets.QFrame.Raised)
        self.s8.setObjectName("s8th")
        self.gridLayout_2.addWidget(self.s8, 0, 2, 1, 1)
        self.s16 = QtWidgets.QFrame(self)
        self.s16.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.s16.setFrameShadow(QtWidgets.QFrame.Raised)
        self.s16.setObjectName("s16")
        self.gridLayout_2.addWidget(self.s16, 0, 1, 1, 1)
        self.s4 = QtWidgets.QFrame(self)
        self.s4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.s4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.s4.setObjectName("s4th")
        self.gridLayout_2.addWidget(self.s4, 0, 0, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_2)

        self.snaps = {
            4: [self.s4],
            8: [self.s8],
            12: [self.s12, self.s12_2],
            16: [self.s16],
            24: [self.s24, self.s24_2]
        }
        self.all_snaps = [self.s4,
                          self.s8,
                          self.s12, self.s12_2,
                          self.s16,
                          self.s24, self.s24_2]
        self.retranslate_ui()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslate_ui(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Dialog", "Virtual Arduino"))

    @capture_exceptions
    def toggle_lanes(self, bitcode):
        self.l1.setStyleSheet(bitcode & 1 and 'rgb(0, 0, 0)' or '')
        self.l2.setStyleSheet(bitcode & 2 and 'rgb(0, 0, 0)' or '')
        self.l3.setStyleSheet(bitcode & 4 and 'rgb(0, 0, 0)' or '')
        self.l4.setStyleSheet(bitcode & 8 and 'rgb(0, 0, 0)' or '')

    @capture_exceptions
    def toogle_snap(self, snap_values):
        for snap in self.all_snaps:
            snap.setStyleSheet('')

        def set_snap_color(condition, r, g, b):
            if set(snap_values) != set(condition):
                return

            for this_snap_value in snap_values:
                for snap in self.snaps[this_snap_value]:
                    snap.setStyleSheet(f'rgb({r}, {g}, {b});')
            return True

        set_snap_color([4], 255, 0, 0)
        set_snap_color([12], 120, 0, 255)
        set_snap_color([8], 0, 0, 255)
        set_snap_color([16], 255, 255, 0)
        set_snap_color([24], 255, 120, 255)
        set_snap_color([4, 8], 255, 120, 0)
        set_snap_color([4, 12], 0, 255, 255)
        set_snap_color([4, 16], 0, 255, 0)
        set_snap_color([8, 12], 120, 120, 120)
        set_snap_color([8, 16], 120, 120, 120)
        set_snap_color([12, 16], 120, 120, 120)
