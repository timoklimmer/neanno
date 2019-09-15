"""Defines helper functions for working with signals emitted during a ParallelWorker job."""

import time


def emit_top_header(text, signals):
    """ Emits a top header."""
    signals.message.emit(text, "\n")
    signals.message.emit(("=") * len(text), "\n")
    signals.message.emit("", "\n")


def emit_sub_header(text, signals):
    """ Emits a sub header."""
    signals.message.emit(text, "\n")
    signals.message.emit("-" * len(text), "\n")


def emit_message(message, signals):
    """Emits a simple message."""
    signals.message.emit(message, "\n")


def emit_image(image_bytes, image_format, signals):
    """Emits the passed image."""
    signals.image.emit(image_bytes, image_format)

def emit_partial_message(message, signals):
    """Emits the given message but does not advance to the next line."""
    signals.message.emit(message, "")


def emit_new_line(signals):
    """Emits a new line to improve readability."""
    signals.message.emit("\n", "")


def emit_start_time(signals):
    """Emits the start time and returns it for later when the duration needs to be calculated."""
    start_time = time.time()
    signals.message.emit(
        "Start time: {}".format(time.strftime("%X", time.localtime(start_time))), "\n"
    )
    return start_time


def emit_end_time_duration(start_time, activity_name, signals):
    """Emits the end time and duration of something that has started before."""
    end_time = time.time()
    signals.message.emit(
        "End time: {}".format(time.strftime("%X", time.localtime(end_time))), "\n"
    )
    signals.message.emit(
        "{} took (hh:mm:ss): {}.".format(
            activity_name, time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))
        ),
        "\n",
    )
