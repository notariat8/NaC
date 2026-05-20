from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) in sys.path:
    sys.path.remove(str(SRC_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from nac_web.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
