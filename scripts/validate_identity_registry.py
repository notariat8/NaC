from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "policies" / "github-identity-registry.json"
ACCOUNT_ID_RE = re.compile(r"^[a-z0-9-]+:[^:]+$")
PRINCIPAL_ID_RE = re.compile(r"^person:[a-z0-9][a-z0-9-]*$")


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("version") != 2:
        errors.append("registry version must be 2")
    if "users" in registry:
        errors.append("legacy users/github_login model is forbidden")

    principals = registry.get("principals")
    accounts = registry.get("accounts")
    if not isinstance(principals, list) or not isinstance(accounts, list):
        return errors + ["principals and accounts must be arrays"]

    principal_ids: set[str] = set()
    for principal in principals:
        principal_id = principal.get("principal_id") if isinstance(principal, dict) else None
        if not isinstance(principal_id, str) or not PRINCIPAL_ID_RE.fullmatch(principal_id):
            errors.append(f"invalid principal_id: {principal_id!r}")
            continue
        if principal_id in principal_ids:
            errors.append(f"duplicate principal_id: {principal_id}")
        principal_ids.add(principal_id)
        if "technical_role_id" in principal:
            errors.append(f"principal {principal_id} must use technical_role_ids")
        roles = principal.get("technical_role_ids")
        if not isinstance(roles, list) or not roles or not all(isinstance(role, str) for role in roles):
            errors.append(f"principal {principal_id} requires technical_role_ids")

    account_ids: set[str] = set()
    provider_logins: set[tuple[str, str]] = set()
    for account in accounts:
        if not isinstance(account, dict):
            errors.append("account entries must be objects")
            continue
        account_id = account.get("account_id")
        provider = account.get("provider")
        login = account.get("login")
        principal_id = account.get("principal_id")
        if not isinstance(account_id, str) or not ACCOUNT_ID_RE.fullmatch(account_id):
            errors.append(f"account_id must be provider-qualified: {account_id!r}")
        elif account_id != f"{provider}:{login}":
            errors.append(f"account_id does not match provider/login: {account_id}")
        elif account_id in account_ids:
            errors.append(f"duplicate account_id: {account_id}")
        else:
            account_ids.add(account_id)
        key = (str(provider).lower(), str(login).lower())
        if key in provider_logins:
            errors.append(f"duplicate provider/login: {provider}:{login}")
        provider_logins.add(key)
        if principal_id not in principal_ids:
            errors.append(f"account {account_id!r} references unknown principal_id {principal_id!r}")
        for forbidden in ("technical_role_id", "technical_role_ids", "qualifications"):
            if forbidden in account:
                errors.append(f"account {account_id!r} must not carry {forbidden}")
    return errors


def resolve_account(registry: dict[str, Any], account_id: str) -> dict[str, Any] | None:
    if not ACCOUNT_ID_RE.fullmatch(account_id):
        raise ValueError("raw login is not a governance account_id")
    normalized = account_id.lower()
    return next(
        (account for account in registry.get("accounts", []) if account.get("account_id", "").lower() == normalized),
        None,
    )


def resolve_principal(registry: dict[str, Any], account_id: str) -> dict[str, Any] | None:
    account = resolve_account(registry, account_id)
    if account is None or not account.get("active", False):
        return None
    principal_id = account.get("principal_id")
    return next(
        (principal for principal in registry.get("principals", []) if principal.get("principal_id") == principal_id and principal.get("active", False)),
        None,
    )


def satisfies_four_eyes(registry: dict[str, Any], first_account_id: str, second_account_id: str) -> bool:
    first = resolve_principal(registry, first_account_id)
    second = resolve_principal(registry, second_account_id)
    return bool(first and second and first["principal_id"] != second["principal_id"])


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    errors = validate_registry(registry)
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
