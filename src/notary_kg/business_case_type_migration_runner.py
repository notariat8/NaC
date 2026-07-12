from __future__ import annotations

import json
import os
import re
import stat
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from .business_case_type_migration import (
    LocalMigrationReplayPort,
    MigrationValidationError,
    build_backfill_plan,
    build_forward_recovery_plan,
    build_manifest,
    build_readiness_evidence_anchor,
    build_rollback_plan,
    canonical_json_hash,
    classify_records,
    evaluate_cutover_readiness,
    run_migration_replay,
    validate_bundle,
    validate_mapping_table,
)
from .business_case_type_migration_quarantine import (
    ArtifactWriteError,
    QuarantineStore,
    canonical_contained_path,
    write_redacted_output,
)
from .business_case_type_runtime import BusinessCaseTypeCatalog


_OBJECT_ID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_SAFE_REF_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
MAPPING_PATH = Path("workflows/migrations/business-case-type/legacy-choice.mapping.json")
CANDIDATES_PATH = Path("workflows/migrations/business-case-type/runtime-candidates.json")
FIXTURE_ROOT = Path("tests/fixtures/business-case-type-migration")
OUTPUT_ROOT = Path("out/notary-kg")
DEFAULT_OUTPUT = OUTPUT_ROOT / "business-case-type-migration-s5.redacted.json"
_MAX_ADMIN_FILE_BYTES = 1024 * 1024
_MAX_PACKED_REFS_BYTES = 8 * 1024 * 1024
_MAX_FIXTURE_BYTES = 4 * 1024 * 1024


class RepositoryStateError(RuntimeError):
    pass


class MigrationContractError(RuntimeError):
    pass


