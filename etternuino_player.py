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
import soundfile as sf
from PyQt5 import QtCore, QtWidgets

from basic_types import Time
from chart_parser import Simfile, parse_simfile
from chart_selection_ui import ChartSelectionDialog
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_TRUE, BYTE_UNCHANGED, DEFAULT_SAMPLE_RATE, LANE_PINS, \
    SNAP_PINS, capture_exceptions, in_reduce
from rows import GlobalScheduledRow, GlobalTimedRow, Snap


class Mixer(object):
    def __init__(self, data=np.zeros((60 * DEFAULT_SAMPLE_RATE, 2)), sample_rate=DEFAULT_SAMPLE_RATE):
        self.data = data.copy()
        self.sample_rate = sample_rate
        self.current_frame = 0
        self.muted = False
        self.paused = False

    @classmethod
    def from_file(cls, source_file: str, sound_start: Time = 0):
        data, sample_rate = sf.read(source_file, dtype='float32')
        mixer = cls(data, sample_rate)

        if sound_start < 0:
            padded = np.zeros((mixer.sample_rate * abs(sound_start), mixer.data.shape[1]))
            mixer.data = np.concatenate((padded, mixer.data))
        else:
            mixer.data = mixer.data[int(mixer.sample_rate * sound_start):]

        return mixer

    def add_sound(self, sound_data: np.ndarray, at_time: Time):
        sample_start = int(self.sample_rate * at_time)
        if sample_start + sound_data.shape[0] >= self.data.shape[0]:
            offset = sample_start + sound_data.shape[0] - self.data.shape[0]
            self.data = np.pad(
                self.data,
                (
                    (0, offset),
                    (0, 0)
                ),
                'constant'
            )
        self.data[sample_start: sample_start + sound_data.shape[0]] += sound_data

        max_volume = np.max(self.data[sample_start: sample_start + sound_data.shape[0]],
                            axis=0)[0]
        if max_volume > 1:
            self.data[sample_start: sample_start + sound_data.shape[0]] *= 1 / max_volume

    def __call__(self, out_data: np.ndarray, frames: int, at_time, status: int):
        sample_start = self.current_frame

        if sample_start + frames > self.data.shape[0] or self.paused:
            out_data.fill(0)
        else:
            if self.muted:
                out_data.fill(0)
            else:
                out_data[:] = self.data[sample_start:sample_start + frames]
            self.current_frame += frames

    @property
    def current_time(self) -> Time:
        return Time(Fraction(self.current_frame, self.sample_rate))


class BaseClapMapper(Callable):
    @classmethod
    def __call__(cls, row: GlobalTimedRow) -> np.ndarray:
        return NotImplemented


class ChartPlayer(QtCore.QObject):
    start: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_start: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_end: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_write: QtCore.pyqtSignal = QtCore.pyqtSignal('char*')

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
        self.arduino = arduino and serial.Serial(arduino)
        self.arduino_muted = False
        self.music_out = music_out
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
            if self.need_to_update_position:
                break

    def pause(self):
        self.mixer.paused = True

    def unpause(self):
        self.mixer.paused = False

    @capture_exceptions
    def schedule_events(self, notes: Sequence[GlobalScheduledRow]):
        TURN_OFF = 0
        TURN_ON = 1
        TURN_ON_AND_BLINK = 2

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
                                  TURN_OFF,
                                  row_time - self.microblink_duration))

                events.append(
                    NoteEvent(pin,
                              TURN_ON_AND_BLINK if pin not in hold_pins else TURN_ON,
                              row_time)
                )

            for pin in deactivated_pins:
                events.append(NoteEvent(pin, TURN_OFF, row_time))

            last_row_time = row_time

        events.sort(key=attrgetter('time'))

        state_sequence: List[Tuple[Time, bytes]] = []
        for time_point, event_group in groupby(events, attrgetter('time')):
            sequence = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
            blink_sequence = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
            for event in event_group:
                sequence[event.pin] = BYTE_TRUE if event.state in (TURN_ON, TURN_ON_AND_BLINK) else BYTE_FALSE
                blink_sequence[event.pin] = BYTE_FALSE if event.state is TURN_ON_AND_BLINK else BYTE_UNCHANGED

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

        first_note = notes[0]
        sequence = list(self.schedule_events(notes))

        self.music_stream and self.music_stream.start()
        self.unpause()
        self.wait_till(first_note.time)

        current_index = 0
        while current_index < len(sequence):
            time_point, message = sequence[current_index]
            self.wait_till(time_point)
            self.on_write.emit(message)
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


    @QtCore.pyqtSlot()
    def die(self):
        self.need_to_die = True

    def cleanup(self):
        self.music_stream and self.music_stream.stop()
        self.arduino and self.arduino.write(BYTE_FALSE * ARDUINO_MESSAGE_LENGTH)
        self.on_end.emit()


