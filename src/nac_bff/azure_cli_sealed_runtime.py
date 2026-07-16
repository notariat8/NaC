from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import stat


_CHUNK_SIZE = 1024 * 1024
_TAMPER_EXIT = 86
_ISOLATION_EXIT = 87


@dataclass(slots=True)
class SealedAzureCliRuntime:
    interpreter_fd: int
    bootstrap_fd: int
    manifest_fd: int

    @property
    def pass_fds(self) -> tuple[int, int, int]:
        return (self.interpreter_fd, self.bootstrap_fd, self.manifest_fd)

    def command(self, azure_argv: list[str]) -> list[str]:
        return [
            f"/proc/self/fd/{self.interpreter_fd}",
            "-I",
            "-B",
            f"/proc/self/fd/{self.bootstrap_fd}",
            f"/proc/self/fd/{self.manifest_fd}",
            *azure_argv,
        ]

    def close(self) -> None:
        for descriptor in self.pass_fds:
            try:
                os.close(descriptor)
            except OSError:
                pass

    def __enter__(self) -> SealedAzureCliRuntime:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def prepare_sealed_azure_cli_runtime(
    *,
    package_root: Path,
    package_digest: str,
    interpreter_path: Path,
    interpreter_digest: str,
    allowed_uids: set[int],
) -> SealedAzureCliRuntime | None:
    """Bind executable bytes and a complete package manifest to sealed memfds."""

    manifest = _package_manifest(package_root, allowed_uids=allowed_uids)
    if manifest is None or manifest[0] != package_digest:
        return None
    tree_digest, payload = manifest
    payload["tree_digest"] = tree_digest

    interpreter = _read_regular_file(
        interpreter_path,
        allowed_uids={0},
        executable=True,
    )
    if (
        interpreter is None
        or hashlib.sha256(interpreter).hexdigest() != interpreter_digest
    ):
        return None

    descriptors: list[int] = []
    try:
        interpreter_fd = _sealed_memfd(
            "nac-azure-cli-python",
            interpreter,
            executable=True,
        )
        descriptors.append(interpreter_fd)
        bootstrap_fd = _sealed_memfd(
            "nac-azure-cli-bootstrap",
            _BOOTSTRAP_SOURCE.encode("utf-8"),
            executable=False,
        )
        descriptors.append(bootstrap_fd)
        manifest_fd = _sealed_memfd(
            "nac-azure-cli-manifest",
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            executable=False,
        )
        descriptors.append(manifest_fd)
    except (OSError, ValueError):
        for descriptor in descriptors:
            os.close(descriptor)
        return None
    return SealedAzureCliRuntime(
        interpreter_fd=interpreter_fd,
        bootstrap_fd=bootstrap_fd,
        manifest_fd=manifest_fd,
    )


def sealed_runtime_failure_code(returncode: int) -> str | None:
    if returncode == _TAMPER_EXIT:
        return "AZURE_CLI_RUNTIME_TAMPERED"
    if returncode == _ISOLATION_EXIT:
        return "AZURE_CLI_RUNTIME_ISOLATION_UNAVAILABLE"
    return None


def _package_manifest(
    root: Path,
    *,
    allowed_uids: set[int],
) -> tuple[str, dict[str, object]] | None:
    if not _trusted_directory(root, allowed_uids=allowed_uids):
        return None
    digest = hashlib.sha256()
    directories: list[dict[str, object]] = []
    files: list[dict[str, object]] = []
    snapshots: list[tuple[Path, tuple[int, ...]]] = []
    try:
        for current_text, child_directories, child_files in os.walk(
            root,
            topdown=True,
            followlinks=False,
        ):
            current = Path(current_text)
            current_metadata = current.lstat()
            if not _trusted_directory(current, allowed_uids=allowed_uids):
                return None
            snapshots.append((current, _stat_signature(current_metadata)))
            child_directories.sort()
            child_files.sort()
            for name in child_directories:
                child = current / name
                metadata = child.lstat()
                if not _trusted_directory(child, allowed_uids=allowed_uids):
                    return None
                relative = child.relative_to(root).as_posix()
                mode = stat.S_IMODE(metadata.st_mode)
                _digest_update(
                    digest,
                    "directory",
                    relative,
                    str(metadata.st_uid),
                    oct(mode),
                )
                directories.append(
                    {"path": relative, "mode": mode, "uid": metadata.st_uid}
                )
            for name in child_files:
                child = current / name
                metadata = child.lstat()
                content = _read_regular_file(child, allowed_uids=allowed_uids)
                if content is None:
                    return None
                relative = child.relative_to(root).as_posix()
                mode = stat.S_IMODE(metadata.st_mode)
                content_digest = hashlib.sha256(content).hexdigest()
                _digest_update(
                    digest,
                    "file",
                    relative,
                    str(metadata.st_uid),
                    oct(mode),
                    content_digest,
                )
                files.append(
                    {
                        "path": relative,
                        "mode": mode,
                        "uid": metadata.st_uid,
                        "size": len(content),
                        "sha256": content_digest,
                    }
                )
    except (OSError, RuntimeError, ValueError):
        return None
    for directory, signature in snapshots:
        try:
            if _stat_signature(directory.lstat()) != signature:
                return None
        except OSError:
            return None
    return digest.hexdigest(), {
        "schema": "nac-azure-cli-sealed-runtime-v1",
        "source_root": str(root),
        "directories": directories,
        "files": files,
    }


