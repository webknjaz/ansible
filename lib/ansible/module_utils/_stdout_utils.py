"""Utils for supplying bytes to stdout."""

import sys

from ansible.module_utils.six import PY3


__all__ = ('write_bytes_to_stdout', )


write_bytes_to_stdout = (  # pylint: disable=invalid-name
    sys.stdout.buffer.write if PY3
    else sys.stdout.write
)
