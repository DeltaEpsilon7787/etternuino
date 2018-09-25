# coding: utf-8

# In[22]:


import collections as col
import io
import operator as op
import os
import re
import time
from fractions import Fraction
from typing import List, NewType, Optional, SupportsFloat

import lark
import numpy as np
import pydub
import serial
import sounddevice as sd
import soundfile as sf
from PyQt5 import QtCore
from attr import attr, attrs
from easygui import fileopenbox, indexbox

# In[14]:


# In[23]:


# Globals
DEFAULT_SAMPLE_RATE = 44100
BYTE_FALSE = b'\x00'
BYTE_TRUE = b'\x01'
BYTE_UNCHANGED = b'\xff'

# In[24]:


# Basic types

Beat = NewType('Beat', Fraction)
Measure = NewType('Measure', Fraction)
LocalPosition = NewType('LocalPosition', Fraction)
GlobalPosition = NewType('GlobalPosition', Fraction)
Objects = NewType('Objects', str)
Time = NewType('Time', Fraction)


# In[25]:


# Slightly more advanced types

def _beat_to_measure(beat: Beat) -> Measure:
    return Measure(Fraction(beat) * Fraction(1, 4))


@attrs(cmp=False, frozen=True, slots=True)
class MeasureValuePair:
    measure: Measure = attr(converter=_beat_to_measure)
    value: Fraction = attr(converter=Fraction)

    @measure.validator
    def _(self, attr, value):
        if value < 0:
            raise ValueError

    @classmethod
    def from_string_list(cls, string_pairs: str):
        return [
            cls(*value.split('='))
            for value in string_pairs
        ]


@attrs(cmp=False, frozen=True, slots=True)
class MeasureMeasurePair(MeasureValuePair):
    value: Measure = attr(converter=_beat_to_measure)


# In[26]:


# Color

def _clamp_color(value):
    return min(max(value, 0), 255)


@attrs(frozen=True, cmp=False, slots=True)
class Color:
    r: int = attr(cmp=False, converter=_clamp_color)
    g: int = attr(cmp=False, converter=_clamp_color)
    b: int = attr(cmp=False, converter=_clamp_color)

    def __add__(self, other):
        return Color(self.r + other.r,
                     self.g + other.g,
                     self.b + other.b)


# In[27]:


# Row data types
class InvalidNoteObjectType(Exception):
    pass


@attrs(cmp=False, frozen=True, slots=True)
class PureRow:
    objects: Objects = attr(converter=Objects)

    @objects.validator
    def _(self, attr, value):
        if not all(char in '012345M' for char in value):
            raise InvalidNoteObjectType

    def __hash__(self):
        encoding_string = "012345M"
        return sum(
            encoding_string.index(character) * len(encoding_string) ** pos
            for pos, character in enumerate(self.objects)
        )

    def __str__(self):
        return hash(self)


@attrs(cmp=True, frozen=True, slots=True)
class LocalRow(PureRow):
    pos: LocalPosition = attr(converter=LocalPosition)

    @pos.validator
    def _(self, attr, value):
        if not 0 <= value < 1:
            raise ValueError

    @property
    def snap(self):
        return AntiSnaps.get(self.pos.denominator, Snaps.GRAY)


@attrs(cmp=True, frozen=True, slots=True)
class GlobalRow(LocalRow):
    pos: GlobalPosition = attr(converter=GlobalPosition)

    @pos.validator
    def _(self, attr, value):
        if value < 0:
            raise ValueError

    @property
    def measure(self):
        return int(self.pos)


@attrs(cmp=True, frozen=True, slots=True)
class GlobalTimedRow(GlobalRow):
    pos: GlobalPosition = attr(converter=GlobalPosition, cmp=False)
    time: Time = attr(cmp=True)


@attrs(cmp=True, frozen=True, slots=True)
class GlobalScheduledRow(GlobalTimedRow):
    @classmethod
    def from_source(cls, source, offset):
        return cls(source.objects, source.pos, source.time + offset)


# In[28]:


# Snap stuff

class ArduinoPins:
    L0, L1, L2, L3 = 0, 1, 2, 3
    T4, T8, T16, T12, T24, T192 = 4, 5, 6, 7, 8, 9

    @classmethod
    def get_lane(cls, lane):
        return (
                lane is 0 and cls.L0 or
                lane is 1 and cls.L1 or
                lane is 2 and cls.L2 or
                lane is 3 and cls.L3
        )


