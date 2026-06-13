from pathlib import Path
import sys


FUNCTION_DIR = Path(__file__).resolve().parent
SOURCE_CANDIDATES = [
    FUNCTION_DIR / "src",
    Path("/function/src"),
]
if len(FUNCTION_DIR.parents) > 2:
    SOURCE_CANDIDATES.insert(1, FUNCTION_DIR.parents[2] / "src")

for candidate in SOURCE_CANDIDATES:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from nac_web.oci_public_functions import handler  # noqa: E402
