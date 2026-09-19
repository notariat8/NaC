from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile


_GIT = Path(shutil.which("git") or "/usr/bin/git")
_OBJECT_RE = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_MODES = frozenset({"100644", "100755"})
_MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
_MAX_FILE_COUNT = 50_000


class ApprovedGitTreeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApprovedTreeSnapshot:
    root: Path
    manifest_sha256: str
    file_count: int


@dataclass(frozen=True)
class ApprovedTreeInspection:
    manifest_sha256: str
    file_count: int
    file_sha256: dict[str, str]


class GitApprovedTreeSource:
    """Materialize regular blobs from one exact approved Git commit tree."""

    def inspect(
        self,
        repo_root: Path,
        *,
        approved_commit: str,
        approved_tree: str,
    ) -> ApprovedTreeInspection:
        entries, files, manifest_sha256 = _verified_tree_payload(
            repo_root,
            approved_commit=approved_commit,
            approved_tree=approved_tree,
        )
        return ApprovedTreeInspection(
            manifest_sha256=manifest_sha256,
            file_count=len(entries),
            file_sha256={
                path: hashlib.sha256(files[path]).hexdigest()
                for path in sorted(entries)
            },
        )

    def materialize(
        self,
        repo_root: Path,
        target_root: Path,
        *,
        approved_commit: str,
        approved_tree: str,
    ) -> ApprovedTreeSnapshot:
        target = target_root.absolute()
        entries, files, manifest_sha256 = _verified_tree_payload(
            repo_root,
            approved_commit=approved_commit,
            approved_tree=approved_tree,
        )

        if target.exists():
            raise ApprovedGitTreeError("APPROVED_GIT_SNAPSHOT_TARGET_EXISTS")
        if os.name == "nt":
            _materialize_windows_snapshot(target, entries, files)
            return ApprovedTreeSnapshot(
                root=target,
                manifest_sha256=manifest_sha256,
                file_count=len(entries),
            )
        target.mkdir(parents=True, mode=0o700)
        try:
            for relative_path, (mode, blob_id) in entries.items():
                destination = target / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                data = files[relative_path]
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                descriptor = os.open(
                    destination,
                    flags,
                    0o500 if mode == "100755" else 0o400,
                )
                try:
                    with os.fdopen(descriptor, "wb", closefd=False) as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                finally:
                    os.close(descriptor)
                if _git_blob_id(data) != blob_id:
                    raise ApprovedGitTreeError("APPROVED_GIT_BLOB_MISMATCH")
        except (OSError, KeyError):
            raise ApprovedGitTreeError("APPROVED_GIT_SNAPSHOT_WRITE_FAILED") from None

        return ApprovedTreeSnapshot(
            root=target,
            manifest_sha256=manifest_sha256,
            file_count=len(entries),
        )


def _materialize_windows_snapshot(
    target: Path,
    entries: dict[str, tuple[str, str]],
    files: dict[str, bytes],
) -> None:
    try:
        from .activation_security_backend import (
            SecurityBoundaryError,
            get_platform_security_backend,
        )

        backend = get_platform_security_backend()
        with backend.open_secure_directory(target, create=True):
            pass
        for relative_path, (_mode, blob_id) in entries.items():
            destination = target / relative_path
            data = files[relative_path]
            with backend.open_secure_directory(
                destination.parent,
                create=True,
            ) as directory:
                snapshot = directory.create_exclusive(destination.name, data)
            if (
                snapshot.sha256 != hashlib.sha256(data).hexdigest()
                or _git_blob_id(data) != blob_id
            ):
                raise ApprovedGitTreeError("APPROVED_GIT_BLOB_MISMATCH")
    except ApprovedGitTreeError:
        raise
    except (KeyError, OSError, RuntimeError, SecurityBoundaryError):
        raise ApprovedGitTreeError(
            "APPROVED_GIT_SNAPSHOT_WRITE_FAILED"
        ) from None


def _verified_tree_payload(
    repo_root: Path,
    *,
    approved_commit: str,
    approved_tree: str,
) -> tuple[dict[str, tuple[str, str]], dict[str, bytes], str]:
    root = repo_root.resolve()
    if not _OBJECT_RE.fullmatch(approved_commit) or not _OBJECT_RE.fullmatch(
        approved_tree
    ):
        raise ApprovedGitTreeError("APPROVED_GIT_OBJECT_INVALID")
    git = _trusted_git()
    resolved_tree = _git_text(
        git, root, ("rev-parse", "--verify", f"{approved_commit}^{{tree}}")
    )
    if resolved_tree != approved_tree:
        raise ApprovedGitTreeError("APPROVED_GIT_TREE_MISMATCH")
    listing = _git_bytes(
        git, root, ("ls-tree", "-r", "-z", "--full-tree", approved_tree)
    )
    entries = _parse_tree_listing(listing)
    archive = _git_bytes(
        git, root, ("archive", "--format=tar", approved_tree),
        max_bytes=_MAX_ARCHIVE_BYTES,
    )
    files = _read_archive(archive, entries)
    if any(
        _git_blob_id(files[path]) != blob_id
        for path, (_mode, blob_id) in entries.items()
    ):
        raise ApprovedGitTreeError("APPROVED_GIT_BLOB_MISMATCH")
    manifest = {
        "schema_version": "nac.approved-git-tree-snapshot/v1",
        "approved_commit_sha": approved_commit,
        "approved_tree_sha": approved_tree,
        "files": [
            {
                "path": path,
                "mode": mode,
                "blob_sha1": blob_id,
                "sha256": hashlib.sha256(files[path]).hexdigest(),
            }
            for path, (mode, blob_id) in sorted(entries.items())
        ],
    }
    manifest_sha256 = hashlib.sha256(
        json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    ).hexdigest()
    return entries, files, manifest_sha256


