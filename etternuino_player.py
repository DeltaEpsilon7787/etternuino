import os
from collections import Callable, deque
from fractions import Fraction
from itertools import groupby
from operator import attrgetter, itemgetter
from typing import List, Optional, Sequence, Set, Tuple

import attr
import easygui_qt
import numpy as np
import pydub
import serial
import sounddevice as sd
import soundfile as sf
from PyQt5 import QtCore, QtWidgets

from basic_types import Time
from chart_parser import Simfile, parse_simfile
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_TRUE, BYTE_UNCHANGED, DEFAULT_SAMPLE_RATE, LANE_PINS, \
    SNAP_PINS, in_reduce
from rows import GlobalScheduledRow, GlobalTimedRow, Snap


@attr.attrs(auto_attribs=True, cmp=False)
class EtternuinoTimer:
    _real_timer: QtCore.QElapsedTimer = attr.attrib(factory=QtCore.QElapsedTimer, init=False)
    _is_paused: bool = True
    _offset: int = 0

    @QtCore.pyqtSlot()
    def pause(self):
        if not self._is_paused:
            self._offset += self._real_timer.nsecsElapsed() / 1e9
        self._is_paused = True

    @QtCore.pyqtSlot()
    def unpause(self):
        self._is_paused = False
        self._real_timer.start()

    @property
    def current_time(self):
        if self._is_paused:
            return self._offset

        return (
                self._real_timer.nsecsElapsed() / 1e9 + self._offset
        )

    @property
    def is_paused(self):
        return self._is_paused


class Mixer(object):
    def __init__(self, timer, data=np.zeros((60 * DEFAULT_SAMPLE_RATE, 2)), sample_rate=DEFAULT_SAMPLE_RATE):
        self.timer = timer
        self.data = data.copy()
        self.sample_rate = sample_rate
        self.current_frame = 0

    @classmethod
    def from_file(cls, timer: EtternuinoTimer, source_file: str, sound_start: Time = 0):
        data, sample_rate = sf.read(source_file, dtype='float32')
        mixer = cls(timer, data, sample_rate)

        if sound_start < 0:
            padded = np.zeros((mixer.sample_rate * abs(sound_start), mixer.data.shape[1]))
            mixer.data = np.concatenate((padded, mixer.data))
        else:
            mixer.data = mixer.data[mixer.sample_rate * sound_start:]

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
        sample_start = int(self.sample_rate * self.timer.current_time)

        if np.abs(sample_start - self.current_frame) > frames * 100:
            self.current_frame += sample_start - self.current_frame

        sample_start = self.current_frame

        if sample_start + frames > self.data.shape[0] or self.timer.is_paused:
            out_data.fill(0)
        else:
            out_data[:] = self.data[sample_start:sample_start + frames]
            self.current_frame += frames


class BaseClapMapper(Callable):
    @classmethod
    def __call__(cls, row: GlobalTimedRow) -> np.ndarray:
        return NotImplemented


class ChartPlayer(QtCore.QObject):
    on_start: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_end: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_write: QtCore.pyqtSignal = QtCore.pyqtSignal()

    def __init__(self,
                 simfile: Simfile,
                 chart_num: int = 0,
                 sound_start_delta: Time = 0,
                 arduino: Optional[serial.Serial] = None,
                 music_out: bool = True,
                 clap_mapper: Optional[BaseClapMapper] = None):
        QtCore.QObject.__init__(self)
        self.simfile = simfile
        self.chart_num = chart_num
        self.sound_start_delta = sound_start_delta
        self.arduino = arduino
        self.music_out = music_out
        self.clap_mapper = clap_mapper

        self.mixer = None
        self.music_stream = None

        self.timer = EtternuinoTimer()

        music = self.music_out and simfile.music
        if music:
            pydub.AudioSegment.from_file(simfile.music).export('temp.wav', format='wav')
            self.mixer = Mixer.from_file(self.timer, 'temp.wav', self.sound_start_delta)
        elif self.clap_mapper:
            self.mixer = Mixer(self.timer)

        if self.mixer:
            self.music_stream = sd.OutputStream(channels=2,
                                                samplerate=DEFAULT_SAMPLE_RATE,
                                                dtype='float32',
                                                callback=self.mixer)

        self.microblink_duration = Fraction('0.01') if self.arduino else 0
        self.blink_duration = Fraction('0.06') if self.arduino else 0

    def wait_till(self, end_time: Time) -> None:
        while self.timer.current_time < end_time:
            pass

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

            if not in_reduce(all, row.objects, ('0', '3', '5')):
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
    def pause(self):
        self.timer.pause()

    @QtCore.pyqtSlot()
    def unpause(self):
        self.timer.unpause()

    @QtCore.pyqtSlot()
    def run(self):
        try:
            try:
                chart = self.simfile.charts[self.chart_num]
            except IndexError:
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
            sequence = self.schedule_events(notes)

            self.music_stream and self.music_stream.start()
            self.unpause()
            self.wait_till(first_note.time)

            try:
                for time_point, message in sequence:
                    self.wait_till(time_point)
                    self.on_write.emit(message)

            except KeyboardInterrupt:
                self.music_stream and self.music_stream.stop()
                self.arduino and self.arduino.write(BYTE_FALSE * ARDUINO_MESSAGE_LENGTH)
                self.on_end.emit()
        except Exception as E:
            print(E)

    @QtCore.pyqtSlot()
    def die(self):
        raise KeyboardInterrupt

class EtternuinoApp(QtWidgets.QMainWindow):
    @QtCore.pyqtSlot()
    def play_file(self):
        sm_file, _ = QtWidgets.QFileDialog.getOpenFileName(None, 'Choose SM file...', os.getcwd(), 'Simfiles (*.sm)')
        if sm_file is None:
            return
        parsed_simfile = parse_simfile(sm_file)
        pick = easygui_qt.get_choice('Select what chart to play',
                                     'Chart selection',
                                     [
                                         str(index) + ':' + str(parsed_simfile.charts[index].diff_name)
                                         for index in range(len(parsed_simfile.charts))
                                     ])
        if pick is None:
            return
        chart_num = int(pick.split(':')[0])
        try:
            arduino_port = self.parent().signal_arduino_checkbox.isChecked() and serial.Serial('/dev/ttyUSB0',
                                                                                               9600) or None
            self.player = ChartPlayer(simfile=parsed_simfile,
                                      chart_num=chart_num,
                                      sound_start_delta=Time(Fraction(0, 1)),
                                      arduino=arduino_port,
                                      music_out=self.parent().play_music_checkbox.isChecked(),
                                      clap_mapper=None)
        except:
            raise
        finally:
            arduino_port and arduino_port.close()

        player_thread = QtCore.QThread()
        self.player.moveToThread(player_thread)
        player_thread.started.connect(self.player.run)
        player_thread.start()

    @QtCore.pyqtSlot()
    def pause(self):
        pass

    @QtCore.pyqtSlot()
    def stop(self):
        pass

    @QtCore.pyqtSlot('bool')
    def play_music(self, new_state):
        pass

    @QtCore.pyqtSlot('bool')
    def signal_arduino(self, new_state):
        pass

    @QtCore.pyqtSlot('bool')
    def add_claps(self, new_state):
        pass