def _read_regular_file(
    path: Path,
    *,
    allowed_uids: set[int],
    executable: bool = False,
) -> bytes | None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        path_before = path.lstat()
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        before = os.fstat(descriptor)
        if (
            stat.S_ISLNK(path_before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_uid not in allowed_uids
            or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (executable and not before.st_mode & stat.S_IXUSR)
            or (before.st_dev, before.st_ino)
            != (path_before.st_dev, path_before.st_ino)
        ):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, _CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_after = path.lstat()
    except OSError:
        return None
    if (
        _stat_signature(before) != _stat_signature(after)
        or _stat_signature(after) != _stat_signature(path_after)
    ):
        return None
    return b"".join(chunks)


def _trusted_directory(path: Path, *, allowed_uids: set[int]) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISDIR(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and metadata.st_uid in allowed_uids
        and not metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    )


def _sealed_memfd(name: str, payload: bytes, *, executable: bool) -> int:
    if not hasattr(os, "memfd_create"):
        raise OSError("memfd unavailable")
    descriptor = os.memfd_create(
        name,
        getattr(os, "MFD_CLOEXEC", 0) | getattr(os, "MFD_ALLOW_SEALING", 0),
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short memfd write")
            view = view[written:]
        os.fchmod(descriptor, 0o500 if executable else 0o400)
        fcntl.fcntl(
            descriptor,
            fcntl.F_ADD_SEALS,
            fcntl.F_SEAL_WRITE
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_SEAL,
        )
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _stat_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _digest_update(digest: object, *values: str) -> None:
    for value in values:
        encoded = value.encode("utf-8", errors="surrogateescape")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)


_BOOTSTRAP_SOURCE = r'''from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import stat
import sys
import tempfile

TAMPER_EXIT = 86
ISOLATION_EXIT = 87
CHUNK_SIZE = 1024 * 1024

def fail(code):
    raise SystemExit(code)

def signature(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

def copy_verified(source, destination, record):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        path_before = source.lstat()
        descriptor = os.open(source, flags)
    except OSError:
        fail(TAMPER_EXIT)
    digest = hashlib.sha256()
    size = 0
    try:
        before = os.fstat(descriptor)
        if (stat.S_ISLNK(path_before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_uid != record["uid"] or stat.S_IMODE(before.st_mode) != record["mode"] or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH) or (before.st_dev, before.st_ino) != (path_before.st_dev, path_before.st_ino)):
            fail(TAMPER_EXIT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            while True:
                chunk = os.read(descriptor, CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_after = source.lstat()
    except OSError:
        fail(TAMPER_EXIT)
    if signature(before) != signature(after) or signature(after) != signature(path_after) or size != record["size"] or digest.hexdigest() != record["sha256"]:
        fail(TAMPER_EXIT)
    os.chmod(destination, record["mode"] & ~0o222)

def copy_config_file(source, destination):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        path_before = source.lstat()
        descriptor = os.open(source, flags)
    except OSError:
        fail(TAMPER_EXIT)
    try:
        before = os.fstat(descriptor)
        if (stat.S_ISLNK(path_before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_uid not in {0, os.getuid()} or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH) or (before.st_dev, before.st_ino) != (path_before.st_dev, path_before.st_ino)):
            fail(TAMPER_EXIT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            while True:
                chunk = os.read(descriptor, CHUNK_SIZE)
                if not chunk:
                    break
                output.write(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_after = source.lstat()
    except OSError:
        fail(TAMPER_EXIT)
    if signature(before) != signature(after) or signature(after) != signature(path_after):
        fail(TAMPER_EXIT)
    os.chmod(destination, stat.S_IMODE(before.st_mode) & ~0o022)

def copy_private_azure_config(source, destination):
    if not source.is_absolute():
        fail(TAMPER_EXIT)
    try:
        root = source.lstat()
    except FileNotFoundError:
        return
    except OSError:
        fail(TAMPER_EXIT)
    if stat.S_ISLNK(root.st_mode) or not stat.S_ISDIR(root.st_mode):
        fail(TAMPER_EXIT)
    for current_text, directories, files in os.walk(source, topdown=True, followlinks=False):
        current = Path(current_text)
        relative = current.relative_to(source)
        directories.sort()
        files.sort()
        for name in directories:
            metadata = (current / name).lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                fail(TAMPER_EXIT)
            (destination / relative / name).mkdir(parents=True, exist_ok=True)
        for name in files:
            if relative == Path(".") and name == "clouds.config":
                fail(TAMPER_EXIT)
            copy_config_file(current / name, destination / relative / name)

def validate_private_azure_profile(config_root):
    profile = config_root / "azureProfile.json"
    try:
        payload = json.loads(profile.read_text(encoding="utf-8"))
        subscriptions = payload["subscriptions"]
    except (OSError, KeyError, TypeError, ValueError):
        fail(TAMPER_EXIT)
    if not isinstance(subscriptions, list):
        fail(TAMPER_EXIT)
    exact = [
        row for row in subscriptions
        if isinstance(row, dict)
        and str(row.get("id", "")).lower()
            == "37cd9645-6cb9-4278-88ee-e80377cd951c"
    ]
    if (
        len(exact) != 1
        or str(exact[0].get("tenantId", "")).lower()
            != "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
        or exact[0].get("environmentName") != "AzureCloud"
        or exact[0].get("isDefault") is not True
    ):
        fail(TAMPER_EXIT)

def isolate():
    libc = ctypes.CDLL(None, use_errno=True)
    clone_newns = 0x00020000
    clone_newuser = 0x10000000
    uid = os.getuid()
    gid = os.getgid()
    if libc.unshare(clone_newuser) != 0:
        fail(ISOLATION_EXIT)
    try:
        Path("/proc/self/setgroups").write_text("deny", encoding="ascii")
    except OSError:
        pass
    try:
        Path("/proc/self/uid_map").write_text(f"0 {uid} 1\n", encoding="ascii")
        Path("/proc/self/gid_map").write_text(f"0 {gid} 1\n", encoding="ascii")
    except OSError:
        fail(ISOLATION_EXIT)
    if libc.unshare(clone_newns) != 0:
        fail(ISOLATION_EXIT)
    ms_rec = 16384
    ms_private = 1 << 18
    if libc.mount(None, b"/", None, ms_rec | ms_private, None) != 0:
        fail(ISOLATION_EXIT)
    mountpoint = Path(tempfile.mkdtemp(prefix="nac-azure-cli-sealed-"))
    if libc.mount(b"tmpfs", os.fsencode(mountpoint), b"tmpfs", 0, b"mode=0700") != 0:
        fail(ISOLATION_EXIT)
    config_mountpoint = Path(tempfile.mkdtemp(prefix="nac-azure-cli-config-"))
    if libc.mount(b"tmpfs", os.fsencode(config_mountpoint), b"tmpfs", 0, b"mode=0700") != 0:
        fail(ISOLATION_EXIT)
    return mountpoint, config_mountpoint, libc

def main():
    if len(sys.argv) < 2:
        fail(TAMPER_EXIT)
    try:
        manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        fail(TAMPER_EXIT)
    if manifest.get("schema") != "nac-azure-cli-sealed-runtime-v1":
        fail(TAMPER_EXIT)
    verify_only = len(sys.argv) >= 4 and sys.argv[2] == "--nac-internal-verify-only"
    if verify_only:
        destination = Path(sys.argv[3])
        azure_argv = []
        libc = None
        private_config = None
    else:
        try:
            source_config = Path(os.environ.get("AZURE_CONFIG_DIR") or (Path(os.environ["HOME"]) / ".azure"))
        except (KeyError, TypeError, ValueError):
            fail(TAMPER_EXIT)
        destination, private_config, libc = isolate()
        copy_private_azure_config(source_config, private_config)
        validate_private_azure_profile(private_config)
        azure_argv = sys.argv[2:]
    source_root = Path(manifest["source_root"])
    try:
        for record in manifest["directories"]:
            target = destination / record["path"]
            target.mkdir(parents=True, exist_ok=True)
        for record in manifest["files"]:
            copy_verified(source_root / record["path"], destination / record["path"], record)
        extension_root = destination / ".nac-empty-extensions"
        extension_root.mkdir(mode=0o500)
        for record in reversed(manifest["directories"]):
            os.chmod(destination / record["path"], record["mode"] & ~0o222)
    except (KeyError, OSError, TypeError, ValueError):
        fail(TAMPER_EXIT)
    if verify_only:
        return
    ms_remount = 32
    ms_rdonly = 1
    if libc.mount(None, os.fsencode(destination), None, ms_remount | ms_rdonly, None) != 0:
        fail(ISOLATION_EXIT)
    import sysconfig
    stdlib = Path(sysconfig.get_path("stdlib"))
    platstdlib = Path(sysconfig.get_path("platstdlib"))
    trusted_paths = [destination, stdlib, platstdlib]
    for root in (stdlib, platstdlib):
        dynload = root / "lib-dynload"
        if dynload not in trusted_paths:
            trusted_paths.append(dynload)
    sys.path[:] = [str(path) for path in trusted_paths]
    # Override both user-configured and system extension roots with one empty,
    # read-only directory inside the isolated mount. Empty dev_sources masks any
    # mutable config-file value; dynamic installation is disabled explicitly.
    extension_root = destination / ".nac-empty-extensions"
    os.environ["AZURE_EXTENSION_DIR"] = str(extension_root)
    os.environ["AZURE_EXTENSION_SYS_DIR"] = str(extension_root)
    os.environ["AZURE_EXTENSION_DEV_SOURCES"] = ""
    os.environ["AZURE_EXTENSION_USE_DYNAMIC_INSTALL"] = "no"
    os.environ["AZURE_CONFIG_DIR"] = str(private_config)
    sys.argv = ["az", *azure_argv]
    runpy.run_module("azure.cli", run_name="__main__")

main()
'''
