from pathlib import Path
import sys


FUNCTION_DIR = Path(__file__).resolve().parent
for candidate in (
    FUNCTION_DIR / "src",
    FUNCTION_DIR.parents[2] / "src",
    Path("/function/src"),
):
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from nac_web.oci_functions import handler  # noqa: E402
