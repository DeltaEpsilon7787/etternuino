import collections
import functools

from PyQt5 import QtCore

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


def capture_exceptions(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as E:
            print(f'Exception occured in {func.__name__}: {E}')
            return

    return decorator


def make_blank_message():
    blank_message = [BYTE_UNCHANGED] * ARDUINO_MESSAGE_LENGTH
    for pin in SNAP_PINS.values():
        blank_message[pin] = BYTE_FALSE
    return blank_message


def run_in_thread(target: QtCore.QObject,
                  thread_container,
                  start_signal,
                  connections: collections.OrderedDict):
    target_thread = QtCore.QThread()
    thread_container.append(target_thread)
    target.moveToThread(target_thread)

    for target_signal, target_slots in connections.items():
        try:
            for target_slot in target_slots:
                getattr(target, target_signal).connect(target_slot)
        except AttributeError:
            getattr(target, target_signal).connect(target_slots)

    start_signal()
    return target_thread