def _trusted_git() -> Path:
    if os.name == "nt":
        try:
            from .activation_security_backend import (
                SecurityBoundaryError,
                get_platform_security_backend,
            )

            get_platform_security_backend().inspect_private_path(
                _GIT,
                purpose="toolchain-executable",
            )
            return _GIT
        except (OSError, SecurityBoundaryError, RuntimeError):
            raise ApprovedGitTreeError("TRUSTED_GIT_UNAVAILABLE") from None
    try:
        metadata = _GIT.stat()
    except OSError:
        raise ApprovedGitTreeError("TRUSTED_GIT_UNAVAILABLE") from None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_mode & 0o022
        or not os.access(_GIT, os.X_OK)
    ):
        raise ApprovedGitTreeError("TRUSTED_GIT_UNAVAILABLE")
    return _GIT


def _git_text(git: Path, root: Path, argv: tuple[str, ...]) -> str:
    value = _git_bytes(git, root, argv, max_bytes=1024).decode("ascii").strip().lower()
    if not _OBJECT_RE.fullmatch(value):
        raise ApprovedGitTreeError("APPROVED_GIT_OBJECT_INVALID")
    return value


def _git_bytes(
    git: Path,
    root: Path,
    argv: tuple[str, ...],
    *,
    max_bytes: int = _MAX_ARCHIVE_BYTES,
) -> bytes:
    arguments = (
        "--no-optional-locks",
        "--no-replace-objects",
        "-C",
        str(root),
        *argv,
    )
    if os.name == "nt":
        try:
            from .activation_security_backend import (
                ProcessSpec,
                SecurityBoundaryError,
                get_platform_security_backend,
            )

            backend = get_platform_security_backend()
            executable_hash = backend.inspect_private_path(
                git,
                purpose="toolchain-executable",
            ).sha256
            environment = {
                key: os.environ[key]
                for key in ("SystemRoot", "TEMP", "TMP", "USERPROFILE", "HOME")
                if key in os.environ
            }
            result = backend.launch_attested_process(
                ProcessSpec(
                    executable=git,
                    arguments=arguments,
                    cwd=root,
                    environment=environment,
                    executable_sha256=executable_hash,
                    timeout_seconds=60,
                    maximum_output_bytes=max_bytes,
                    allowed_exit_codes=tuple(range(256)),
                )
            )
        except (OSError, SecurityBoundaryError, RuntimeError):
            raise ApprovedGitTreeError("APPROVED_GIT_READ_FAILED") from None
        if result.exit_code != 0 or len(result.stdout) > max_bytes:
            raise ApprovedGitTreeError("APPROVED_GIT_READ_FAILED")
        return result.stdout
    try:
        result = subprocess.run(
            [
                str(git),
                *arguments,
            ],
            check=False,
            capture_output=True,
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        raise ApprovedGitTreeError("APPROVED_GIT_READ_FAILED") from None
    if result.returncode != 0 or len(result.stdout) > max_bytes:
        raise ApprovedGitTreeError("APPROVED_GIT_READ_FAILED")
    return result.stdout


def _parse_tree_listing(payload: bytes) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    for raw in payload.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, raw_path = raw.split(b"\t", 1)
            mode, object_type, blob_id = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            raise ApprovedGitTreeError("APPROVED_GIT_TREE_ENTRY_INVALID") from None
        normalized = _safe_relative_path(path)
        if (
            mode not in _ALLOWED_MODES
            or object_type != "blob"
            or not _OBJECT_RE.fullmatch(blob_id)
            or normalized in entries
        ):
            raise ApprovedGitTreeError("APPROVED_GIT_TREE_ENTRY_INVALID")
        entries[normalized] = (mode, blob_id)
        if len(entries) > _MAX_FILE_COUNT:
            raise ApprovedGitTreeError("APPROVED_GIT_TREE_TOO_LARGE")
    if not entries:
        raise ApprovedGitTreeError("APPROVED_GIT_TREE_EMPTY")
    return entries


def _read_archive(
    payload: bytes, entries: dict[str, tuple[str, str]]
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
            for member in archive:
                path = _safe_relative_path(member.name)
                if member.isdir():
                    continue
                if not member.isfile() or path not in entries or path in files:
                    raise ApprovedGitTreeError("APPROVED_GIT_ARCHIVE_INVALID")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ApprovedGitTreeError("APPROVED_GIT_ARCHIVE_INVALID")
                files[path] = stream.read()
    except (tarfile.TarError, OSError):
        raise ApprovedGitTreeError("APPROVED_GIT_ARCHIVE_INVALID") from None
    if set(files) != set(entries):
        raise ApprovedGitTreeError("APPROVED_GIT_ARCHIVE_INVALID")
    return files


def _safe_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ApprovedGitTreeError("APPROVED_GIT_PATH_INVALID")
    return path.as_posix()


def _git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()
