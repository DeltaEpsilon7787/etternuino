from functools import lru_cache

from attr.__init__ import attrs, attr

from basic_types import Objects, LocalPosition, GlobalPosition, Time
from complex_types import Color
from definitions import ArduinoPins


class InvalidNoteObjectType(Exception):
    pass


@attrs(cmp=False, frozen=True, slots=True)
class PureRow:
    objects: Objects = attr(converter=Objects)

    @objects.validator
    def _(self, attr_name, value):
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
    def _(self, attr_name, value):
        if not 0 <= value < 1:
            raise ValueError

    @property
    @lru_cache
    def snap(self):
        return Snap.from_row(self).snap_value


@attrs(cmp=True, frozen=True, slots=True)
class GlobalRow(LocalRow):
    pos: GlobalPosition = attr(converter=GlobalPosition)

    @pos.validator
    def _(self, attr_name, value):
        if value < 0:
            raise ValueError

    @property
    @lru_cache
    def measure(self):
        # noinspection PyTypeChecker
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
