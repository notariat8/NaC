from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from typing import Any, Mapping, Protocol, Sequence

from nac_identity.governance_registry import (
    OWNER_SOLO_APPROVAL,
    evaluate_approval_mode,
    resolve_principal,
    validate_registry,
)


ISSUE_NUMBER = 746
PR_NUMBER = 747
AUTHORIZATION_SCOPE = "issue746_readonly_reconciliation"
GATE_CLOSED = "ISSUE_746_RECONCILIATION_GATE_CLOSED"
REQUIRED_REMOTE_CONTEXTS = frozenset(
    {
        "Privacy and Secrets Guard / secret-scan",
        "Privacy and Secrets Guard / privacy-lint",
        "NaC Quality Gate / quality-gate",
        "NaC Windows Portability / windows-offline-cli",
    }
)
_REFERENCE_RE = re.compile(
    r"https://github\.com/notariat8/NaC/issues/746#issuecomment-([1-9][0-9]*)"
)
_HEX_40_RE = re.compile(r"[0-9a-f]{40}")
_HEX_64_RE = re.compile(r"[0-9a-f]{64}")
_AUTHORIZATION_SEAL = object()


class Issue746ReconciliationGateError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"{GATE_CLOSED}: {reason}")
        self.code = GATE_CLOSED
        self.reason = reason


class Issue746GitHubReadPort(Protocol):
    def read_json(self, argv: Sequence[str]) -> Mapping[str, Any] | None: ...


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def identity_binding_sha256(kind: str, value: str) -> str:
    return _sha256_text(f"nac-issue-746-{kind}-v1\0{value}")


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return _sha256_text(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )


