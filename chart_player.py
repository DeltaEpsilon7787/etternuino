from collections.__init__ import deque
from fractions import Fraction
from itertools import groupby
from operator import attrgetter, itemgetter
from typing import Optional, Sequence, List, Set, Tuple

import pydub
import serial
import sounddevice as sd
from PyQt5 import QtCore
from attr import attrs, attrib

from basic_types import Time
from chart_parser import Simfile
from definitions import DEFAULT_SAMPLE_RATE, capture_exceptions, in_reduce, SNAP_PINS, LANE_PINS, BYTE_UNCHANGED, \
    ARDUINO_MESSAGE_LENGTH, BYTE_TRUE, BYTE_FALSE
from etternuino import BaseClapMapper
from mixer import Mixer
from rows import GlobalScheduledRow, Snap


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
                 arduino: Optional[serial.Serial] = None,
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

        @attrs
        class NoteEvent(object):
            """Set `pin` to `state` at `time`"""
            pin: int = attrib()
            state: int = attrib()
            time: Time = attrib()

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