@attrs(cmp=False, slots=True)
class Snap:
    real_snap: int = attr()

    arduino_mapping = {
        1: [ArduinoPins.T4],
        2: [ArduinoPins.T4],
        3: [ArduinoPins.T12],
        4: [ArduinoPins.T4],
        8: [ArduinoPins.T8],
        12: [ArduinoPins.T12],
        16: [ArduinoPins.T16],
        24: [ArduinoPins.T24],
        32: [ArduinoPins.T4, ArduinoPins.T8],
        48: [ArduinoPins.T4, ArduinoPins.T12],
        64: [ArduinoPins.T4, ArduinoPins.T16],
        96: [ArduinoPins.T8, ArduinoPins.T12],
        128: [ArduinoPins.T8, ArduinoPins.T16],
        192: [ArduinoPins.T12, ArduinoPins.T16]
    }

    @property
    def arduino_pins(self):
        return self.arduino_mapping.get(self.snap_value, [ArduinoPins.T192])

    @property
    def color(self):
        return (
                self.snap_value is 4 and Color(255, 0, 0) or
                self.snap_value is 8 and Color(0, 0, 255) or
                self.snap_value is 12 and Color(120, 0, 255) or
                self.snap_value is 16 and Color(255, 255, 0) or
                self.snap_value is 24 and Color(255, 120, 255) or
                self.snap_value is 32 and Color(255, 120, 0) or
                self.snap_value is 48 and Color(0, 255, 255) or
                self.snap_value is 64 and Color(0, 255, 0) or
                Color(120, 120, 120)
        )

    @property
    def snap_value(self):
        return (
                self.real_snap in (1, 2, 4) and 4 or
                self.real_snap is 3 and 12 or
                self.real_snap is 8 and 8 or
                self.real_snap is 12 and 12 or
                self.real_snap is 16 and 16 or
                self.real_snap is 24 and 24 or
                self.real_snap is 32 and 32 or
                self.real_snap is 48 and 48 or
                self.real_snap is 64 and 64 or
                192
        )

    @classmethod
    def from_row(cls, row: LocalRow):
        return cls(real_snap=row.pos.denominator)


# In[29]:


@attrs(cmp=False, slots=True)
class PureChart:
    step_artist: Optional[str] = attr(default=None)
    diff_name: str = attr(default='Beginner')
    diff_value: int = attr(default=1)
    notefield: List[GlobalRow] = attr(factory=list)


@attrs(cmp=False, slots=True)
class AugmentedChart(PureChart):
    notefield: List[GlobalTimedRow] = attr(factory=list)
    bpm_segments: List[MeasureValuePair] = attr(factory=list)
    stop_segments: List[MeasureValuePair] = attr(factory=list)
    offset: Time = attr(0)

    def time(self):
        bpm_segments = col.deque(sorted(self.bpm_segments, key=op.attrgetter('measure')))
        stop_segments = col.deque(sorted(self.stop_segments, key=op.attrgetter('measure')))
        notefield = col.deque(sorted(self.notefield, key=op.attrgetter('pos')))

        # Time for serious state magic
        elapsed_time = 0
        last_measure = 0
        last_object = None
        last_bpm = bpm_segments.popleft()
        next_stop = stop_segments.popleft() if stop_segments else None

        augmented_notefield = []
        while notefield:
            last_object = notefield.popleft()
            delta_measure = last_object.pos - last_measure

            delta_time = 0
            while True:
                next_bpm = bpm_segments[0] if bpm_segments else None

                if next_bpm and next_bpm.measure < last_object.pos:
                    delta_timing = next_bpm.measure - last_measure
                    delta_time += Fraction(240, last_bpm.value) * delta_timing
                    delta_measure -= delta_timing
                    last_bpm = bpm_segments.popleft()
                    last_measure = last_bpm.measure
                else:
                    break

            delta_time += Fraction(240, last_bpm.value) * delta_measure

            while True:
                if next_stop and next_stop.measure < last_measure + delta_measure:
                    time += Fraction(240, next_stop.value)
                    next_stop = stop_segments.popleft() if stop_segments else None
                else:
                    break

            elapsed_time += delta_time
            last_measure += delta_measure

            augmented_notefield.append(GlobalTimedRow(**last_object.__dict__, time=elapsed_time - self.offset))

        self.notefield = augmented_notefield


# In[30]:


@attrs(cmp=False, slots=True)
class FileContents:
    contents: bytes = attr(repr=False)


# In[31]:


@attrs(cmp=False, slots=True)
class Simfile:
    title: str = attr(default="")
    subtitle: str = attr(default="")
    artist: str = attr(default="")
    genre: str = attr(default="")
    credit: str = attr(default="")
    music: Optional[FileContents] = attr(default=None)
    banner: Optional[FileContents] = attr(default=None)
    bg: Optional[FileContents] = attr(default=None)
    cdtitle: Optional[FileContents] = attr(default=None)
    sample_start: Time = attr(0)
    sample_length: Time = attr(10)
    display_bpm: str = '*'
    bpm_segments: List[MeasureValuePair] = attr(factory=list)
    stop_segments: List[MeasureMeasurePair] = attr(factory=list)
    offset: Time = attr(0, converter=Time)
    charts: List[AugmentedChart] = attr(factory=list)


# In[32]:


class ChartTransformer(lark.Transformer):
    file_handles = set()

    @staticmethod
    def extract_first(tree):
        return tree.children[0]

    def row(self, tokens):
        return PureRow(''.join(tokens))

    def measure(self, tokens):
        return [
            LocalRow(token.objects, Fraction(pos, len(tokens)))
            for pos, token in enumerate(tokens)
        ]

    def measures(self, tokens):
        return [
            GlobalRow(local_row.objects, global_pos + local_row.pos)
            for global_pos, measure in enumerate(tokens)
            for local_row in measure
        ]

    def notes(self, tokens):
        try:
            return PureChart(*map(self.extract_first, tokens[:3]), tokens[4])
        except IndexError:
            return PureChart('', *map(self.extract_first, tokens[:2]), tokens[3])

    def safe_file(self, tokens):
        try:
            with open(tokens[0], mode='rb') as file:
                contents = FileContents(file.read())
            return contents
        except IOError:
            return None

    def simfile(self, tokens):
        result = Simfile()

        for token in tokens:
            if not token:
                continue
            elif isinstance(token, PureChart):
                new_chart = AugmentedChart(**token.__dict__,
                                           bpm_segments=result.bpm_segments,
                                           stop_segments=result.stop_segments,
                                           offset=result.offset)
                new_chart.time()
                result.charts.append(new_chart)
            elif not token.children:
                continue
            elif token.data == 'bpms':
                result.bpm_segments += token.children[0]
            elif token.data == 'stops':
                result.stop_segments += token.children[0]
            else:
                setattr(result, token.data, token.children[0])

        return result

    row4 = row6 = row8 = row
    measure4 = measure6 = measure8 = measure
    measures4 = measures6 = measures8 = measures
    dontcare = lambda _, __: None
    false = lambda _, __: False
    true = lambda _, __: True
    no_comma_phrase = no_colon_phrase = phrase = lambda _, tokens: str(tokens[0])
    file = safe_file
    float = lambda _, tokens: Fraction(tokens[0]) or None
    int = lambda _, tokens: int(tokens[0])
    beat_value_pair = lambda _, tokens: MeasureValuePair.from_string_list(tokens)
    beat_beat_pair = lambda _, tokens: MeasureMeasurePair.from_string_list(tokens)


sm_transformer = ChartTransformer()


# In[33]:


def in_reduce(reduce_logic_func, sequence, inclusion_list) -> bool:
    """Using `reduce_logic_func` check if each element of `sequence` is in `inclusion_list`"""
    return reduce_logic_func(elmn in inclusion_list for elmn in sequence)


# In[34]:


class Mixer:
    def __init__(self, data: np.ndarray, sample_rate: int):
        self.data = data
        self.sample_rate = sample_rate
        self.current_frame = 0

    @classmethod
    def from_file(cls, source_file, sound_start=0):
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

    def add_sound(self, sound_data: np.ndarray, time: SupportsFloat):
        sample_start = int(self.sample_rate * time)
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

    def __call__(self, outdata, frames, time, status):
        sample_start = self.current_frame
        if sample_start + frames > self.data.shape[0]:
            outdata.fill(0)
        else:
            outdata[:] = self.data[sample_start:sample_start + frames]
            self.current_frame += frames


# In[65]:


def play_file(self):
    PATH = fileopenbox(msg='Choose Simfile', title='Play Simfile', default='*.sm')
    if PATH is None:
        return
    parsed_simfile = parse_simfile(PATH)

    selection = 0

    if len(parsed_simfile.charts) > 1:
        selection = indexbox(
            msg='Which chart to play?', title='Chart selection',
            choices=[
                f'{i+1}: {parsed_simfile.charts[i].diff_name}'
                for i in range(len(parsed_simfile.charts))
            ]
        )

        if selection is None:
            return

    self.die_chart_to_signals = False
    active_thread = threading.Thread(
        target=chart_to_signals,
        kwargs={
            'simfile': parsed_simfile,
            'chart_num': selection,
            'app_ref': self,
            'arduino': serial.Serial('/dev/ttyUSB0') if self.signal_arduino.get() else None,
            'music_out': self.play_music.get()
        }
    )
    active_thread.start()


# In[39]:


class BaseClapMapper(col.Callable):
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
        QtCore.QThread.__init__(self, parent)

        self.simfile = simfile
        self.chart_num = chart_num
        self.sound_start_delta = sound_start_delta
        self.arduino = arduino
        self.music_out = music_out
        self.clap_mapper = clap_mapper

        self.mixer = None
        self.music_stream = None

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
            self.time_function = lambda: mixer.current_frame / mixer.sample_rate

        self.microblink_duration = 0
        self.blink_duration = 0

        self.time_function = time.perf_counter
        self.is_active = False

        self.blink_schedule = [0] * 10

    @staticmethod
    def wait_till(end_time: SupportsFloat) -> None:
        while self.time_function() < end_time:
            pass

    @QtCore.pyqtSlot()
    def run(self):
        try:
            chart = simfile.charts[chart_num]
        except IndexError:
            return

        notes = sorted(chart.notefield)
        notes = col.deque(
            row
            for row in notes
            if not in_reduce(all, row.objects, ('0', 'M'))
        )

        self.microblink_duration = Fraction('0.01') if self.arduino else 0
        self.blink_duration = Fraction('0.06') if self.arduino else 0

        self.activate_signal.emit()
        self.is_active = True

        if self.clap_mapper:
            for row in notes:
                mixer.add_sound(clap_mapper(row), row.time)

        self.music_stream and self.music_stream.start()
        start = self.time_function() - self.sound_start_delta

        notes = col.deque(
            GlobalScheduledRow.from_source(row, start)
            for row in notes
        )

        first_note = notes[0]
        partial_wait_till(first_note.time)

        while notes:
            if not self.is_active:
                self.die()
                return

            current_row = notes.popleft()
            current_snap = Snap.from_row(current_row)
            next_row = notes[0] if notes else current_row

            if arduino:
                blink_message = [BYTE_UNCHANGED] * 10
                new_message = [BYTE_UNCHANGED] * 10

                if not in_reduce(all, current_row.objects, ('0', '3', '5')):
                    new_message[4:] = [BYTE_FALSE] * 6
                    for pin in current_snap.arduino_pins:
                        new_message[pin] = T

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

                arduino and not in_reduce(all, blink_message, (BYTE_UNCHANGED,)) and arduino.write(
                    b''.join(blink_message))
                partial_wait_till(current_row.time)
                arduino and arduino.write(b''.join(new_message))

            next_row_time = next_row.time - MICROBLINK_DURATION
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

            partial_wait_till(next_state)

            if next_state is next_row_time:
                continue

            if arduino or app_ref:
                off_message = [BYTE_UNCHANGED] * 10
                for pin, timing in enumerate(off_schedule):
                    if not timing:
                        continue
                    if time_function() >= timing:
                        off_message[pin] = BYTE_FALSE
                        off_schedule[pin] = 0
                    arduino and arduino.write(b''.join(off_message))
            partial_wait_till(next_row_time)

    @QtCore.pyqtSlot()
    def die(self):
        self.music_stream and music_stream.stop()
        self.arduino and arduino.write(BYTE_FALSE * 10)


# In[40]:


def parse_simfile(file_path):
    this_dir = os.getcwd()

    with open(file_path, encoding='utf-8', errors='ignore') as chart:
        lines = chart.readlines()

    chart = []
    for line in lines:
        chart.append(re.sub(r'(\/\/.*$)', '', line))

    chart = ''.join(chart)
    try:
        sm_parser = lark.Lark.open('sm_grammar.lark', parser='lalr', transformer=sm_transformer, start='simfile')
        os.chdir(os.path.dirname(file_path))
        parsed_chart = sm_parser.parse(chart)
        os.chdir(this_dir)
    except:
        raise
    finally:
        os.chdir(this_dir)

    return parsed_chart


# In[36]:


PATH = fileopenbox(msg='Choose Simfile', title='Play Simfile', default='*.sm')
parsed_simfile = parse_simfile(PATH)
chart_to_signals(parsed_simfile,
                 chart_num=0,
                 arduino=serial.Serial('/dev/ttyUSB0'),
                 music_out=True)
