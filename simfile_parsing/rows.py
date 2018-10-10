from functools import lru_cache

from attr import attrib, attrs

from definitions import SNAP_PINS
from simfile_parsing.basic_types import GlobalPosition, LocalPosition, NoteObjects, Time
from simfile_parsing.complex_types import Color


@attrs(cmp=False)
class PureRow(object):
    objects: NoteObjects = attrib()


@attrs(cmp=True)
class LocalRow(PureRow):
    objects: NoteObjects = attrib(cmp=False)
    pos: LocalPosition = attrib(cmp=True)

    @property
    @lru_cache(None)
    def snap(self):
        return Snap.from_row(self).snap_value


@attrs(cmp=True)
class GlobalRow(LocalRow):
    objects: NoteObjects = attrib(cmp=False)
    pos: GlobalPosition = attrib(cmp=True)

    @property
    @lru_cache(None)
    def measure(self):
        return int(self.pos.real)


@attrs(cmp=True)
class GlobalTimedRow(GlobalRow):
    objects: NoteObjects = attrib(cmp=False)
    pos: GlobalPosition = attrib(cmp=False)
    time: Time = attrib(cmp=True)


@attrs(cmp=True)
class GlobalScheduledRow(GlobalTimedRow):
    objects: NoteObjects = attrib(cmp=False)
    pos: GlobalPosition = attrib(cmp=False)
    time: Time = attrib(cmp=True)

    @classmethod
    def from_source(cls, source, offset):
        return cls(source.objects, source.pos, source.time + offset)


@attrs(cmp=False)
class Snap(object):
    real_snap: int = attrib()

    arduino_mapping = {
        1: [SNAP_PINS[4]],
        2: [SNAP_PINS[4]],
        3: [SNAP_PINS[12]],
        4: [SNAP_PINS[4]],
        8: [SNAP_PINS[8]],
        12: [SNAP_PINS[12]],
        16: [SNAP_PINS[16]],
        24: [SNAP_PINS[24]],
        32: [SNAP_PINS[4], SNAP_PINS[8]],
        48: [SNAP_PINS[4], SNAP_PINS[12]],
        64: [SNAP_PINS[4], SNAP_PINS[16]],
        96: [SNAP_PINS[8], SNAP_PINS[12]],
        128: [SNAP_PINS[8], SNAP_PINS[16]],
        192: [SNAP_PINS[12], SNAP_PINS[16]]
    }

    @property
    def arduino_pins(self):
        return self.arduino_mapping.get(self.snap_value, [SNAP_PINS[192]])

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
