from fractions import Fraction

from attr import attrib, attrs

from basic_types import Beat, Measure


def _beat_to_measure(beat: Beat) -> Measure:
    return Measure(Fraction(beat) * Fraction(1, 4))


@attrs(cmp=False)
class MeasureValuePair(object):
    measure: Measure = attrib(converter=_beat_to_measure)
    value: Fraction = attrib(converter=Fraction)

    @classmethod
    def from_string_list(cls, string_pairs: str):
        return [
            cls(*value.split('=')[:2])
            for value in string_pairs
        ]


@attrs(cmp=False)
class MeasureMeasurePair(object):
    measure: Measure = attrib(converter=_beat_to_measure)
    value: Measure = attrib(converter=_beat_to_measure)
    from_string_list = MeasureValuePair.from_string_list


def _clamp_color(value):
    return min(max(value, 0), 255)


@attrs(cmp=False)
class Color(object):
    r: int = attrib(converter=_clamp_color)
    g: int = attrib(converter=_clamp_color)
    b: int = attrib(converter=_clamp_color)

    def __add__(self, other):
        return Color(
            self.r + other.r,
            self.g + other.g,
            self.b + other.b
        )
