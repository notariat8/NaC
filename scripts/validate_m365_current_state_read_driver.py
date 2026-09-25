"""CLI wrapper for the offline Issue #748 driver-release verifier."""

from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nac_bff.current_state_read_driver_release import (  # noqa: E402
    main,
    validate_candidate_release,
    validate_release_contract,
    validate_resources,
)


if __name__ == "__main__":
    raise SystemExit(main())
