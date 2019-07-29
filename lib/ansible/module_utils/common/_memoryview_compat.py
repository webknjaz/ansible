"""Compatibility utils for using the ``memoryviews``, Python 3 style."""

from __future__ import (absolute_import, division, print_function)

from ansible.module_utils.six import moves, PY3


__metaclass__ = type

if PY3:
    # Python 3 has memoryview builtin.
    # Python 2.7 has it backported, but socket.write() does
    # str(memoryview(b'0' * 100)) -> <memory at 0x7fb6913a5588>
    # instead of accessing it correctly.
    # pylint: disable=invalid-name, redefined-builtin
    memoryview = moves.builtins.memoryview
else:
    # Link memoryview to buffer under Python 2.
    # pylint: disable=invalid-name, redefined-builtin
    memoryview = moves.builtins.buffer


def extract_bytes(mem_view):
    """Retrieve bytes out of memoryview/buffer or bytes."""
    if isinstance(mem_view, memoryview):
        return mem_view.tobytes() if PY3 else bytes(mem_view)

    if isinstance(mem_view, bytes):
        return mem_view

    raise ValueError
