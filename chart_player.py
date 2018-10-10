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
from definitions import ARDUINO_MESSAGE_LENGTH, BYTE_FALSE, BYTE_TRUE, BYTE_UNCHANGED, DEFAULT_SAMPLE_RATE, LANE_PINS, \
    SNAP_PINS, capture_exceptions, in_reduce
from mixer import Mixer
from simfile_parsing.basic_types import Time
from simfile_parsing.rows import GlobalScheduledRow, Snap
from simfile_parsing.simfile_parser import AugmentedChart


@attrs
class NoteEvent:
    time: Time = attrib()
    arduino_message: bytes = attrib()
    row: GlobalScheduledRow = attrib()


class ChartPlayer(QtCore.QObject):
    on_start: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_end: QtCore.pyqtSignal = QtCore.pyqtSignal()
    on_write: QtCore.pyqtSignal = QtCore.pyqtSignal(object)

    def __init__(self,
                 chart: AugmentedChart,
                 audio: io.BufferedReader,
                 sound_start_delta: Time = 0,
                 arduino: Optional[serial.Serial] = None,
                 music_out: bool = True,
                 clap_mapper: Optional[BaseClapMapper] = None):
        super().__init__(self)

        self.chart = chart
        self.audio = audio
        self.sound_start_delta = sound_start_delta
        self.arduino = arduino
        self.arduino_muted = False
        self.clap_mapper = clap_mapper

        self.microblink_duration = Fraction('0.01')
        self.blink_duration = Fraction('0.06')

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
            if self.progress_slider_output:
                self.progress_slider_output.setValue(self.mixer.current_frame)
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

    def filter_chart_notes(self, chart):
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

    def schedule_events(self, notes: Sequence[GlobalScheduledRow]):
        snap_sequence = []
        for note in notes:
            if in_reduce(all, note.objects, ('0', '3', '5', 'M')):
                continue
            snap_sequence.append((note.time,
                                  Snap.from_row(note),
                                  note))

        # And then lanes
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
                    active_list.append(note.time)

        # Compose ON-OFF-ON-OFF sequences
        ordered_events = []
        for lane in range(len(LANE_PINS)):
            active_list = lane_changes[lane]

            snap_index = 0
            for status, time in enumerate(active_list, start=1):
                status %= 2
                if status:
                    while snap_sequence[snap_index][0] < time:
                        snap_index += 1
                    snap_index -= 1
                ordered_events.append((note.time, snap_sequence[snap_index], lane, status))

        ordered_events.sort(key=itemgetter(0))

        blank_message = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
        for snap in SNAP_PINS:
            for pin in SNAP_PINS[snap]:
                blank_message[pin] = BYTE_FALSE

        result = []
        for time, snap, lane, status in ordered_events:
            message = blank_message.copy()
            message[LANE_PINS[lane]] = status and BYTE_TRUE or BYTE_FALSE
            for pin in snap[1].arduino_pins:
                message[pin] = BYTE_TRUE
            result.append(NoteEvent(time, b''.join(message), snap[2]))

        return result

    @QtCore.pyqtSlot()
    @capture_exceptions
    def play(self):
        self.load_audio()

        notes = self.filter_chart_notes(self.chart)

        if self.clap_mapper:
            for row in notes:
                self.mixer.add_sound(self.clap_mapper(row), row.time)

        first_note = notes[0]
        sequence = self.schedule_events(notes)

        self.on_start.emit()

        self.music_stream and self.music_stream.start()
        self.unpause()
        self.wait_till(first_note.time)

        current_index = 0
        while current_index < len(sequence):
            event = sequence[current_index]
            self.wait_till(event.time)
            self.on_write.emit(event.row)
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

    def cleanup(self):
        self.music_stream and self.music_stream.stop()
        self.on_end.emit()
        self.disconnect()
