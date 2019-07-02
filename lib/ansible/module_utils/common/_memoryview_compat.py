"""Compatibility utils for using the ``memoryviews``, Python 3 style."""

from ansible.module_utils.six import PY3


if PY3:
    """Python 3 has memoryview builtin."""
    # Python 2.7 has it backported, but socket.write() does
    # str(memoryview(b'0' * 100)) -> <memory at 0x7fb6913a5588>
    # instead of accessing it correctly.
    memoryview = memoryview
else:
    """Link memoryview to buffer under Python 2."""
    memoryview = buffer  # noqa: F821


def extract_bytes(mv):
    """Retrieve bytes out of memoryview/buffer or bytes."""
    if isinstance(mv, memoryview):
        return mv.tobytes() if PY3 else bytes(mv)

    if isinstance(mv, bytes):
        return mv

    raise ValueError
