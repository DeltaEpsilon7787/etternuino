from fractions import Fraction

from attr.__init__ import attrs, attr

from basic_types import Beat, Measure


def _beat_to_measure(beat: Beat) -> Measure:
    return Measure(Fraction(beat) * Fraction(1, 4))


@attrs(cmp=False, frozen=True, slots=True)
class MeasureValuePair:
    measure: Measure = attr(converter=_beat_to_measure)
    value: Fraction = attr(converter=Fraction)

    @measure.validator
    def _(self, attr_name, value):
        if value < 0:
            raise ValueError

    @classmethod
    def from_string_list(cls, string_pairs: str):
        return [
            cls(*value.split('=')[:2])
            for value in string_pairs
        ]


@attrs(cmp=False, frozen=True, slots=True)
class MeasureMeasurePair(MeasureValuePair):
    value: Measure = attr(converter=_beat_to_measure)


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
