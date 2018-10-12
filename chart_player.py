import io
from fractions import Fraction
from operator import itemgetter
from typing import Optional, Sequence

import pydub
import serial
import sounddevice as sd
from PyQt5 import QtCore
from attr import attrib, attrs

from clap_mapper import BaseClapMapper
from definitions import BYTE_FALSE, BYTE_TRUE, DEFAULT_SAMPLE_RATE, LANE_PINS, \
    capture_exceptions, in_reduce, make_blank_message
from mixer import Mixer
from simfile_parsing.basic_types import Time
from simfile_parsing.rows import GlobalScheduledRow, Snap
from simfile_parsing.simfile_parser import AugmentedChart


@attrs
class NoteEvent:
    time: Time = attrib()
    arduino_message: bytes = attrib()
    row: GlobalScheduledRow = attrib()
    state: bool = attrib()


class EventScheduler:
    def __init__(self):
        self.microblink_duration = Fraction('0.01')
        self.blink_duration = Fraction('0.12')

    def schedule_events(self, notes: Sequence[GlobalScheduledRow]):
        snap_sequence = self.obtain_snap_changes(notes)
        lane_changes = self.obtain_lane_changes(notes)
        ordered_events = self.compose_events(lane_changes, snap_sequence)
        result = self.merge_events_into_messages(ordered_events)

        return result

    @staticmethod
    def obtain_snap_changes(notes):
        snap_sequence = []
        for note in notes:
            if in_reduce(all, note.objects, ('0', '3', '5', 'M')):
                continue
            snap_sequence.append((note.time,
                                  Snap.from_row(note),
                                  note))
        return snap_sequence

    def obtain_lane_changes(self, notes):
        lane_changes = [[] for _ in range(len(LANE_PINS))]
        for lane in range(len(LANE_PINS)):
            active_list = lane_changes[lane]

            for note in notes:
                if note.objects[lane] in ('0', 'M'):
                    continue
                if note.objects[lane] in ('1',):
                    if active_list and active_list[-1] > note.time:
                        active_list[-1] = note.time - self.microblink_duration
                    active_list.append(note.time)
                    active_list.append(note.time + self.blink_duration)
                if note.objects[lane] in ('2', '3', '4', '5'):
                    if active_list and active_list[-1] > note.time:
                        active_list[-1] = note.time - self.microblink_duration
                    active_list.append(note.time)
        return lane_changes

    @staticmethod
    def compose_events(lane_changes, snap_sequence):
        ordered_events = []
        for lane in range(len(LANE_PINS)):
            active_list = lane_changes[lane]

            snap_index = 0
            for status, time in enumerate(active_list, start=1):
                status %= 2
                if status:
                    while time > snap_sequence[snap_index][0]:
                        if snap_index < len(snap_sequence):
                            snap_index += 1
                        else:
                            break
                    while time < snap_sequence[snap_index][0]:
                        if snap_index:
                            snap_index -= 1
                        else:
                            break
                ordered_events.append((time, snap_sequence[snap_index], lane, status))
        ordered_events.sort(key=itemgetter(0))

        return ordered_events

    @staticmethod
    def merge_events_into_messages(ordered_events):
        result = []
        blank_message = make_blank_message()
        for time, snap, lane, status in ordered_events:
            message = blank_message.copy()
            message[LANE_PINS[lane]] = status and BYTE_TRUE or BYTE_FALSE
            for pin in snap[1].arduino_pins:
                message[pin] = BYTE_TRUE
            result.append(NoteEvent(time, b''.join(message), snap[2], bool(status)))
        return result


class ChartPlayer(QtCore.QObject, EventScheduler):
    on_start = QtCore.pyqtSignal()
    on_end = QtCore.pyqtSignal()
    on_write = QtCore.pyqtSignal(object)
    time_tick = QtCore.pyqtSignal(object)
    play_signal = QtCore.pyqtSignal()

    @capture_exceptions
    def __init__(self,
                 chart: AugmentedChart,
                 audio: io.BufferedReader,
                 sound_start_delta: Time = 0,
                 arduino: Optional[serial.Serial] = None,
                 clap_mapper: Optional[BaseClapMapper] = None):
        super().__init__()

        self.chart = chart
        self.audio = audio
        self.sound_start_delta = sound_start_delta
        self.arduino = arduino
        self.arduino_muted = False
        self.clap_mapper = clap_mapper

        self.mixer = None
        self.music_stream = None

        self.need_to_die = False
        self.need_to_update_position = False

    @QtCore.pyqtSlot()
    def pause(self):
        self.mixer.paused = True

    @QtCore.pyqtSlot()
    def unpause(self):
        self.mixer.paused = False

    @QtCore.pyqtSlot()
    def mute_arduino(self):
        self.arduino_muted = True

    @QtCore.pyqtSlot()
    def unmute_arduino(self):
        self.arduino_muted = False

    @QtCore.pyqtSlot()
    def mute_music(self):
        self.mixer.muted = True

    @QtCore.pyqtSlot()
    def unmute_music(self):
        self.mixer.muted = False

    @QtCore.pyqtSlot()
    def die(self):
        self.need_to_die = True

    def wait_till(self, end_time: Time) -> None:
        while self.mixer.current_time < end_time:
            self.time_tick.emit(self.mixer.current_time)
            if self.need_to_update_position or self.need_to_die:
                break
            sd.sleep(1)

    def load_audio(self):
        pydub.AudioSegment.from_file(self.audio).export('temp.wav', format='wav')
        self.mixer = Mixer.from_file('temp.wav', self.sound_start_delta)
        self.music_stream = sd.OutputStream(channels=2,
                                            samplerate=DEFAULT_SAMPLE_RATE,
                                            dtype='float32',
                                            callback=self.mixer)

    def chart_to_timed_rows(self, chart):
        notes = sorted(chart.note_field)
        notes = (
            row
            for row in notes
            if not in_reduce(all, row.objects, ('0', 'M'))
        )
        notes = [
            GlobalScheduledRow.from_source(row, self.sound_start_delta)
            for row in notes
        ]

        return notes

    @QtCore.pyqtSlot()
    @capture_exceptions
    def play(self):
        notes = self.chart_to_timed_rows(self.chart)
        sequence = self.schedule_events(notes)

        self.load_audio()
        self.inject_claps(notes)

        try:
            first_note = notes[0]
        except IndexError:
            return

        self.on_start.emit()
        self.music_stream and self.music_stream.start()
        self.unpause()
        self.wait_till(first_note.time)

        current_index = 0
        while current_index < len(sequence):
            event = sequence[current_index]
            self.wait_till(event.time)
            self.on_write.emit(event)
            self.arduino and not self.arduino_muted and self.arduino.write(event.arduino_message)
            if self.need_to_die:
                return
            if self.need_to_update_position:
                current_index = [
                    index
                    for index, event in enumerate(sequence)
                    if event.time >= self.mixer.current_time
                ][0]
                self.need_to_update_position = False
            current_index += 1

    def inject_claps(self, notes):
        if self.clap_mapper:
            for row in notes:
                self.mixer.add_sound(self.clap_mapper(row), row.time)

    def cleanup(self):
        self.music_stream and self.music_stream.stop()
        self.on_end.emit()
        # self.disconnect()
