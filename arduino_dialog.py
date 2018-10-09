# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'arduino_virtual.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!
import time
from typing import List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from attr import attrs, attrib

from basic_types import NoteObjects, Time
from definitions import capture_exceptions, in_reduce
from rows import GlobalScheduledRow, Snap


@attrs
class ChartInfoEntry:
    time: Time = attrib()
    snap: Snap = attrib()
    objects: NoteObjects = attrib()
    local_nps: List[int] = attrib(factory=lambda: [0] * 4)
    local_counters: List[int] = attrib(factory=lambda: [0] * 4)
    global_nps: int = attrib(default=0)

class VirtualArduino(QtWidgets.QDialog):
    chart_info: List[ChartInfoEntry] = None
    current_info: int = None

    def __init__(self, *args, **kwargs):
        QtWidgets.QDialog.__init__(self, *args, **kwargs)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
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
        self.horizontalWidget = QtWidgets.QWidget(self)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalWidget)
        self.nps_window_dial = QtWidgets.QDial(self.horizontalWidget)
        self.local_dial = QtWidgets.QDial(self.horizontalWidget)
        self.blink_dial = QtWidgets.QDial(self.horizontalWidget)
        self.global_dial = QtWidgets.QDial(self.horizontalWidget)

        self.chart_info = []
        self.safe_lanes = set()
        self.lane_activation_times = [0] * 4
        self.blink_period = 0.05
        self.nps_window = 3.0
        self.current_index = 0

        self.setup_ui()
        self.local_dial.valueChanged.connect(self.modify_local)
        self.global_dial.valueChanged.connect(self.modify_global)
        self.blink_dial.valueChanged.connect(self.modify_blink)
        self.nps_window_dial.sliderReleased.connect(self.modify_nps_window)

        self.local_dial.setValue(20000)
        self.global_dial.setValue(60000)
        self.blink_dial.setValue(50)
        self.nps_window_dial.setValue(3000)

    def setup_ui(self):
        self.setObjectName("Dialog")
        self.resize(613, 553)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
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
        self.l1.setAutoFillBackground(True)
        self.l1.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l1.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l1.setObjectName("l1")
        self.horizontalLayout_2.addWidget(self.l1)
        self.l2.setMinimumSize(QtCore.QSize(100, 100))
        self.l2.setAutoFillBackground(True)
        self.l2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l2.setObjectName("l2")
        self.horizontalLayout_2.addWidget(self.l2)
        self.l3.setMinimumSize(QtCore.QSize(100, 100))
        self.l3.setAutoFillBackground(True)
        self.l3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.l3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.l3.setObjectName("l3")
        self.horizontalLayout_2.addWidget(self.l3)
        self.l4.setMinimumSize(QtCore.QSize(100, 100))
        self.l4.setAutoFillBackground(True)
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
        self.verticalLayout_2.addWidget(self.frame)
        self.horizontalWidget.setObjectName("horizontalWidget")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.nps_window_dial.setMaximum(5000)
        self.nps_window_dial.setObjectName('nps_window_dial')
        self.horizontalLayout.addWidget(self.nps_window_dial)
        self.local_dial.setMaximum(20000)
        self.local_dial.setObjectName("local_dial")
        self.horizontalLayout.addWidget(self.local_dial)
        self.blink_dial.setMaximum(100)
        self.blink_dial.setOrientation(QtCore.Qt.Horizontal)
        self.blink_dial.setObjectName("blink_dial")
        self.horizontalLayout.addWidget(self.blink_dial)
        self.global_dial.setMaximum(60000)
        self.global_dial.setObjectName("global_dial")
        self.horizontalLayout.addWidget(self.global_dial)
        self.verticalLayout_2.addWidget(self.horizontalWidget)

        self.retranslate_ui()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslate_ui(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Dialog", "Visuterna"))

    @QtCore.pyqtSlot(int)
    def modify_local(self, new_max):
        self.l1_nps.setMaximum(new_max)
        self.l2_nps.setMaximum(new_max)
        self.l3_nps.setMaximum(new_max)
        self.l4_nps.setMaximum(new_max)

    @QtCore.pyqtSlot(int)
    def modify_global(self, new_max):
        self.l_nps.setMaximum(new_max)

    @QtCore.pyqtSlot(int)
    def modify_blink(self, new_max):
        self.blink_period = new_max / 1000

    @QtCore.pyqtSlot()
    def modify_nps_window(self):
        self.nps_window = self.nps_window_dial.value() / 1000
        self.reanalyze_chart()

    @QtCore.pyqtSlot(object)
    def analyze_chart(self, chart: List[GlobalScheduledRow]):
        self.chart = chart
        self.reanalyze_chart()

    @capture_exceptions
    def reanalyze_chart(self):
        chart = list(self.chart)

        global_timing_points = [
            note.time
            for note in chart
            if not in_reduce(all, note.objects, ('0', 'M'))
        ]
        global_nps = [0]
        second_period_notes = []
        for index, new_note in enumerate(chart):
            for note in second_period_notes:
                if new_note.time - note.time > self.nps_window:
                    second_period_notes.remove(note)
                else:
                    break

            if not in_reduce(all, new_note.objects, ('0', '3', '5', 'M')):
                second_period_notes.append(new_note)

            data_points = {
                              note.time
                              for note in second_period_notes
                          } | {
                              chart[index - 1].time
                          } if index > 0 else {}
            global_nps.append(
                len(data_points) > 1 and
                sum(1 for _ in data_points) / (max(data_points) - min(data_points)) or
                1
            )
        local_nps_storage = []
        local_counter_storage = []
        for lane in range(4):
            last_counter = 0
            local_nps = [0]
            local_counter = [0]

            second_period_notes = []
            for index, new_note in enumerate(chart):
                for note in second_period_notes:
                    if new_note.time - note.time > self.nps_window:
                        second_period_notes.remove(note)
                    else:
                        break

                if new_note.objects[lane] != '0':
                    if not in_reduce(all, new_note.objects, ('3', '5', 'M')):
                        second_period_notes.append(new_note)

                data_points = {
                                  note.time
                                  for note in second_period_notes
                              } | {
                                  chart[index - 1].time
                              } if index > 0 else {}

                last_nps = (
                        len(data_points) > 1 and
                        sum(1 for _ in data_points) / (max(data_points) - min(data_points)) or
                        1
                )
                local_nps.append(last_nps)
                last_counter += 1
                local_counter.append(last_counter)

            local_nps_storage.append(local_nps)
            local_counter_storage.append(local_counter)

        local_nps_storage = list(zip(*local_nps_storage))
        local_counter_storage = list(zip(*local_counter_storage))

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

        self.chart_info = full_data

    @QtCore.pyqtSlot(object)
    @capture_exceptions
    def rewind_to(self, timing_point):
        def in_bounds(index=None):
            data_length = len(self.chart_info)
            if index is not None:
                return 0 <= index < data_length
            return 0 <= self.current_index < data_length

        if not self.chart_info or not in_bounds():
            return

        current_point = self.chart_info[self.current_index]

        while timing_point < current_point.time:
            # Need to rewind back
            current_point = self.chart_info[self.current_index]
            has_prev = in_bounds(self.current_index - 1)
            prev_still_after = has_prev and timing_point < current_point.time
            if has_prev and prev_still_after:
                self.current_index -= 1
            else:
                break
        while timing_point > current_point.time:
            current_point = self.chart_info[self.current_index]
            has_next = in_bounds(self.current_index + 1)
            next_still_behind = has_next and timing_point > current_point.time
            if has_next and next_still_behind:
                self.current_index += 1
            else:
                break

        if current_point.time == timing_point:
            self.handle_event(current_point)
        else:
            self.handle_event(None)

    @capture_exceptions
    def set_color(self, lane_index, lane, r, g, b):
        palette = lane.palette()
        role = lane.backgroundRole()
        palette.setColor(role, QtGui.QColor(r, g, b, 255))
        lane.setPalette(palette)

        self.lane_activation_times[lane_index] = time.perf_counter()

    @capture_exceptions
    def reset_color(self, lane_index, lane):
        if lane_index in self.safe_lanes:
            return
        if time.perf_counter() - self.lane_activation_times[lane_index] < self.blink_period:
            return
        lane.setPalette(self.frame.palette())

    @capture_exceptions
    def handle_event(self, event: Optional[ChartInfoEntry]):
        lane_object_map = [self.l1, self.l2, self.l3, self.l4]
        nps_map = [self.l1_nps, self.l2_nps, self.l3_nps, self.l4_nps]
        if event is None:
            for i in range(4):
                self.reset_color(i, lane_object_map[i])
        else:
            snap_color = (event.snap.color.r, event.snap.color.g, event.snap.color.b)
            for i in range(4):
                event.objects[i] in ('1', '2', '4') and self.set_color(i, lane_object_map[i], *snap_color)
                event.objects[i] in ('2', '4') and self.safe_lanes.add(i)
                if event.objects[i] in ('3', '5'):
                    self.reset_color(i, self.l2)
                    self.safe_lanes.remove(i)

            for i in range(4):
                nps_map[i].setValue(int(1000 * event.local_nps[i]))
            self.l_nps.setValue(int(1000 * event.global_nps))
