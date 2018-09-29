from fractions import Fraction
from typing import NewType

Beat = NewType('Beat', Fraction)
Measure = NewType('Measure', Fraction)
LocalPosition = NewType('LocalPosition', Fraction)
GlobalPosition = NewType('GlobalPosition', Fraction)
NoteObjects = NewType('NoteObjects', str)
Time = NewType('Time', Fraction)
