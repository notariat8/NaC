from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_identity.governance_registry import (
    ACCOUNT_ID_RE,
    BLOCKED_SINGLE_PRINCIPAL,
    OWNER_SOLO_APPROVAL,
    PRINCIPAL_ID_RE,
    evaluate_approval_mode,
    resolve_account,
    resolve_principal,
    satisfies_four_eyes,
    validate_registry,
)


REGISTRY_PATH = REPO_ROOT / "policies" / "github-identity-registry.json"
PUBLIC_SYNTHETIC_PRINCIPAL_IDS = {"person:owner-example"}
PUBLIC_SYNTHETIC_ACCOUNTS = {
    ("github:owner-example-primary", "owner-example-primary"),
    ("github:owner-example-secondary", "owner-example-secondary"),
    ("nvidia-gitlab:owner-example", "owner-example"),
}


def validate_public_registry_privacy(registry: dict[str, Any]) -> list[str]:
    """Allow only the exact synthetic identity fixture in the checked-in registry."""
    errors: list[str] = []
    principal_ids = {
        principal.get("principal_id")
        for principal in registry.get("principals", [])
        if isinstance(principal, dict)
    }
    if principal_ids != PUBLIC_SYNTHETIC_PRINCIPAL_IDS:
        errors.append("public registry must use the exact synthetic principal fixture")
    accounts = {
        (account.get("account_id"), account.get("login"))
        for account in registry.get("accounts", [])
        if isinstance(account, dict)
    }
    if accounts != PUBLIC_SYNTHETIC_ACCOUNTS:
        errors.append("public registry must use the exact synthetic account fixture")
    return errors


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    errors = validate_registry(registry)
    errors.extend(validate_public_registry_privacy(registry))
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: provider-qualified accounts resolve to stable principals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