class EtternuinoApp(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.chart_selection = ChartSelectionDialog()
        self.active_threads = []
        self.setup_ui()

        self.show()

    def setup_ui(self):
        self.setObjectName("self")
        self.resize(254, 463)
        self.setWindowTitle("Etternuino")
        self.main_widget = QtWidgets.QWidget(self)
        self.main_widget.setObjectName("main_widget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.main_widget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.lane_group = QtWidgets.QWidget(self.main_widget)
        self.lane_group.setObjectName("lane_group")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.lane_group)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lane_0 = QtWidgets.QFrame(self.lane_group)
        self.lane_0.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_0.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_0.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_0.setObjectName("lane_0")
        self.horizontalLayout.addWidget(self.lane_0)
        self.lane_1 = QtWidgets.QFrame(self.lane_group)
        self.lane_1.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_1.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_1.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_1.setObjectName("lane_1")
        self.horizontalLayout.addWidget(self.lane_1)
        self.lane_2 = QtWidgets.QFrame(self.lane_group)
        self.lane_2.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_2.setObjectName("lane_2")
        self.horizontalLayout.addWidget(self.lane_2)
        self.lane_3 = QtWidgets.QFrame(self.lane_group)
        self.lane_3.setMinimumSize(QtCore.QSize(50, 50))
        self.lane_3.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lane_3.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lane_3.setObjectName("lane_3")
        self.horizontalLayout.addWidget(self.lane_3)
        self.verticalLayout_2.addWidget(self.lane_group)
        self.checkbox_group = QtWidgets.QWidget(self.main_widget)
        self.checkbox_group.setObjectName("checkbox_group")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.checkbox_group)
        self.verticalLayout.setObjectName("verticalLayout")
        self.play_music_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.play_music_checkbox.setChecked(True)
        self.play_music_checkbox.setObjectName("play_music_checkbox")
        self.verticalLayout.addWidget(self.play_music_checkbox)
        self.signal_arduino_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.signal_arduino_checkbox.setChecked(True)
        self.signal_arduino_checkbox.setObjectName("signal_arduino_checkbox")
        self.verticalLayout.addWidget(self.signal_arduino_checkbox)
        self.add_claps_checkbox = QtWidgets.QCheckBox(self.checkbox_group)
        self.add_claps_checkbox.setObjectName("add_claps_checkbox")
        self.verticalLayout.addWidget(self.add_claps_checkbox)
        self.verticalLayout_2.addWidget(self.checkbox_group)
        self.play_group = QtWidgets.QWidget(self.main_widget)
        self.play_group.setObjectName("play_group")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.play_group)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.play_file_btn = QtWidgets.QPushButton(self.play_group)
        self.play_file_btn.setFlat(False)
        self.play_file_btn.setObjectName("play_file_btn")
        self.horizontalLayout_2.addWidget(self.play_file_btn)
        self.verticalLayout_2.addWidget(self.play_group)
        self.control_group = QtWidgets.QWidget(self.main_widget)
        self.control_group.setObjectName("control_group")
        self.play_active_group = QtWidgets.QHBoxLayout(self.control_group)
        self.play_active_group.setObjectName("play_active_group")
        self.pause_stop_group = QtWidgets.QWidget(self.control_group)
        self.pause_stop_group.setEnabled(True)
        self.pause_stop_group.setObjectName("pause_stop_group")
        self.ctrl_button_group = QtWidgets.QVBoxLayout(self.pause_stop_group)
        self.ctrl_button_group.setObjectName("ctrl_button_group")
        self.pause_btn = QtWidgets.QPushButton(self.pause_stop_group)
        self.pause_btn.setObjectName("pause_btn")
        self.ctrl_button_group.addWidget(self.pause_btn)
        self.stop_btn = QtWidgets.QPushButton(self.pause_stop_group)
        self.stop_btn.setObjectName("stop_btn")
        self.ctrl_button_group.addWidget(self.stop_btn)
        self.play_active_group.addWidget(self.pause_stop_group)
        self.label_3 = QtWidgets.QLabel(self.control_group)
        self.label_3.setObjectName("label_3")
        self.play_active_group.addWidget(self.label_3)
        self.progress_slider = QtWidgets.QSlider(self.control_group)
        self.progress_slider.setMaximum(0)
        self.progress_slider.setSingleStep(4410)
        self.progress_slider.setPageStep(44100)
        self.progress_slider.setOrientation(QtCore.Qt.Horizontal)
        self.progress_slider.setObjectName("progress_slider")
        self.play_active_group.addWidget(self.progress_slider)
        self.verticalLayout_2.addWidget(self.control_group)
        self.widget = QtWidgets.QWidget(self.main_widget)
        self.widget.setObjectName("widget")
        self.setCentralWidget(self.main_widget)

        self.retranslate_ui()
        self.play_file_btn.clicked.connect(self.play_file)
        self.pause_btn.clicked.connect(self.pause)
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
        self.stop_btn.setText(_translate("self", "Stop"))
        self.label_3.setText(_translate("self", "Progress:"))

    @QtCore.pyqtSlot('bool')
    def set_control_group_visibility(self, state):
        self.control_group.setVisible(state)

    @QtCore.pyqtSlot('bool')
    def set_play_group_visibility(self, state):
        self.play_group.setVisible(state)

    @QtCore.pyqtSlot('int')
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
        arduino_port = self.signal_arduino_checkbox.isChecked() and 'COM4' or None
        self.player = ChartPlayer(
            simfile=parsed_simfile, chart_num=chart_num,
            sound_start_delta=Time(Fraction(0, 1)),
            arduino=arduino_port,
            music_out=self.play_music_checkbox.isChecked(),
            clap_mapper=None,
            progress_slider_output=self.progress_slider
        )

        self.progress_slider.setMaximum(self.player.mixer.data.shape[0])
        self.progress_slider.setValue(0)


        self.player.on_start.connect(lambda: self.set_play_group_visibility(False))
        self.player.on_start.connect(lambda: self.set_control_group_visibility(True))
        self.player.on_write.connect(self.interpret_message)
        self.player.on_end.connect(lambda: self.set_play_group_visibility(True))
        self.player.on_end.connect(lambda: self.set_control_group_visibility(False))

        player_thread = QtCore.QThread()
        player_thread.start()
        self.player.moveToThread(player_thread)
        self.player.start.emit()
        self.active_threads.append(player_thread)
        self.player.on_end.connect(lambda: self.active_threads.remove(player_thread))


    @QtCore.pyqtSlot()
    def play_file(self):
        sm_file, _ = QtWidgets.QFileDialog.getOpenFileName(None, 'Choose SM file...', os.getcwd(),
                                                           'Simfiles (*.sm)')
        if sm_file == "":
            return
        parsed_simfile = parse_simfile(sm_file)
        self.chart_selection.chart_list.clear()
        for index, chart in enumerate(parsed_simfile.charts, 1):
            self.chart_selection.chart_list.addItem(f'{index}: {chart.diff_name}')
        self.chart_selection.on_selection.connect(lambda chart_num: self.chart_selected(parsed_simfile, chart_num))
        self.chart_selection.show()

    @QtCore.pyqtSlot()
    def pause(self):
        self.player and self.player.pause()

    @QtCore.pyqtSlot()
    def unpause(self):
        self.player and self.player.unpause()

    @QtCore.pyqtSlot()
    def stop(self):
        self.player.die()

    @QtCore.pyqtSlot('bool')
    def play_music(self, new_state):
        if not self.player:
            return
        self.player.mixer.muted = not new_state

    @QtCore.pyqtSlot('bool')
    def signal_arduino(self, new_state):
        if not self.player:
            return
        self.player.arduino_muted = not new_state

    @QtCore.pyqtSlot('bool')
    def add_claps(self, new_state):
        pass

    @QtCore.pyqtSlot('char *')
    def interpret_message(self, message):
        pass


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    the_app = EtternuinoApp()

    sys.exit(app.exec_())
