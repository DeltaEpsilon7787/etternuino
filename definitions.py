import functools

DEFAULT_SAMPLE_RATE = 44100
BYTE_FALSE = b'\x00'
BYTE_TRUE = b'\x01'
BYTE_UNCHANGED = b'\xff'

ARDUINO_MESSAGE_LENGTH = 12

LANE_PINS = {
    0: 11,
    1: 10,
    2: 9,
    3: 8
}

SNAP_PINS = {
    4: 7,
    8: 3,
    16: 5,
    12: 6,
    24: 4,
    192: 2
}


def in_reduce(reduce_logic_func, sequence, inclusion_list) -> bool:
    """Using `reduce_logic_func` check if each element of `sequence` is in `inclusion_list`"""
    return reduce_logic_func(elmn in inclusion_list for elmn in sequence)


def capture_exceptions(function):
    @functools.wraps(function)
    def decorator(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as E:
            print(f'Exception occured in {function.__name__}: {E}')
            return

    return decorator
