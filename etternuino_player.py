import os
from collections import Callable, deque
from fractions import Fraction
from itertools import groupby
from operator import attrgetter, itemgetter
from typing import List, Optional, Sequence, Set, Tuple

import attr
import numpy as np
import pydub
import serial
import sounddevice as sd
from PyQt5 import QtCore, QtWidgets

from arduino_dialog import VirtualArduino
from basic_types import Time
from chart_parser import Simfile, parse_simfile
from chart_selection_ui import ChartSelectionDialog
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_TRUE, BYTE_UNCHANGED, DEFAULT_SAMPLE_RATE, LANE_PINS, \
    SNAP_PINS, capture_exceptions, in_reduce
from mixer import Mixer
from rows import GlobalScheduledRow, GlobalTimedRow, Snap


class BaseClapMapper(Callable):
    @classmethod
    def __call__(cls, row: GlobalTimedRow) -> np.ndarray:
        return NotImplemented


class ChartPlayer(QtCore.QObject):
    chart_obtained: QtCore.pyqtSignal = QtCore.pyqtSignal(object)
    start: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_start: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_end: QtCore.pyqtSignal = QtCore.pyqtSignal()
    time_arrived: QtCore.pyqtSignal = QtCore.pyqtSignal(object)

    def __init__(self,
                 simfile: Simfile,
                 chart_num: int = 0,
                 sound_start_delta: Time = 0,
                 arduino: Optional[str] = None,
                 music_out: bool = True,
                 clap_mapper: Optional[BaseClapMapper] = None,
                 progress_slider_output=None):
        QtCore.QObject.__init__(self)
        self.simfile = simfile
        self.chart_num = chart_num
        self.sound_start_delta = sound_start_delta
        self.arduino = arduino
        self.arduino_muted = False
        self.clap_mapper = clap_mapper

        self.mixer = None
        self.music_stream = None

        pydub.AudioSegment.from_file(simfile.music).export('temp.wav', format='wav')
        self.mixer = Mixer.from_file('temp.wav', self.sound_start_delta)
        self.mixer.muted = not music_out
        self.music_stream = sd.OutputStream(channels=2,
                                            samplerate=DEFAULT_SAMPLE_RATE,
                                            dtype='float32',
                                            callback=self.mixer)

        self.microblink_duration = Fraction('0.01')
        self.blink_duration = Fraction('0.06')

        self.need_to_die = False
        self.need_to_update_position = False
        self.progress_slider_output = progress_slider_output
        self.start.connect(self.run)

    def wait_till(self, end_time: Time) -> None:
        while self.mixer.current_time < end_time:
            if self.progress_slider_output:
                self.progress_slider_output.setValue(self.mixer.current_frame)
            if self.need_to_update_position or self.need_to_die:
                break
            sd.sleep(1)

    def pause(self):
        self.mixer.paused = True

    def unpause(self):
        self.mixer.paused = False

    @capture_exceptions
    def schedule_events(self, notes: Sequence[GlobalScheduledRow]):
        turn_off = 0
        turn_on = 1
        turn_on_and_blink = 2

        @attr.attrs
        class NoteEvent(object):
            """Set `pin` to `state` at `time`"""
            pin: int = attr.attrib()
            state: int = attr.attrib()
            time: Time = attr.attrib()

        events: List[NoteEvent] = []

        hold_pins: Set[int] = set()
        last_row_time = 0
        for row in notes:
            row_time = row.time
            row_snap = Snap.from_row(row)

            activated_pins = set()
            deactivated_pins = set()

            if not in_reduce(all, row.objects, ('0', '3', '5', 'M')):
                deactivated_pins |= set(SNAP_PINS.values()) - set(row_snap.arduino_pins)
                activated_pins |= set(row_snap.arduino_pins)

            for lane, note in enumerate(row.objects):
                lane_pin = LANE_PINS[lane]
                if note in ('1',):
                    activated_pins.add(lane_pin)

                if note in ('2', '4'):
                    activated_pins.add(lane_pin)
                    hold_pins.add(lane_pin)

                if note in ('3', '5'):
                    deactivated_pins.add(lane_pin)
                    hold_pins -= {lane_pin}

            for pin in activated_pins:
                if row_time - last_row_time < self.blink_duration:
                    events.append(
                        NoteEvent(pin,
                                  turn_off,
                                  row_time - self.microblink_duration))

                events.append(
                    NoteEvent(pin,
                              turn_on_and_blink if pin not in hold_pins else turn_on,
                              row_time)
                )

            for pin in deactivated_pins:
                events.append(NoteEvent(pin, turn_off, row_time))

            last_row_time = row_time

        events.sort(key=attrgetter('time'))

        state_sequence: List[Tuple[Time, bytes]] = []
        for time_point, event_group in groupby(events, attrgetter('time')):
            sequence = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
            blink_sequence = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
            for event in event_group:
                sequence[event.pin] = BYTE_TRUE if event.state in (turn_on, turn_on_and_blink) else BYTE_FALSE
                blink_sequence[event.pin] = BYTE_FALSE if event.state is turn_on_and_blink else BYTE_UNCHANGED

            if not in_reduce(all, blink_sequence, (BYTE_UNCHANGED,)):
                state_sequence.append((Time(time_point + self.blink_duration), b''.join(blink_sequence)))
            state_sequence.append((Time(time_point), b''.join(sequence)))

        state_sequence.sort(key=itemgetter(0))

        return state_sequence

    @QtCore.pyqtSlot()
    @capture_exceptions
    def run(self):
        try:
            chart = self.simfile.charts[self.chart_num]
        except IndexError:
            self.cleanup()
            return

        notes = sorted(chart.note_field)
        notes = deque(
            row
            for row in notes
            if not in_reduce(all, row.objects, ('0', 'M'))
        )

        self.on_start.emit()

        if self.clap_mapper:
            for row in notes:
                self.mixer.add_sound(self.clap_mapper(row), row.time)

        notes = deque(
            GlobalScheduledRow.from_source(row, self.sound_start_delta)
            for row in notes
        )

        self.chart_obtained.emit(notes)

        first_note = notes[0]
        sequence = list(self.schedule_events(notes))

        self.music_stream and self.music_stream.start()
        self.unpause()
        self.wait_till(first_note.time)

        current_index = 0
        while current_index < len(sequence):
            time_point, message = sequence[current_index]
            self.wait_till(time_point)
            self.time_arrived.emit(time_point)
            self.arduino and not self.arduino_muted and self.arduino.write(message)
            if self.need_to_die:
                self.cleanup()
                return
            if self.need_to_update_position:
                current_index = [
                    index
                    for index, event in enumerate(sequence)
                    if event[0] >= self.mixer.current_time
                ][0]
                self.need_to_update_position = False
            current_index += 1

        self.on_end.emit()

    @QtCore.pyqtSlot()
    def die(self):
        self.need_to_die = True

    def cleanup(self):
        self.music_stream and self.music_stream.stop()
        self.on_end.emit()
        self.disconnect()


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
        self.virtual_arduino = VirtualArduino()
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
