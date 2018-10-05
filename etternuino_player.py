import io
from collections import Callable, deque
from fractions import Fraction
from itertools import groupby
from operator import attrgetter, itemgetter
from typing import Optional, Sequence, TextIO

import attr
import numpy as np
import pydub
import serial
import sounddevice as sd
import soundfile as sf
from PyQt5 import QtCore

from basic_types import NoteObjects, Time
from chart_parser import Simfile
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_TRUE, BYTE_UNCHANGED, DEFAULT_SAMPLE_RATE, LANE_PINS, \
    SNAP_PINS, in_reduce
from rows import GlobalScheduledRow, GlobalTimedRow, Snap


@attr.attrs(cmp=False)
class EtternuinoTimer:
    _real_timer = attr.attrib(factory=QtCore.QElapsedTimer, init=False)
    _is_paused: bool = True
    _offset: int = 0

    @QtCore.pyQtSlot()
    def pause(self):
        if not self._paused:
            self._offset += self._real_timer.nsecsElapsed()
        self._is_paused = True

    @QtCore.pyqtSlot()
    def unpause(self):
        self._is_paused = False
        self._real_timer.restart()

    @property
    def current_time(self):
        if self._is_paused:
            return self._offset

        return (
                self._real_timer.nsecsElapsed() + self._offset
        )


@attr.attrs(cmp=False)
class Mixer(object):
    timer: EtternuinoTimer = attr.NOTHING
    data: np.ndarray = np.zeros(60 * DEFAULT_SAMPLE_RATE, 2)
    sample_rate: int = DEFAULT_SAMPLE_RATE

    @classmethod
    def from_file(cls, timer: EtternuinoTimer, source_file: TextIO, sound_start: Time = 0):
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

    def __call__(self, outdata: np.ndarray, frames: int, at_time, status: int):
        sample_start = self.sample_rate * self.timer.current_time
        if sample_start + frames > self.data.shape[0]:
            outdata.fill(0)
        else:
            outdata[:] = self.data[sample_start:sample_start + frames]


class BaseClapMapper(Callable):
    @classmethod
    def __call__(cls, row: GlobalTimedRow) -> np.ndarray:
        return NotImplemented


class ChartPlayer(QtCore.QObject):
    on_start = QtCore.pyqtSignal(name='on_start')
    on_end = QtCore.pyqtSignal(name='on_end')
    on_write = QtCore.pyqtSignal('str', name='on_write')

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

        music = self.music_out and simfile.music.contents
        if music:
            audio = pydub.AudioSegment.from_file(io.BytesIO(music))
            transformed = audio.export(format='wav')
            self.mixer = Mixer.from_file(self.timer, transformed, self.sound_start_delta)
        elif self.clap:
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

    def schedule_events(self, notes: Sequence[NoteObjects]):
        events = []

        TURN_OFF = 0
        TURN_ON = 1
        TURN_ON_AND_BLINK = 2

        @attr.attr
        class NoteEvent(object):
            """Set `pin` to `state` at `time`"""
            pin: int = attr.NOTHING
            state: int = attr.NOTHING
            time: Time = attr.NOTHING

        hold_pins = set()
        last_row_time = 0
        for row in notes:
            row_time = row.time
            row_snap = Snap.from_row(row)

            activated_pins = set()
            deactivated_pins = set()

            if not in_reduce(all, row.objects, ('0', '3', '5')):
                deactivated_pins += set(SNAP_PINS.values()) - set(row_snap.arduino_pins)
                activated_pins += set(row_snap.arduino_pins)

            for lane, note in enumerate(row.objects):
                lane_pin = LANE_PINS[lane]
                if note in ('1', '2', '4'):
                    activated_pins.add(lane_pin)

                elif note in ('2', '4'):
                    activated_pins.add(lane_pin)
                    hold_pins.add(lane_pin)

                elif note in ('3', '5'):
                    deactivated_pins.add(lane_pin)
                    hold_pins.remove(lane_pin)

            for pin in activated_pins:
                if row_time - last_row_time < self.blink_duration:
                    events.append(
                        NoteEvent(pin,
                                  TURN_OFF,
                                  row_time - self.microblink_duration))

                events.append(
                    NoteEvent(pin,
                              TURN_ON_AND_BLINK if pin not in hold_pins else TURN_ON,
                              row_time))

            for pin in deactivated_pins:
                events.append(NoteEvent(pin, TURN_OFF, row_time))

            last_row_time = row_time

        events.sort(key=attrgetter('time'))

        state_sequence = []
        for time_point, event_group in groupby(events, attrgetter('time')):
            sequence = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
            blink_sequence = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
            for event in event_group:
                sequence[event.pin] = BYTE_TRUE if event.state in (TURN_ON, TURN_ON_AND_BLINK) else BYTE_FALSE
                blink_sequence[event.pin] = BYTE_FALSE if event.state is TURN_ON_AND_BLINK else BYTE_UNCHANGED

            if not in_reduce(all, blink_sequence, (BYTE_UNCHANGED,)):
                state_sequence.append((time_point + self.blink_duration, b''.join(blink_sequence)))
            state_sequence.append((time_point, b''.join(sequence)))

        state_sequence.sort(key=itemgetter(0))

        return state_sequence


    @QtCore.pyQtSlot()
    def pause(self):
        self.timer.pause()

    @QtCore.pyQtSlot()
    def unpause(self):
        self.timer.unpause()

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

        self.on_start.emit()

        if self.clap_mapper:
            for row in notes:
                self.mixer.add_sound(self.clap_mapper(row), row.time)

        notes = deque(
            GlobalScheduledRow.from_source(row, self.sound_start_delta)
            for row in notes
        )

        first_note = notes[0]
        sequence = self.schedule_notes(notes)

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

    @QtCore.pyqtSlot()
    def die(self):
        raise KeyboardInterrupt
