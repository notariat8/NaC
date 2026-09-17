from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_runtime.platform_file_lock import lock_exclusive, unlock


class PlatformFileLockTests(unittest.TestCase):
    def test_exclusive_nonblocking_lock_rejects_competing_handle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock"
            path.write_bytes(b"\0")
            first = os.open(path, os.O_RDWR)
            second = os.open(path, os.O_RDWR)
            try:
                lock_exclusive(first, nonblocking=True)
                with self.assertRaises(BlockingIOError):
                    lock_exclusive(second, nonblocking=True)
                unlock(first)
                lock_exclusive(second, nonblocking=True)
                unlock(second)
            finally:
                os.close(second)
                os.close(first)


if __name__ == "__main__":
    unittest.main()
