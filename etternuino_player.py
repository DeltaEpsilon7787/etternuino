import io
import time
from collections import Callable, deque
from fractions import Fraction
from typing import Optional

import numpy as np
import pydub
import serial
import sounddevice as sd
import soundfile as sf
from PyQt5 import QtCore

from basic_types import Time
from chart_parser import Simfile
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_TRUE, BYTE_UNCHANGED, DEFAULT_SAMPLE_RATE, in_reduce
from rows import GlobalScheduledRow, GlobalTimedRow, Snap


class Mixer(object):
    def __init__(self, data: np.ndarray, sample_rate: int):
        self.data = data
        self.sample_rate = sample_rate
        self.current_frame = 0

    @classmethod
    def from_file(cls, source_file: str, sound_start: Time = 0):
        data, sample_rate = sf.read(source_file, dtype='float32')
        mixer = cls(data, sample_rate)

        if sound_start < 0:
            padded = np.zeros((mixer.sample_rate * abs(sound_start), mixer.data.shape[1]))
            mixer.data = np.concatenate((padded, mixer.data))
        else:
            mixer.data = mixer.data[mixer.sample_rate * sound_start:]

        return mixer

    @classmethod
    def null_mixer(cls):
        return cls(np.zeros(60 * DEFAULT_SAMPLE_RATE, 2), DEFAULT_SAMPLE_RATE)

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

    def __call__(self, outdata, frames, at_time, status):
        sample_start = self.current_frame
        if sample_start + frames > self.data.shape[0]:
            outdata.fill(0)
        else:
            outdata[:] = self.data[sample_start:sample_start + frames]
            self.current_frame += frames


class EtternuinoTimer:
    def __init__(self, initial_time=0):
        self.current_time = initial_time
        self._real_timer = QtCore.QTimer()
        self._real_timer.timeout().connect
        self._is_paused = False

    @QtCore.pyQtSlot()
    def pause(self):
        self._is_paused = True

    @QtCore.pyqtSlot()
    def unpause(self):
        self._is_paused = False


class BaseClapMapper(Callable):
    @classmethod
    def __call__(cls, row: GlobalTimedRow) -> np.ndarray:
        return NotImplemented


class ChartPlayer(QtCore.QObject):
    activate_signal = QtCore.pyqtSignal(name='activation_signal')

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

        self.is_paused = False

        music = self.music_out and simfile.music.contents
        if music:
            audio = pydub.AudioSegment.from_file(io.BytesIO(music))
            audio.export('temp.wav', format='wav')
            self.mixer = Mixer.from_file('temp.wav', self.sound_start_delta)
        elif self.clap:
            self.mixer = Mixer.null_mixer()

        if self.mixer:
            self.music_stream = sd.OutputStream(channels=2,
                                                samplerate=DEFAULT_SAMPLE_RATE,
                                                dtype='float32',
                                                callback=self.mixer)
            # Music based timer, significantly more accurate
            self.time_function = lambda: self.mixer.current_frame / self.mixer.sample_rate

        self.microblink_duration = Fraction('0.01') if self.arduino else 0
        self.blink_duration = Fraction('0.06') if self.arduino else 0

        self.time_function = time.perf_counter
        self.is_active = False

        self.blink_schedule = [0] * ARDUINO_MESSAGE_LENGTH

    def wait_till(self, end_time: Time) -> None:
        while self.time_function() < end_time:
            pass

    @QtCore.pyQtSlot()
    def pause(self):
        self.is_paused = True

    @QtCore.pyqtSlot()
    def run(self):
        try:
            chart = self.simfile.charts[self.chart_num]
        except IndexError:
            return

        notes = sorted(chart.notefield)
        notes = deque(
            row
            for row in notes
            if not in_reduce(all, row.objects, ('0', 'M'))
        )

        self.activate_signal.emit()
        self.is_active = True

        if self.clap_mapper:
            for row in notes:
                self.mixer.add_sound(self.clap_mapper(row), row.time)

        self.music_stream and self.music_stream.start()
        start = self.time_function() - self.sound_start_delta

        notes = deque(
            GlobalScheduledRow.from_source(row, start)
            for row in notes
        )

        first_note = notes[0]
        self.wait_till(first_note.time)

        while notes:
            if not self.is_active:
                self.die()
                return

            current_row = notes.popleft()
            current_snap = Snap.from_row(current_row)
            next_row = notes[0] if notes else current_row

            if self.arduino:
                blink_message = [BYTE_UNCHANGED] * 10
                new_message = [BYTE_UNCHANGED] * 10

                if not in_reduce(all, current_row.objects, ('0', '3', '5')):
                    new_message[4:] = [BYTE_FALSE] * 6
                    for pin in current_snap.arduino_pins:
                        new_message[pin] = BYTE_TRUE

                for lane, note in enumerate(current_row.objects):
                    if note in ('1',):
                        if self.blink_schedule[lane_map[lane]]:
                            blink_message[lane_map[lane]] = BYTE_FALSE
                        new_message[lane_map[lane]] = BYTE_TRUE
                        self.blink_schedule[lane_map[lane]] = current_row.time + BLINK_DURATION

                    elif note in ('2', '4'):
                        new_message[lane_map[lane]] = BYTE_TRUE
                        self.blink_schedule[lane_map[lane]] = 0

                    elif note in ('3', '5'):
                        new_message[lane_map[lane]] = BYTE_TRUE

                self.arduino and not in_reduce(all, blink_message, (BYTE_UNCHANGED,)) and arduino.write(
                    b''.join(blink_message))
                self.wait_till(current_row.time)
                self.arduino and self.arduino.write(b''.join(new_message))

            next_row_time = next_row.time - self.microblink_duration
            next_state = None
            if in_reduce(all, off_schedule, (0,)):
                next_state = next_row.time
            else:
                filtered_schedule = (
                    timing
                    for timing in off_schedule
                    if timing != 0
                )
                next_state = min(*filtered_schedule, next_row_time)

                self.wait_till(next_state)

            if next_state is next_row_time:
                continue

            if self.arduino:
                off_message = [BYTE_UNCHANGED] * 10
                for pin, timing in enumerate(off_schedule):
                    if not timing:
                        continue
                    if time_function() >= timing:
                        off_message[pin] = BYTE_FALSE
                        off_schedule[pin] = 0
                    arduino and arduino.write(b''.join(off_message))
            self.wait_till(next_row_time)

    @QtCore.pyqtSlot()
    def die(self):
        self.music_stream and music_stream.stop()
        self.arduino and arduino.write(BYTE_FALSE * 10)
