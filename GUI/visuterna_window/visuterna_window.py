# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui

from GUI.dial_group.dial_group import DialGroup
from GUI.visuterna_window.visuterna_gui import Ui_visuterna_dialog
from chart_player import NoteEvent
from definitions import LANE_PINS, capture_exceptions
from simfile_parsing.rows import Snap


class VisuternaWindow(QtWidgets.QDialog, Ui_visuterna_dialog):
    time_changed = QtCore.pyqtSignal(int)

    def __init__(self, lanes_amt=4, player=None):
        super().__init__()
        self.setupUi(self)

        self.unpause_btn.hide()
        self.nps_window = 3.0

        self.lane_frames = []
        self.lane_nps_bars = []

        for i in range(lanes_amt):
            lane_frame = QtWidgets.QFrame()
            lane_nps_bar = QtWidgets.QProgressBar()

            lane_frame.setObjectName(f'lane_frame_{i}')
            lane_nps_bar.setObjectName(f'lane_nps_bar_{i}')

            lane_frame.setMinimumSize(100, 100)
            lane_frame.setAutoFillBackground(True)

            self.lane_group.addWidget(lane_frame)
            self.nps_group.addWidget(lane_nps_bar)

            self.lane_frames.append(lane_frame)
            self.lane_nps_bars.append(lane_nps_bar)

        self.global_nps_bar = QtWidgets.QProgressBar()
        self.nps_group.addWidget(self.global_nps_bar)

        self.nps_window_dial_group = DialGroup("NPS Window (sec)", 0, 5, 0.001, self.modify_nps_window)
        self.dial_group.addWidget(self.nps_window_dial_group)
        self.local_nps_dial_group = DialGroup("Local NPS max", 0, 30, 1, self.modify_local)
        self.dial_group.addWidget(self.local_nps_dial_group)
        self.global_nps_dial_group = DialGroup("Global NPS max", 0, 60, 1, self.modify_global)
        self.dial_group.addWidget(self.global_nps_dial_group)

        self.local_nps_dial_group.slider.setValue(20000)
        self.global_nps_dial_group.slider.setValue(60000)
        self.nps_window_dial_group.slider.setValue(3000)

        self.player = player

    def modify_local(self, new_max):
        for lane_nps_bar in self.lane_nps_bars:
            lane_nps_bar.setMaximum(int(new_max))

    def modify_global(self, new_max):
        self.global_nps_bar.setMaximum(int(new_max))

    def modify_nps_window(self, new_window):
        self.nps_window = new_window

    @QtCore.pyqtSlot(int)
    def rewind(self, new_time):
        self.time_changed.emit(new_time)

    @QtCore.pyqtSlot(object)
    @capture_exceptions
    def receive_event(self, event: NoteEvent):
        snap = Snap.from_row(event.row)
        snap_color = snap.color
        for lane in range(len(LANE_PINS)):
            lane_frame = self.lane_frames[lane]
            if event.row.objects[lane] in ('0', 'M'):
                continue
            if event.row.objects[lane] in ('1', '2', '3', '4', '5'):
                if event.state:
                    pal = lane_frame.palette()
                    pal.setColor(lane_frame.backgroundRole(),
                                 QtGui.QColor(snap_color.r, snap_color.g, snap_color.b))
                    lane_frame.setPalette(pal)
                else:
                    lane_frame.setPalette(self.palette())
