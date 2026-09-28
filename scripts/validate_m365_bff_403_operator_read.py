"""Validate the exact inactive Issue #756 operator-read contract."""

from __future__ import annotations

import json

from nac_bff.bff_403_operator_read import CONTRACT_PATH, _unique_pairs, validate_contract


def validate() -> list[str]:
    try:
        value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    except (OSError, ValueError, UnicodeError):
        return ["operator contract cannot be read"]
    return validate_contract(value)


if __name__ == "__main__":
    errors = validate()
    for error in errors:
        print(f"ERROR: {error}")
    print("STATUS: PASSED" if not errors else "STATUS: FAILED")
    raise SystemExit(bool(errors))