def run_offline_migration(
    repo_root: Path,
    *,
    fixture: Path,
    quarantine_state: Path,
    output: Path = DEFAULT_OUTPUT,
    artifact_root: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    repo_root = repo_root.resolve(strict=True)
    output_root = (
        artifact_root.absolute() if artifact_root is not None else (repo_root / OUTPUT_ROOT).absolute()
    )
    quarantine_candidate = quarantine_state if artifact_root is not None else repo_root / quarantine_state
    output_candidate = output if artifact_root is not None else repo_root / output
    quarantine_path = canonical_contained_path(quarantine_candidate, root=output_root)
    output_path = canonical_contained_path(output_candidate, root=output_root)
    if _overlaps(quarantine_path, output_path):
        raise ArtifactWriteError()

    try:
        bundle = _read_fixture_object(repo_root, fixture)
    except (OSError, UnicodeError, json.JSONDecodeError, MigrationValidationError) as exc:
        raise MigrationValidationError("fixture_invalid") from exc
    try:
        mapping_table = _read_object(repo_root / MAPPING_PATH)
        candidate_registry = _read_object(repo_root / CANDIDATES_PATH)
        catalog = BusinessCaseTypeCatalog.from_repo(repo_root)
        known_ids = frozenset(entry.business_case_type_id for entry in catalog.entries)
        mapping = validate_mapping_table(mapping_table, known_ids)
        candidates = candidate_registry["candidates"]
        candidate_bindings = [
            (candidate["candidate_id"], candidate["contract_version"])
            for candidate in candidates
        ]
        if candidate_bindings != [("runtime-current", "v2"), ("runtime-previous", "v1")]:
            raise MigrationValidationError("runtime candidate binding mismatch")
    except (
        AttributeError,
        KeyError,
        OSError,
        TypeError,
        UnicodeError,
        json.JSONDecodeError,
        MigrationValidationError,
        ValueError,
    ) as exc:
        raise MigrationContractError("contract_invalid") from exc
    try:
        records = validate_bundle(bundle, known_ids)
        if bundle.get("catalog_version") != catalog.catalog_version:
            raise MigrationValidationError("fixture_invalid")
    except MigrationValidationError as exc:
        raise MigrationValidationError("fixture_invalid") from exc
    try:
        replay = run_migration_replay(
            candidate_registry=candidate_registry,
            scenarios=bundle["replay_scenarios"],
            canonical_business_case_type_ids=known_ids,
            port=LocalMigrationReplayPort(),
        )
    except (AttributeError, KeyError, TypeError, MigrationValidationError) as exc:
        raise MigrationContractError("contract_invalid") from exc

    manifest = build_manifest(
        repository_commit=read_repository_head(repo_root),
        catalog_version=catalog.catalog_version,
        mapping_table=mapping_table,
        matter_pages=bundle["matter_pages"],
        registry_snapshot=bundle["registry_snapshot"],
        process_snapshot=bundle["process_snapshot"],
        bindings=bundle["bindings"],
        role_approval_refs=bundle["role_approval_refs"],
        schema_version=bundle["schema_version"],
        runtime_version=str(candidates[0].get("candidate_id", "")),
        contract_version_n=str(candidates[0].get("contract_version", "")),
        candidate_n_minus_1=str(candidates[1].get("candidate_id", "")),
        runtime_candidate_registry=candidate_registry,
        final_scans=bundle["scans"],
        post_scan_observed_at=bundle["post_scan_observed_at"],
        post_scan_registry_snapshot=bundle["post_scan_registry_snapshot"],
        post_scan_process_snapshot=bundle["post_scan_process_snapshot"],
        canonical_business_case_type_ids=known_ids,
    )
    classified = classify_records(records, mapping, known_ids)
    backfill = build_backfill_plan(
        classified,
        manifest_hash=manifest["manifest_hash"],
        observed_at=bundle["observed_at"],
    )
    rollback = build_rollback_plan(
        manifest_hash=manifest["manifest_hash"],
        candidate_n_minus_1=str(candidates[1]["candidate_id"]),
    )
    forward_recovery = build_forward_recovery_plan(
        manifest_hash=manifest["manifest_hash"],
        candidate_n=str(candidates[0]["candidate_id"]),
    )
    store = QuarantineStore(quarantine_path)
    with store.persist_locked(backfill["quarantine"]) as quarantine_index:
        readiness_anchor = build_readiness_evidence_anchor(
            base_manifest_hash=manifest["manifest_hash"],
            backfill_plan=backfill,
            replay_scenarios=bundle["replay_scenarios"],
            profile_evaluation_result=replay,
            reconciled_quarantine_index=quarantine_index,
        )
        readiness = evaluate_cutover_readiness(
            classification_counts=backfill["classification_counts"],
            scans=bundle["scans"],
            manifest_registry_snapshot_hash=manifest["registry_snapshot_hash"],
            current_registry_snapshot=bundle["post_scan_registry_snapshot"],
            manifest_process_snapshot_hash=manifest["process_snapshot_hash"],
            current_process_snapshot=bundle["post_scan_process_snapshot"],
            replay_result=replay,
        )
        quarantine_records = quarantine_index.get("records")
        if not isinstance(quarantine_records, list):
            raise ArtifactWriteError()
        if quarantine_records:
            reason_codes = list(readiness["reason_codes"])
            if "quarantine_not_empty" not in reason_codes:
                reason_codes.append("quarantine_not_empty")
            readiness = {
                **readiness,
                "status": "BLOCKED",
                "reason_codes": reason_codes,
            }
        readiness = {
            **readiness,
            "readiness_evidence_hash": readiness_anchor["readiness_evidence_hash"],
        }
        artifact = {
            "schema_version": "nac.business-case-type-migration-s5-evidence/v0.1",
            "status": readiness["status"],
            "readiness_scope": "S5_OFFLINE_ONLY",
            "live_cutover_status": "BLOCKED_PENDING_S6_S7_APPROVAL",
            "allowed_live_calls": 0,
            "allowed_tenant_writes": 0,
            "manifest": manifest,
            "readiness_evidence_anchor": readiness_anchor,
            "backfill_plan": backfill,
            "quarantine_index": quarantine_index,
            "profile_evaluation": replay,
            "readiness": readiness,
            "rollback": rollback,
            "forward_recovery": forward_recovery,
        }
        write_redacted_output(output_path, artifact, allowed_root=output_root)
        summary = {
            "status": readiness["status"],
            "readiness_scope": "S5_OFFLINE_ONLY",
            "live_cutover_status": "BLOCKED_PENDING_S6_S7_APPROVAL",
            "allowed_live_calls": 0,
            "allowed_tenant_writes": 0,
            "reason_codes": readiness["reason_codes"],
            "class_counts": backfill["classification_counts"],
            "top_level_hashes": {
                "manifest_hash": manifest["manifest_hash"],
                "mapping_hash": manifest["mapping_hash"],
                "profile_evaluation_hash": canonical_json_hash(replay),
                "readiness_evidence_hash": readiness_anchor["readiness_evidence_hash"],
            },
        }
    return (0 if readiness["status"] == "READY" else 2), summary


def read_repository_head(repo_root: Path) -> str:
    try:
        root = Path(os.path.abspath(repo_root))
        dot_git = root / ".git"
        with ExitStack() as descriptors:
            root_fd = _open_absolute_directory(root)
            descriptors.callback(os.close, root_fd)
            try:
                git_dir_fd = _open_directory_at(root_fd, ".git")
            except OSError:
                marker = _read_file_at(root_fd, ".git", encoding="utf-8").strip()
                if not marker.startswith("gitdir: ") or "\n" in marker:
                    raise RepositoryStateError()
                git_dir = _absolute_path(root, marker[8:])
                if git_dir.parent.name != "worktrees" or git_dir.parent.parent.name != ".git":
                    raise RepositoryStateError()
                common_dir = git_dir.parent.parent
                common_dir_fd = _open_absolute_directory(common_dir)
                descriptors.callback(os.close, common_dir_fd)
                worktrees_fd = _open_directory_at(common_dir_fd, "worktrees")
                descriptors.callback(os.close, worktrees_fd)
                git_dir_fd = _open_directory_at(worktrees_fd, git_dir.name)
                descriptors.callback(os.close, git_dir_fd)
                backlink = _read_file_at(git_dir_fd, "gitdir", encoding="utf-8").strip()
                if _absolute_path(git_dir, backlink) != dot_git:
                    raise RepositoryStateError()
                commondir = _read_file_at(git_dir_fd, "commondir", encoding="utf-8").strip()
                if _absolute_path(git_dir, commondir) != common_dir:
                    raise RepositoryStateError()
            else:
                descriptors.callback(os.close, git_dir_fd)
                common_dir_fd = git_dir_fd
                if _entry_exists_at(git_dir_fd, "commondir") or _entry_exists_at(
                    git_dir_fd, "gitdir"
                ):
                    raise RepositoryStateError()

            head = _read_file_at(git_dir_fd, "HEAD", encoding="ascii").strip()
            if _OBJECT_ID.fullmatch(head):
                return head
            if not head.startswith("ref: "):
                raise RepositoryStateError()
            ref = head[5:]
            if not _safe_ref(ref):
                raise RepositoryStateError()
            try:
                value = _read_relative_file(
                    common_dir_fd, ref.split("/"), encoding="ascii"
                ).strip()
            except FileNotFoundError:
                pass
            else:
                if _OBJECT_ID.fullmatch(value):
                    return value
                raise RepositoryStateError()
            try:
                packed_refs = _read_file_at(
                    common_dir_fd,
                    "packed-refs",
                    encoding="ascii",
                    max_bytes=_MAX_PACKED_REFS_BYTES,
                )
            except FileNotFoundError:
                packed_refs = ""
            matches = []
            for line in packed_refs.splitlines():
                if not line or line.startswith(("#", "^")):
                    continue
                fields = line.split(" ")
                if len(fields) != 2 or not _OBJECT_ID.fullmatch(fields[0]) or not _safe_ref(fields[1]):
                    raise RepositoryStateError()
                if fields[1] == ref:
                    matches.append(fields[0])
            if len(matches) == 1:
                return matches[0]
    except (OSError, UnicodeError, ValueError, RepositoryStateError):
        pass
    raise RepositoryStateError("repository_state_unavailable")


def _safe_ref(ref: str) -> bool:
    if not ref.startswith("refs/") or ref.endswith(("/", ".")) or ".." in ref or "@{" in ref:
        return False
    components = ref.split("/")
    return len(components) >= 3 and all(
        _SAFE_REF_COMPONENT.fullmatch(component)
        and not component.startswith(".")
        and not component.endswith(".lock")
        for component in components
    )


def _absolute_path(base: Path, value: str) -> Path:
    if not value or "\x00" in value:
        raise RepositoryStateError()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    return Path(os.path.abspath(candidate))


def _directory_open_flags() -> int:
    try:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    except AttributeError as exc:
        raise RepositoryStateError() from exc


def _open_directory_at(directory_fd: int, component: str) -> int:
    if not component or component in (".", "..") or "/" in component or "\x00" in component:
        raise RepositoryStateError()
    return os.open(component, _directory_open_flags(), dir_fd=directory_fd)


def _open_absolute_directory(path: Path) -> int:
    if not path.is_absolute() or not path.anchor:
        raise RepositoryStateError()
    descriptor = os.open(path.anchor, _directory_open_flags())
    try:
        for component in path.parts[1:]:
            next_descriptor = _open_directory_at(descriptor, component)
            os.close(descriptor)
            descriptor = next_descriptor
        result = descriptor
        descriptor = -1
        return result
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_file_at(
    directory_fd: int,
    name: str,
    *,
    encoding: str,
    max_bytes: int = _MAX_ADMIN_FILE_BYTES,
) -> str:
    if (
        not name
        or name in (".", "..")
        or "/" in name
        or "\x00" in name
        or type(max_bytes) is not int
        or max_bytes <= 0
    ):
        raise RepositoryStateError()
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_bytes:
            raise RepositoryStateError()
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise RepositoryStateError()
        return b"".join(chunks).decode(encoding)
    finally:
        os.close(descriptor)

def _read_relative_file(directory_fd: int, components: list[str], *, encoding: str) -> str:
    if not components:
        raise RepositoryStateError()
    descriptor = os.dup(directory_fd)
    try:
        for component in components[:-1]:
            next_descriptor = _open_directory_at(descriptor, component)
            os.close(descriptor)
            descriptor = next_descriptor
        return _read_file_at(descriptor, components[-1], encoding=encoding)
    finally:
        os.close(descriptor)


def _entry_exists_at(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MigrationValidationError("JSON root must be an object")
    return value



def _read_fixture_object(repo_root: Path, fixture: Path) -> dict[str, Any]:
    if fixture.is_absolute():
        raise MigrationValidationError("fixture_invalid")
    components = fixture.parts
    fixture_root_components = FIXTURE_ROOT.parts
    if (
        len(components) <= len(fixture_root_components)
        or components[: len(fixture_root_components)] != fixture_root_components
    ):
        raise MigrationValidationError("fixture_invalid")
    descriptor = _open_absolute_directory(repo_root)
    try:
        for component in components[:-1]:
            next_descriptor = _open_directory_at(descriptor, component)
            os.close(descriptor)
            descriptor = next_descriptor
        raw = _read_file_at(
            descriptor,
            components[-1],
            encoding="utf-8",
            max_bytes=_MAX_FIXTURE_BYTES,
        )
    except (OSError, UnicodeError, RepositoryStateError) as exc:
        raise MigrationValidationError("fixture_invalid") from exc
    finally:
        os.close(descriptor)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise MigrationValidationError("fixture_invalid")
    return value

def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents
