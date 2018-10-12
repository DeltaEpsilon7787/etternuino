import io
import operator as op
import os
import re
from collections import deque
from fractions import Fraction
from typing import List, Optional

import lark
from PyQt5 import QtCore
from attr import Factory, attrib, attrs

from definitions import capture_exceptions
from simfile_parsing.basic_types import NoteObjects, Time
from simfile_parsing.complex_types import MeasureMeasurePair, MeasureValuePair
from simfile_parsing.rows import GlobalRow, GlobalTimedRow, LocalRow, PureRow


@attrs(cmp=False, auto_attribs=True)
class PureChart(object):
    step_artist: Optional[str] = None
    diff_name: str = 'Beginner'
    diff_value: int = 1
    note_field: List[GlobalRow] = Factory(list)


@attrs(cmp=False, auto_attribs=True)
class AugmentedChart(object):
    step_artist: Optional[str] = None
    diff_name: str = 'Beginner'
    diff_value: int = 1
    note_field: List[GlobalTimedRow] = Factory(list)
    bpm_segments: List[MeasureValuePair] = Factory(list)
    stop_segments: List[MeasureMeasurePair] = Factory(list)
    offset: Time = 0

    def time(self):
        bpm_segments = deque(sorted(self.bpm_segments, key=op.attrgetter('measure')))
        stop_segments = deque(sorted(self.stop_segments, key=op.attrgetter('measure')))
        notefield = deque(sorted(self.note_field, key=op.attrgetter('pos')))

        # Time for serious state magic
        elapsed_time = 0
        last_measure = 0
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
                    delta_time += Fraction(240, next_stop.value)
                    next_stop = stop_segments.popleft() if stop_segments else None
                else:
                    break

            elapsed_time += delta_time
            last_measure += delta_measure

            augmented_notefield.append(GlobalTimedRow(**last_object.__dict__, time=elapsed_time - self.offset))

        self.note_field = augmented_notefield


@attrs(cmp=False)
class Simfile(object):
    title: str = attrib(default="")
    subtitle: str = attrib(default="")
    artist: str = attrib(default="")
    genre: str = attrib(default="")
    credit: str = attrib(default="")
    music: Optional[io.BufferedReader] = attrib(default=None)
    banner: Optional[io.BufferedReader] = attrib(default=None)
    bg: Optional[io.BufferedReader] = attrib(default=None)
    cdtitle: Optional[io.BufferedReader] = attrib(default=None)
    sample_start: Time = attrib(default=0)
    sample_length: Time = attrib(default=10)
    display_bpm: str = '*'
    bpm_segments: List[MeasureValuePair] = attrib(factory=list)
    stop_segments: List[MeasureMeasurePair] = attrib(factory=list)
    offset: Time = attrib(default=0, converter=Time)
    charts: List[AugmentedChart] = attrib(factory=list)


class ChartTransformer(lark.Transformer):
    file_handles = set()

    @staticmethod
    def extract_first(tree):
        return tree.children[0]

    @staticmethod
    def row(tokens):
        return PureRow(NoteObjects(''.join(tokens)))

    @staticmethod
    def measure(tokens):
        return [
            LocalRow(token.objects, Fraction(pos, len(tokens)))
            for pos, token in enumerate(tokens)
        ]

    @staticmethod
    def measures(tokens):
        return [
            GlobalRow(local_row.objects, global_pos + local_row.pos)
            for global_pos, measure in enumerate(tokens)
            for local_row in measure
        ]

    @staticmethod
    def notes(tokens):
        try:
            return PureChart(*map(ChartTransformer.extract_first, tokens[:3]), tokens[4])
        except IndexError:
            return PureChart('', *map(ChartTransformer.extract_first, tokens[:2]), tokens[3])

    @staticmethod
    def unsafe_file(tokens):
        return open(tokens[0], mode='rb')

    @staticmethod
    def safe_file(tokens):
        try:
            return open(tokens[0], mode='rb')
        except IOError:
            return None

    @staticmethod
    def simfile(tokens):
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

    @staticmethod
    def dontcare(__):
        return None

    @staticmethod
    def false(__):
        return False

    @staticmethod
    def true(__):
        return True

    @staticmethod
    def phrase(tokens):
        return str(tokens[0])

    @staticmethod
    def float(tokens):
        return Fraction(tokens[0])

    @staticmethod
    def int(tokens):
        return int(tokens[0])

    @staticmethod
    def beat_value_pair(tokens):
        return MeasureValuePair.from_string_list(tokens)

    @staticmethod
    def beat_beat_pair(tokens):
        return MeasureMeasurePair.from_string_list(tokens)

    row4 = row6 = row8 = row
    measure4 = measure6 = measure8 = measure
    measures4 = measures6 = measures8 = measures
    no_comma_phrase = no_colon_phrase = phrase
    file = safe_file


class SimfileParser(QtCore.QObject):
    parse_simfile = QtCore.pyqtSignal(str)
    simfile_parsed = QtCore.pyqtSignal(object)

    @QtCore.pyqtSlot(str)
    @capture_exceptions
    def perform_parsing(self, file_path):
        sm_transformer = ChartTransformer()

        this_dir = os.getcwd()

        with open(file_path, encoding='utf-8', errors='ignore') as chart:
            lines = chart.readlines()

        chart = []
        for line in lines:
            chart.append(re.sub(r'(//.*$)', '', line))

        chart = ''.join(chart)
        try:
            sm_parser = lark.Lark.open('sm_grammar.lark', parser='lalr', transformer=sm_transformer, start='simfile')
            os.chdir(os.path.dirname(file_path))
            parsed_chart = sm_parser.parse(chart)
        except Exception:
            raise
        finally:
            os.chdir(this_dir)

        self.simfile_parsed.emit(parsed_chart)