@dataclass(frozen=True)
class Issue746ReconciliationAuthorization:
    approved_head: str
    approved_tree: str
    pr_number: int
    resolver_sha256: str
    operator_account_id_sha256: str
    operator_principal_id_sha256: str
    approval_reference_sha256: str
    approval_body_sha256: str
    required_checks_sha256: str
    authorization_sha256: str
    _runtime_seal: object = field(repr=False, compare=False)
    approval_mode: str = OWNER_SOLO_APPROVAL
    four_eyes_satisfied: bool = False
    scope: str = AUTHORIZATION_SCOPE

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "approved_head": self.approved_head,
            "approved_tree": self.approved_tree,
            "pr_number": self.pr_number,
            "resolver_sha256": self.resolver_sha256,
            "operator_account_id_sha256": self.operator_account_id_sha256,
            "operator_principal_id_sha256": self.operator_principal_id_sha256,
            "approval_reference_sha256": self.approval_reference_sha256,
            "approval_body_sha256": self.approval_body_sha256,
            "required_checks_sha256": self.required_checks_sha256,
            "approval_mode": self.approval_mode,
            "four_eyes_satisfied": self.four_eyes_satisfied,
            "scope": self.scope,
        }

    def verify(self, *, expected_head: str, expected_tree: str) -> None:
        if (
            self._runtime_seal is not _AUTHORIZATION_SEAL
            or self.scope != AUTHORIZATION_SCOPE
            or self.approval_mode != OWNER_SOLO_APPROVAL
            or self.four_eyes_satisfied is not False
            or self.pr_number != PR_NUMBER
            or self.approved_head != expected_head
            or self.approved_tree != expected_tree
            or not _HEX_40_RE.fullmatch(self.approved_head)
            or not _HEX_40_RE.fullmatch(self.approved_tree)
        ):
            raise Issue746ReconciliationGateError("authorization binding mismatch")
        digests = (
            self.resolver_sha256,
            self.operator_account_id_sha256,
            self.operator_principal_id_sha256,
            self.approval_reference_sha256,
            self.approval_body_sha256,
            self.required_checks_sha256,
        )
        if not all(_HEX_64_RE.fullmatch(value) for value in digests):
            raise Issue746ReconciliationGateError("authorization digest invalid")
        if self.authorization_sha256 != _canonical_sha256(self.canonical_payload()):
            raise Issue746ReconciliationGateError("authorization digest mismatch")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _load_posix_protected_bytes(path: Path) -> bytes:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None:
        raise Issue746ReconciliationGateError("protected resolver backend unavailable")
    directory_descriptor: int | None = None
    descriptor: int | None = None
    try:
        directory_descriptor = os.open("/", os.O_RDONLY | directory | nofollow)
        components = path.parts[1:]
        if not components:
            raise OSError("resolver leaf missing")
        for component in components[:-1]:
            next_descriptor = os.open(
                component,
                os.O_RDONLY | directory | nofollow,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(
            components[-1], os.O_RDONLY | nofollow, dir_fd=directory_descriptor
        )
        file_stat = os.fstat(descriptor)
        if (
            not stat.S_ISREG(file_stat.st_mode)
            or file_stat.st_uid != os.geteuid()
            or stat.S_IMODE(file_stat.st_mode) != 0o600
            or file_stat.st_size > 131072
        ):
            raise Issue746ReconciliationGateError("protected resolver metadata invalid")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            payload = handle.read(131073)
        if len(payload) > 131072:
            raise Issue746ReconciliationGateError("protected resolver exceeds size limit")
        return payload
    except Issue746ReconciliationGateError:
        raise
    except OSError as exc:
        raise Issue746ReconciliationGateError("protected resolver secure open failed") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def load_protected_identity_resolver(
    *, repo_root: Path, path: Path, expected_sha256: str
) -> dict[str, Any]:
    if not path.is_absolute() or not _HEX_64_RE.fullmatch(expected_sha256):
        raise Issue746ReconciliationGateError("protected resolver binding invalid")
    normalized = Path(os.path.abspath(path))
    try:
        normalized.relative_to(repo_root.resolve())
    except ValueError:
        pass
    else:
        raise Issue746ReconciliationGateError("protected resolver must be outside repository")
    if os.name == "nt":
        try:
            from .activation_security_backend import get_platform_security_backend

            backend = get_platform_security_backend()
            binding = backend.inspect_private_path(
                normalized, purpose="protected-identity-resolver"
            )
            if binding.size > 131072:
                raise Issue746ReconciliationGateError(
                    "protected resolver exceeds size limit"
                )
            with backend.open_bound_read(normalized, binding) as handle:
                payload_bytes = handle.read(131073)
        except Issue746ReconciliationGateError:
            raise
        except (OSError, RuntimeError) as exc:
            raise Issue746ReconciliationGateError(
                "protected resolver secure Windows open failed"
            ) from exc
    else:
        payload_bytes = _load_posix_protected_bytes(normalized)
    if len(payload_bytes) > 131072 or _sha256_bytes(payload_bytes) != expected_sha256:
        raise Issue746ReconciliationGateError("protected resolver digest mismatch")
    try:
        payload = json.loads(
            payload_bytes.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise Issue746ReconciliationGateError("protected resolver JSON invalid") from exc
    if not isinstance(payload, dict):
        raise Issue746ReconciliationGateError("protected resolver shape invalid")
    return payload


def resolve_authorized_operator(
    resolver: Mapping[str, Any], operator_account_id: str
) -> Mapping[str, Any]:
    if set(resolver) != {
        "schema_version",
        "contract_id",
        "known_owner_account_count",
        "all_known_accounts_same_principal",
        "registry",
    }:
        raise Issue746ReconciliationGateError("protected resolver shape invalid")
    if (
        resolver.get("schema_version") != "nac.protected-identity-resolver/v1"
        or resolver.get("contract_id")
        != "issue-746-owner-account-principal-resolution"
        or resolver.get("known_owner_account_count") != 3
        or resolver.get("all_known_accounts_same_principal") is not True
    ):
        raise Issue746ReconciliationGateError("protected resolver contract invalid")
    registry = resolver.get("registry")
    if not isinstance(registry, dict) or validate_registry(registry):
        raise Issue746ReconciliationGateError("protected resolver registry invalid")
    accounts = registry.get("accounts", [])
    active_accounts = [
        account
        for account in accounts
        if isinstance(account, dict) and account.get("active") is True
    ]
    principal_ids = {account.get("principal_id") for account in active_accounts}
    if len(accounts) != 3 or len(active_accounts) != 3 or len(principal_ids) != 1:
        raise Issue746ReconciliationGateError("three-account principal binding invalid")
    try:
        operator = resolve_principal(registry, operator_account_id)
    except ValueError as exc:
        raise Issue746ReconciliationGateError("operator account id invalid") from exc
    if operator is None or operator.get("principal_id") not in principal_ids:
        raise Issue746ReconciliationGateError("operator principal unresolved")
    if "prozessverantwortung" not in operator.get("technical_role_ids", []):
        raise Issue746ReconciliationGateError("operator process role missing")
    if "process_design" not in operator.get("qualifications", []):
        raise Issue746ReconciliationGateError("operator qualification missing")
    decision = evaluate_approval_mode(
        registry,
        operator_account_id=operator_account_id,
        external_two_person_required=False,
    )
    if (
        decision.get("status") != OWNER_SOLO_APPROVAL
        or decision.get("four_eyes_satisfied") != "false"
    ):
        raise Issue746ReconciliationGateError("solo-owner mode invalid")
    return operator


def _git_read(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise Issue746ReconciliationGateError("git snapshot unavailable") from exc
    if result.returncode != 0:
        raise Issue746ReconciliationGateError("git snapshot unavailable")
    return result.stdout.rstrip("\n")


def read_clean_git_snapshot(repo_root: Path) -> tuple[str, str]:
    head = _git_read(repo_root, "rev-parse", "--verify", "HEAD^{commit}")
    tree = _git_read(repo_root, "rev-parse", "--verify", f"{head}^{{tree}}")
    dirty = _git_read(
        repo_root, "status", "--porcelain=v1", "--untracked-files=all"
    )
    if dirty:
        raise Issue746ReconciliationGateError("worktree is not clean")
    if not _HEX_40_RE.fullmatch(head) or not _HEX_40_RE.fullmatch(tree):
        raise Issue746ReconciliationGateError("git snapshot invalid")
    return head, tree


def _check_context(item: Mapping[str, Any]) -> str:
    workflow = item.get("workflowName") or item.get("workflow_name")
    name = item.get("name") or item.get("context")
    return f"{workflow} / {name}" if workflow else str(name)


def _verify_pr(payload: Mapping[str, Any], *, expected_head: str) -> str:
    if payload.get("number") != PR_NUMBER or payload.get("headRefOid") != expected_head:
        raise Issue746ReconciliationGateError("PR binding mismatch")
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    checks = payload.get("statusCheckRollup")
    if not isinstance(checks, list):
        raise Issue746ReconciliationGateError("PR checks missing")
    for item in checks:
        if isinstance(item, Mapping):
            grouped.setdefault(_check_context(item), []).append(item)
    for context in REQUIRED_REMOTE_CONTEXTS:
        instances = grouped.get(context, [])
        if len(instances) != 1:
            raise Issue746ReconciliationGateError("required PR check missing or duplicated")
        conclusion = str(
            instances[0].get("conclusion") or instances[0].get("state") or ""
        ).upper()
        if conclusion not in {"SUCCESS", "PASSED"}:
            raise Issue746ReconciliationGateError("required PR check not successful")
    return _canonical_sha256(
        {"contexts": sorted(REQUIRED_REMOTE_CONTEXTS), "head": expected_head}
    )


def verify_issue746_readonly_reconciliation_gate(
    *,
    repo_root: Path,
    protected_identity_resolver_file: Path,
    protected_identity_resolver_sha256: str,
    operator_account_id: str,
    owner_solo_approval_reference: str,
    github_reader: Issue746GitHubReadPort,
) -> Issue746ReconciliationAuthorization:
    resolver = load_protected_identity_resolver(
        repo_root=repo_root,
        path=protected_identity_resolver_file,
        expected_sha256=protected_identity_resolver_sha256,
    )
    operator = resolve_authorized_operator(resolver, operator_account_id)
    principal_id = str(operator.get("principal_id"))
    head, tree = read_clean_git_snapshot(repo_root)

    pr_payload = github_reader.read_json(
        (
            "pr",
            "view",
            str(PR_NUMBER),
            "--json",
            "number,headRefOid,statusCheckRollup",
        )
    )
    if pr_payload is None:
        raise Issue746ReconciliationGateError("GitHub PR read capability unavailable")
    required_checks_sha256 = _verify_pr(pr_payload, expected_head=head)

    match = _REFERENCE_RE.fullmatch(owner_solo_approval_reference)
    if match is None:
        raise Issue746ReconciliationGateError("owner approval reference invalid")
    comment = github_reader.read_json(
        ("api", f"repos/notariat8/NaC/issues/comments/{match.group(1)}")
    )
    if comment is None:
        raise Issue746ReconciliationGateError("owner approval read capability unavailable")
    expected_body = (
        "OWNER_SOLO_APPROVAL\n"
        "issue=746\n"
        "pr=747\n"
        f"head_sha={head}\n"
        f"account_id_sha256={identity_binding_sha256('account-id', operator_account_id)}\n"
        f"principal_id_sha256={identity_binding_sha256('principal-id', principal_id)}\n"
        f"identity_resolver_sha256={protected_identity_resolver_sha256}\n"
        "four_eyes_satisfied=false"
    )
    author = comment.get("user")
    account_login = operator_account_id.split(":", 1)[1]
    if (
        comment.get("html_url") != owner_solo_approval_reference
        or comment.get("created_at") != comment.get("updated_at")
        or comment.get("author_association") != "OWNER"
        or not isinstance(author, Mapping)
        or author.get("login") != account_login
        or comment.get("body") != expected_body
    ):
        raise Issue746ReconciliationGateError("owner approval provenance invalid")

    values: dict[str, Any] = {
        "approved_head": head,
        "approved_tree": tree,
        "pr_number": PR_NUMBER,
        "resolver_sha256": protected_identity_resolver_sha256,
        "operator_account_id_sha256": identity_binding_sha256(
            "account-id", operator_account_id
        ),
        "operator_principal_id_sha256": identity_binding_sha256(
            "principal-id", principal_id
        ),
        "approval_reference_sha256": _sha256_text(owner_solo_approval_reference),
        "approval_body_sha256": _sha256_text(expected_body),
        "required_checks_sha256": required_checks_sha256,
        "approval_mode": OWNER_SOLO_APPROVAL,
        "four_eyes_satisfied": False,
        "scope": AUTHORIZATION_SCOPE,
    }
    authorization = Issue746ReconciliationAuthorization(
        **values,
        authorization_sha256=_canonical_sha256(values),
        _runtime_seal=_AUTHORIZATION_SEAL,
    )
    authorization.verify(expected_head=head, expected_tree=tree)
    return authorization
