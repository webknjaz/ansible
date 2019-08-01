"""Utils for supplying bytes to stdout."""

import sys

from ansible.module_utils.six import PY3


__all__ = ('write_bytes_to_stdout', )


def write_bytes_to_stdout(*args, **kwargs):
    """Write bytes to stdout and flush immediately."""
    _write_stdout_stream = (
        sys.stdout.buffer if PY3
        else sys.stdout
    ).write
    _write_stdout_stream(*args, **kwargs)
    sys.stdout.flush()
