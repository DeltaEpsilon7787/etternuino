DEFAULT_SAMPLE_RATE = 44100
BYTE_FALSE = b'\x00'
BYTE_TRUE = b'\x01'
BYTE_UNCHANGED = b'\xff'


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


def in_reduce(reduce_logic_func, sequence, inclusion_list) -> bool:
    """Using `reduce_logic_func` check if each element of `sequence` is in `inclusion_list`"""
    return reduce_logic_func(elmn in inclusion_list for elmn in sequence)
