# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'arduino_virtual.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!
from typing import List

from PyQt5 import QtCore, QtGui, QtWidgets
from attr import attrs, attrib

from basic_types import NoteObjects, Time
from definitions import capture_exceptions, BYTE_TRUE, BYTE_FALSE
from itertools import chain

from rows import GlobalScheduledRow, Snap

@attrs
class ChartInfoEntry:
    time: Time = attrib()
    snap: Snap = attrib()
    objects: NoteObjects = attrib()
    local_nps: List[float] = attrib(factory=lambda: [0] * 4)
    local_counters: List[int] = attrib(factory=lambda: [0] * 4)
    global_nps: float = attrib(default=0)

class VirtualArduino(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(*args, **kwargs)

        self.setObjectName("Dialog")
        self.resize(597, 520)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.frame = QtWidgets.QFrame(self)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.frame)
        self.l1_nps = QtWidgets.QProgressBar(self.frame)
        self.l2_nps = QtWidgets.QProgressBar(self.frame)
        self.l3_nps = QtWidgets.QProgressBar(self.frame)
        self.l4_nps = QtWidgets.QProgressBar(self.frame)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.l1 = QtWidgets.QFrame(self.frame)
        self.l2 = QtWidgets.QFrame(self.frame)
        self.l3 = QtWidgets.QFrame(self.frame)
        self.l4 = QtWidgets.QFrame(self.frame)
        self.l_nps = QtWidgets.QProgressBar(self.frame)

        self.chart_info = []

        self.setup_ui()

    def setup_ui(self):
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.l1_nps.setMaximumSize(QtCore.QSize(50, 400))
        self.l1_nps.setMaximum(10)
        self.l1_nps.setProperty("value", 5)
        self.l1_nps.setTextVisible(True)
        self.l1_nps.setOrientation(QtCore.Qt.Vertical)
        self.l1_nps.setTextDirection(QtWidgets.QProgressBar.TopToBottom)
        self.l1_nps.setFormat("%v / %m")
        self.l1_nps.setObjectName("l1_nps")
        self.horizontalLayout_3.addWidget(self.l1_nps)
        self.l2_nps.setMaximumSize(QtCore.QSize(50, 400))
        self.l2_nps.setMaximum(10)
        self.l2_nps.setProperty("value", 5)
        self.l2_nps.setTextVisible(True)
        self.l2_nps.setOrientation(QtCore.Qt.Vertical)
        self.l2_nps.setTextDirection(QtWidgets.QProgressBar.TopToBottom)
        self.l2_nps.setFormat("%v / %m")
        self.l2_nps.setObjectName("l2_nps")
        self.horizontalLayout_3.addWidget(self.l2_nps)
        self.l3_nps.setMaximumSize(QtCore.QSize(50, 400))
        self.l3_nps.setMaximum(10)
        self.l3_nps.setProperty("value", 5)
        self.l3_nps.setTextVisible(True)
        self.l3_nps.setOrientation(QtCore.Qt.Vertical)
        self.l3_nps.setInvertedAppearance(False)
        self.l3_nps.setTextDirection(QtWidgets.QProgressBar.TopToBottom)
        self.l3_nps.setFormat("%v")
        self.l3_nps.setObjectName("l3_nps")
        self.horizontalLayout_3.addWidget(self.l3_nps)
        self.l4_nps.setMaximumSize(QtCore.QSize(50, 400))
        self.l4_nps.setMaximum(10)
        self.l4_nps.setProperty("value", 5)
        self.l4_nps.setTextVisible(True)
        self.l4_nps.setOrientation(QtCore.Qt.Vertical)
        self.l4_nps.setTextDirection(QtWidgets.QProgressBar.TopToBottom)
        self.l4_nps.setFormat("%v / %m")
        self.l4_nps.setObjectName("l4_nps")
        self.horizontalLayout_3.addWidget(self.l4_nps)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.l1.setMinimumSize(QtCore.QSize(100, 100))
        self.l1.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l1.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l1.setObjectName("l1")
        self.horizontalLayout_2.addWidget(self.l1)
        self.l2.setMinimumSize(QtCore.QSize(100, 100))
        self.l2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l2.setObjectName("l2")
        self.horizontalLayout_2.addWidget(self.l2)
        self.l3.setMinimumSize(QtCore.QSize(100, 100))
        self.l3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l3.setObjectName("l3")
        self.horizontalLayout_2.addWidget(self.l3)
        self.l4.setMinimumSize(QtCore.QSize(100, 100))
        self.l4.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l4.setObjectName("l4")
        self.horizontalLayout_2.addWidget(self.l4)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3.addLayout(self.verticalLayout)
        self.l_nps.setMaximum(10)
        self.l_nps.setProperty("value", 5)
        self.l_nps.setOrientation(QtCore.Qt.Vertical)
        self.l_nps.setTextDirection(QtWidgets.QProgressBar.TopToBottom)
        self.l_nps.setFormat("%v / %m")
        self.l_nps.setObjectName("l_nps")
        self.horizontalLayout_3.addWidget(self.l_nps)
        self.horizontalLayout.addWidget(self.frame)

        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Dialog", "Visuterna"))

        QtCore.QMetaObject.connectSlotsByName(self)

    @QtCore.pyqtSlot()
    @capture_exceptions
    def analyze_chart(self, chart: List[GlobalScheduledRow]):
        global_timing_points = [
            note.time
            for note in chart
        ]

        global_nps = [0]
        for prev_note, new_note in zip(chart[:-1], chart[1:]):
            global_nps.append((new_note.time - prev_note.time)**-1)

        local_nps_storage = []
        local_counter_storage = []
        for lane in range(4):
            filtered_chart = list(reversed([
                note
                for note in chart
                if note.objects[lane] in ('1', '2', '4')
            ]))
            timing_copy = global_timing_points.copy()

            last_nps = 0
            last_counter = 0
            local_nps = [0]
            local_counter = [0]
            for prev_note, new_note in filtered_chart:
                while timing_copy and timing_copy[-1].time < new_note.time:
                    local_nps.append(last_nps)
                    local_counter.append(last_counter)
                    timing_copy.pop()
                last_nps = (new_note.time - prev_note.time)**-1
                local_nps.append(last_nps)
                last_counter += 1
                local_counter.append(last_counter)

            local_nps_storage.append(local_nps)
            local_counter_storage.append(local_counter)

        local_nps_storage = list(zip(*local_nps_storage))

        full_data = []
        for timing_point, global_nps_point, local_nps_point, local_counter_point, row in zip(global_timing_points,
                                                                                             global_nps,
                                                                                             local_nps_storage,
                                                                                             local_counter_storage,
                                                                                             chart):
            full_data.append(
                ChartInfoEntry(
                    timing_point,
                    Snap.from_row(row),
                    row.objects,
                    local_nps_point, local_counter_point,
                    global_nps_point
                )
            )

    @QtCore.pyqtSlot(Time)
    def rewind_to(self, timing_point):
        pass