"""Offline Issue #748 BFF request-log triage contract validator."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from nac_bff.bff_request_log_triage import TriageBlocked, load_triage_contract  # noqa: E402


def main() -> int:
    try:
        load_triage_contract(REPO_ROOT)
    except TriageBlocked as exc:
        print("STATUS: FAILED")
        print(f"ERROR: {exc.code}")
        return 1
    print("STATUS: PASSED")
    print("OK: Issue #748 BFF-Triage-Vertrag ist offline und fail-closed gebunden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
