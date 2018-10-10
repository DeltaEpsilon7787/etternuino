import os
from fractions import Fraction

import serial
from PyQt5 import QtCore, QtWidgets

from GUI.visuterna_window.visuterna_window import VisuternaWindow
from basic_types import Time
from chart_parser import parse_simfile
from chart_player import ChartPlayer
from GUI.chart_selection_dialog.chart_selection import ChartSelectionDialog
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_UNCHANGED, LANE_PINS, \
    SNAP_PINS, capture_exceptions, in_reduce


class EtternuinoApp(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)

        self.setObjectName("self")
        self.resize(254, 463)
        self.setWindowTitle("Etternuino")
        self.main_widget = QtWidgets.QWidget(self)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.main_widget)
        self.lane_group = QtWidgets.QWidget(self.main_widget)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.lane_group)
        self.lane_0 = QtWidgets.QFrame(self.lane_group)
        self.lane_1 = QtWidgets.QFrame(self.lane_group)
        self.lane_2 = QtWidgets.QFrame(self.lane_group)
        self.lane_3 = QtWidgets.QFrame(self.lane_group)
        self.checkbox_group = QtWidgets.QWidget(self.main_widget)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.checkbox_group)
        self.play_music_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.signal_arduino_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.add_claps_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.play_group = QtWidgets.QWidget(self.main_widget)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.play_group)
        self.play_file_btn = QtWidgets.QPushButton(self.play_group)
        self.control_group = QtWidgets.QWidget(self.main_widget)
        self.play_active_group = QtWidgets.QHBoxLayout(self.control_group)
        self.pause_stop_group = QtWidgets.QWidget(self.control_group)
        self.ctrl_button_group = QtWidgets.QVBoxLayout(self.pause_stop_group)
        self.pause_btn = QtWidgets.QPushButton(self.pause_stop_group)
        self.unpause_btn = QtWidgets.QPushButton(self.pause_stop_group)
        self.stop_btn = QtWidgets.QPushButton(self.pause_stop_group)
        self.label_3 = QtWidgets.QLabel(self.control_group)
        self.progress_slider = QtWidgets.QSlider(self.control_group)
        self.widget = QtWidgets.QWidget(self.main_widget)

        self.chart_selection = ChartSelectionDialog()
        self.virtual_arduino = VisuternaWindow()
        self.active_threads = []
        self.player = None
        self.arduino = None
        self.setup_ui()

        try:
            self.arduino = serial.Serial('COM4')
        except serial.SerialException:
            try:
                self.arduino = serial.Serial('/dev/ttyUSB0')
            except serial.SerialException:
                self.signal_arduino_checkbox.setVisible(False)

        self.show()

    def setup_ui(self):
        self.main_widget.setObjectName("main_widget")
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.lane_group.setObjectName("lane_group")
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lane_0.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_0.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_0.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_0.setObjectName("lane_0")
        self.horizontalLayout.addWidget(self.lane_0)
        self.lane_1.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_1.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_1.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_1.setObjectName("lane_1")
        self.horizontalLayout.addWidget(self.lane_1)
        self.lane_2.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_2.setObjectName("lane_2")
        self.horizontalLayout.addWidget(self.lane_2)
        self.lane_3.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_3.setObjectName("lane_3")
        self.horizontalLayout.addWidget(self.lane_3)
        self.verticalLayout_2.addWidget(self.lane_group)
        self.checkbox_group.setObjectName("checkbox_group")
        self.verticalLayout.setObjectName("verticalLayout")
        self.play_music_checkbox.setChecked(True)
        self.play_music_checkbox.setObjectName("play_music_checkbox")
        self.verticalLayout.addWidget(self.play_music_checkbox)
        self.signal_arduino_checkbox.setChecked(True)
        self.signal_arduino_checkbox.setObjectName("signal_arduino_checkbox")
        self.verticalLayout.addWidget(self.signal_arduino_checkbox)
        self.add_claps_checkbox.setObjectName("add_claps_checkbox")
        self.verticalLayout.addWidget(self.add_claps_checkbox)
        self.verticalLayout_2.addWidget(self.checkbox_group)
        self.play_group.setObjectName("play_group")
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.play_file_btn.setFlat(False)
        self.play_file_btn.setObjectName("play_file_btn")
        self.horizontalLayout_2.addWidget(self.play_file_btn)
        self.verticalLayout_2.addWidget(self.play_group)
        self.control_group.setObjectName("control_group")
        self.play_active_group.setObjectName("play_active_group")
        self.pause_stop_group.setEnabled(True)
        self.pause_stop_group.setObjectName("pause_stop_group")
        self.ctrl_button_group.setObjectName("ctrl_button_group")
        self.pause_btn.setObjectName("pause_btn")
        self.ctrl_button_group.addWidget(self.pause_btn)
        self.unpause_btn.setObjectName("unpause_btn")
        self.unpause_btn.setVisible(False)
        self.ctrl_button_group.addWidget(self.unpause_btn)
        self.stop_btn.setObjectName("stop_btn")
        self.ctrl_button_group.addWidget(self.stop_btn)
        self.play_active_group.addWidget(self.pause_stop_group)
        self.label_3.setObjectName("label_3")
        self.play_active_group.addWidget(self.label_3)
        self.progress_slider.setMaximum(0)
        self.progress_slider.setSingleStep(4410)
        self.progress_slider.setPageStep(44100)
        self.progress_slider.setOrientation(QtCore.Qt.Horizontal)
        self.progress_slider.setObjectName("progress_slider")
        self.play_active_group.addWidget(self.progress_slider)
        self.verticalLayout_2.addWidget(self.control_group)
        self.widget.setObjectName("widget")
        self.setCentralWidget(self.main_widget)

        self.retranslate_ui()
        self.play_file_btn.clicked.connect(self.play_file)
        self.pause_btn.clicked.connect(self.pause)
        self.unpause_btn.clicked.connect(self.unpause)
        self.stop_btn.clicked.connect(self.stop)
        self.play_music_checkbox.toggled['bool'].connect(self.play_music)
        self.signal_arduino_checkbox.toggled['bool'].connect(self.signal_arduino)
        self.add_claps_checkbox.toggled['bool'].connect(self.add_claps)
        self.progress_slider.sliderMoved['int'].connect(self.change_current_time)
        self.progress_slider.sliderReleased.connect(self.update_player)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.set_control_group_visibility(False)

    def retranslate_ui(self):
        _translate = QtCore.QCoreApplication.translate
        self.play_music_checkbox.setText(_translate("self", "Play music"))
        self.signal_arduino_checkbox.setText(_translate("self", "Signal Arduino"))
        self.add_claps_checkbox.setText(_translate("self", "Add claps"))
        self.play_file_btn.setText(_translate("self", "Play file"))
        self.pause_btn.setText(_translate("self", "Pause"))
        self.unpause_btn.setText(_translate("self", "Unpause"))
        self.stop_btn.setText(_translate("self", "Stop"))
        self.label_3.setText(_translate("self", "Progress:"))

    @QtCore.pyqtSlot(bool)
    def set_control_group_visibility(self, state):
        self.control_group.setVisible(state)

    @QtCore.pyqtSlot(bool)
    def set_play_group_visibility(self, state):
        self.play_group.setVisible(state)

    @QtCore.pyqtSlot(int)
    def change_current_time(self, new_value):
        if self.player:
            self.player.mixer.current_frame = new_value

    @QtCore.pyqtSlot()
    def update_player(self):
        self.player.need_to_update_position = True

    @capture_exceptions
    def chart_selected(self, parsed_simfile, chart_num):
        if chart_num < 0:
            return
        self.player = ChartPlayer(
            simfile=parsed_simfile, chart_num=chart_num,
            sound_start_delta=Time(Fraction(0, 1)),
            arduino=self.arduino,
            music_out=self.play_music_checkbox.isChecked(),
            clap_mapper=None,
            progress_slider_output=self.progress_slider
        )

        self.progress_slider.setMaximum(self.player.mixer.data.shape[0])
        self.progress_slider.setValue(0)

        self.player.on_start.connect(lambda: self.set_play_group_visibility(False))
        self.player.on_start.connect(lambda: self.set_control_group_visibility(True))
        self.player.on_start.connect(self.virtual_arduino.show)

        self.player.chart_obtained.connect(self.virtual_arduino.analyze_chart)
        self.player.time_arrived.connect(self.virtual_arduino.rewind_to)

        self.player.on_end.connect(lambda: self.set_play_group_visibility(True))
        self.player.on_end.connect(lambda: self.set_control_group_visibility(False))
        self.player.on_end.connect(self.virtual_arduino.close)

        player_thread = QtCore.QThread()
        player_thread.start()
        self.player.moveToThread(player_thread)
        self.player.start.emit()
        self.active_threads.append(player_thread)
        self.player.on_end.connect(lambda: self.active_threads.remove(player_thread))
        self.player.on_end.connect(self.cleanup)

    @QtCore.pyqtSlot()
    @capture_exceptions
    def play_file(self):
        sm_file, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose SM file...', os.getcwd(),
                                                           'Simfiles (*.sm)')
        if sm_file == "":
            return
        parsed_simfile = parse_simfile(sm_file)
        self.chart_selection.chart_list.clear()
        for index, chart in enumerate(parsed_simfile.charts, 1):
            self.chart_selection.chart_list.addItem(f'{index}: {chart.diff_name}')
        self.chart_selection.on_selection.connect(lambda chart_num: self.chart_selected(parsed_simfile, chart_num))
        self.chart_selection.on_cancel.connect(self.cleanup)
        self.chart_selection.show()

    @QtCore.pyqtSlot()
    def pause(self):
        self.player and self.player.pause()
        self.unpause_btn.setVisible(True)
        self.pause_btn.setVisible(False)

    @QtCore.pyqtSlot()
    def unpause(self):
        self.player and self.player.unpause()
        self.unpause_btn.setVisible(False)
        self.pause_btn.setVisible(True)

    @QtCore.pyqtSlot()
    def stop(self):
        self.player.die()

    @QtCore.pyqtSlot()
    def cleanup(self):
        if self.chart_selection:
            self.chart_selection.on_selection.disconnect()
            self.chart_selection.on_cancel.disconnect()
        if self.player:
            self.player.cleanup()
        if self.arduino:
            self.arduino.write(BYTE_FALSE * ARDUINO_MESSAGE_LENGTH)

    @QtCore.pyqtSlot(bool)
    def play_music(self, new_state):
        if not self.player:
            return
        self.player.mixer.muted = not new_state

    @QtCore.pyqtSlot(bool)
    def signal_arduino(self, new_state):
        if not self.player:
            return
        self.player.arduino_muted = not new_state

    @QtCore.pyqtSlot(bool)
    def add_claps(self, new_state):
        pass

    @QtCore.pyqtSlot(bytes)
    @capture_exceptions
    def interpret_message(self, message: bytes):
        if in_reduce(all, message, (BYTE_UNCHANGED,)):
            return

        self.virtual_arduino.toggle_lanes([message[LANE_PINS[i]] for i in range(4)])
        self.virtual_arduino.toogle_snap([
            snap
            for snap in [
                message[SNAP_PINS[possible_snap]] and possible_snap or None
                for possible_snap in [4, 8, 12, 16, 24]
            ]
            if snap is not None
        ])


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    the_app = EtternuinoApp()

    sys.exit(app.exec_())
