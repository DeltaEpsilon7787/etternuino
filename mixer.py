from fractions import Fraction

import numpy as np
import soundfile as sf
from PyQt5 import QtCore

from definitions import DEFAULT_SAMPLE_RATE
from simfile_parsing.basic_types import Time


class Mixer(QtCore.QObject):
    def __init__(self, data=np.zeros((60 * DEFAULT_SAMPLE_RATE, 2)), sample_rate=DEFAULT_SAMPLE_RATE):
        super().__init__()

        self.data = data.copy()
        self.sample_rate = sample_rate
        self.current_frame = 0
        self.muted = False
        self.paused = False

    @classmethod
    def from_file(cls, source_file: str, sound_start: Time = 0):
        data, sample_rate = sf.read(source_file, dtype='float32')
        mixer = cls(data, sample_rate)

        if sound_start < 0:
            padded = np.zeros((mixer.sample_rate * abs(sound_start), mixer.data.shape[1]))
            mixer.data = np.concatenate((padded, mixer.data))
        else:
            mixer.data = mixer.data[int(mixer.sample_rate * sound_start):]

        return mixer

    def add_sound(self, sound_data: np.ndarray, at_time: Time):
        sample_start = int(self.sample_rate * at_time)
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

    def __call__(self, out_data: np.ndarray, frames: int, at_time, status: int):
        sample_start = self.current_frame

        if sample_start + frames > self.data.shape[0] or self.paused:
            out_data.fill(0)
        else:
            if self.muted:
                out_data.fill(0)
            else:
                out_data[:] = self.data[sample_start:sample_start + frames]
            self.current_frame += frames

    @property
    def current_time(self) -> Time:
        return Time(Fraction(self.current_frame, self.sample_rate))
