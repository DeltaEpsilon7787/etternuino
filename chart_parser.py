import operator as op
import os
import re
from collections import __init__ as col
from fractions import Fraction
from typing import Optional, List

import lark
from attr.__init__ import attrs, attr

from basic_types import Time
from complex_types import MeasureValuePair, MeasureMeasurePair
from rows import GlobalRow, GlobalTimedRow, PureRow, LocalRow


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
                    delta_time += Fraction(240, next_stop.value)
                    next_stop = stop_segments.popleft() if stop_segments else None
                else:
                    break

            elapsed_time += delta_time
            last_measure += delta_measure

            augmented_notefield.append(GlobalTimedRow(**last_object.__dict__, time=elapsed_time - self.offset))

        self.notefield = augmented_notefield


@attrs(cmp=False, slots=True)
class FileContents:
    contents: bytes = attr(repr=False)


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


class ChartTransformer(lark.Transformer):
    file_handles = set()

    @staticmethod
    def extract_first(tree):
        return tree.children[0]

    @staticmethod
    def row(tokens):
        return PureRow(''.join(tokens))

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

    def notes(self, tokens):
        try:
            return PureChart(*map(self.extract_first, tokens[:3]), tokens[4])
        except IndexError:
            return PureChart('', *map(self.extract_first, tokens[:2]), tokens[3])

    @staticmethod
    def safe_file(tokens):
        try:
            with open(tokens[0], mode='rb') as file:
                contents = FileContents(file.read())
            return contents
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


def parse_simfile(file_path):
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

    return parsed_chart
