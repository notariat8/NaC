from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_ai_sbom.export_mapping import load_export_mapping  # noqa: E402


def validate() -> list[str]:
    try:
        load_export_mapping(REPO_ROOT)
    except (KeyError, ValueError) as exc:
        return [str(exc)]
    return []


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: AI-SBOM-Export-Mapping ist gewaehlt, aber Release-Export bleibt gesperrt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
