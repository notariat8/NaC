from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat


MANIFEST_ENV = "NAC_NODE_RUNTIME_MANIFEST"
MANIFEST_SCHEMA = "nac-node-runtime-integrity-manifest-v1"
_DIGEST_DOMAIN = b"nac-node-runtime-tree-v1\0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_READ_CHUNK_SIZE = 1024 * 1024
_MAX_FILE_BYTES = 512 * 1024 * 1024
_MAX_TREE_BYTES = 4 * 1024 * 1024 * 1024
_MAX_FILE_COUNT = 200_000
_UNTRUSTED_WRITE_BITS = stat.S_IWGRP | stat.S_IWOTH
_SPECIAL_MODE_BITS = stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX


class NodeRuntimeIntegrityError(RuntimeError):
    """Raised when a Node runtime tree cannot be trusted or verified."""


@dataclass(frozen=True, slots=True)
class NodeRuntimeFile:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class NodeRuntimeManifest:
    root: Path
    files: tuple[NodeRuntimeFile, ...]
    digest: str

    def payload_bytes(self) -> bytes:
        payload = {
            "digest": self.digest,
            "files": {
                item.relative_path: item.sha256
                for item in self.files
            },
            "root": str(self.root),
            "schema": MANIFEST_SCHEMA,
        }
        return (
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )


@dataclass(frozen=True, slots=True)
class NodeRuntimeIntegrityPayloads:
    digest: str
    manifest: bytes
    commonjs_preloader: bytes
    esm_loader: bytes


def build_node_runtime_manifest(root: Path) -> NodeRuntimeManifest:
    """Scan a stable trusted tree and return its path-independent manifest."""

    runtime_root = _normalized_absolute_root(root)
    root_fd = _open_trusted_root(runtime_root)
    files: list[NodeRuntimeFile] = []
    counters = [0, 0]
    try:
        root_before = os.fstat(root_fd)
        _scan_directory(root_fd, (), files, counters)
        root_after = os.fstat(root_fd)
        if _stat_snapshot(root_before) != _stat_snapshot(root_after):
            _fail("NODE_RUNTIME_TREE_CHANGED")
    finally:
        os.close(root_fd)

    ordered = tuple(
        sorted(files, key=lambda item: item.relative_path.encode("utf-8"))
    )
    return NodeRuntimeManifest(
        root=runtime_root,
        files=ordered,
        digest=_tree_digest(ordered),
    )


def verify_node_runtime_manifest(
    root: Path,
    *,
    expected_digest: str,
) -> NodeRuntimeManifest:
    """Build a manifest and fail closed unless its full-tree digest matches."""

    if not isinstance(expected_digest, str) or not _SHA256_RE.fullmatch(
        expected_digest
    ):
        _fail("NODE_RUNTIME_EXPECTED_DIGEST_INVALID")
    manifest = build_node_runtime_manifest(root)
    if not hmac.compare_digest(manifest.digest, expected_digest):
        _fail("NODE_RUNTIME_DIGEST_MISMATCH")
    return manifest


def build_node_runtime_integrity_payloads(
    root: Path,
    *,
    expected_digest: str,
) -> NodeRuntimeIntegrityPayloads:
    """Return manifest and loader bytes suitable for separate sealed memfds."""

    manifest = verify_node_runtime_manifest(
        root,
        expected_digest=expected_digest,
    )
    manifest_payload = manifest.payload_bytes()
    manifest_sha256 = hashlib.sha256(manifest_payload).hexdigest()
    return NodeRuntimeIntegrityPayloads(
        digest=manifest.digest,
        manifest=manifest_payload,
        commonjs_preloader=_commonjs_preloader_payload(
            expected_digest=manifest.digest,
            expected_manifest_sha256=manifest_sha256,
        ),
        esm_loader=_esm_loader_payload(
            expected_digest=manifest.digest,
            expected_manifest_sha256=manifest_sha256,
        ),
    )


def _normalized_absolute_root(root: Path) -> Path:
    try:
        candidate = Path(root)
    except TypeError as exc:
        raise NodeRuntimeIntegrityError("NODE_RUNTIME_ROOT_INVALID") from exc
    if (
        not candidate.is_absolute()
        or candidate == Path(candidate.anchor)
        or candidate != Path(os.path.abspath(candidate))
    ):
        _fail("NODE_RUNTIME_ROOT_INVALID")
    try:
        str(candidate).encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise NodeRuntimeIntegrityError("NODE_RUNTIME_PATH_INVALID") from exc
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        _fail("NODE_RUNTIME_PLATFORM_UNSUPPORTED")
    return candidate


def _open_trusted_root(root: Path) -> int:
    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    current = -1
    try:
        current = os.open(root.anchor, flags)
        parts = root.parts[1:]
        for index, component in enumerate(parts):
            metadata = os.stat(
                component,
                dir_fd=current,
                follow_symlinks=False,
            )
            is_root = index == len(parts) - 1
            if not _trusted_directory(metadata, allow_sticky_ancestor=not is_root):
                _fail("NODE_RUNTIME_ROOT_UNTRUSTED")
            opened = os.open(component, flags, dir_fd=current)
            opened_metadata = os.fstat(opened)
            if _stat_snapshot(metadata) != _stat_snapshot(opened_metadata):
                os.close(opened)
                _fail("NODE_RUNTIME_ROOT_CHANGED")
            os.close(current)
            current = opened
        result = current
        current = -1
        return result
    except NodeRuntimeIntegrityError:
        raise
    except (OSError, ValueError) as exc:
        raise NodeRuntimeIntegrityError("NODE_RUNTIME_ROOT_UNAVAILABLE") from exc
    finally:
        if current >= 0:
            os.close(current)


def _scan_directory(
    directory_fd: int,
    relative_parts: tuple[str, ...],
    files: list[NodeRuntimeFile],
    counters: list[int],
) -> None:
    before = os.fstat(directory_fd)
    if not _trusted_directory(before, allow_sticky_ancestor=False):
        _fail("NODE_RUNTIME_DIRECTORY_UNTRUSTED")
    try:
        names_before = _directory_names(directory_fd)
        for name in names_before:
            metadata = os.stat(
                name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
            parts = (*relative_parts, name)
            relative_path = "/".join(parts)
            if stat.S_ISLNK(metadata.st_mode):
                _fail("NODE_RUNTIME_SYMLINK_REJECTED")
            if stat.S_ISDIR(metadata.st_mode):
                if name == ".bin":
                    _verify_excluded_directory(directory_fd, name, metadata)
                    continue
                _scan_child_directory(
                    directory_fd,
                    name,
                    metadata,
                    parts,
                    files,
                    counters,
                )
                continue
            if not stat.S_ISREG(metadata.st_mode):
                _fail("NODE_RUNTIME_ENTRY_UNTRUSTED")
            if relative_path.lower().endswith(".node"):
                _fail("NODE_RUNTIME_NATIVE_ADDON_REJECTED")
            files.append(
                _read_file(
                    directory_fd,
                    name,
                    relative_path,
                    metadata,
                    counters,
                )
            )
        if names_before != _directory_names(directory_fd):
            _fail("NODE_RUNTIME_TREE_CHANGED")
        after = os.fstat(directory_fd)
        if _stat_snapshot(before) != _stat_snapshot(after):
            _fail("NODE_RUNTIME_TREE_CHANGED")
    except NodeRuntimeIntegrityError:
        raise
    except (OSError, ValueError) as exc:
        raise NodeRuntimeIntegrityError("NODE_RUNTIME_SCAN_FAILED") from exc


def _scan_child_directory(
    parent_fd: int,
    name: str,
    metadata: os.stat_result,
    relative_parts: tuple[str, ...],
    files: list[NodeRuntimeFile],
    counters: list[int],
) -> None:
    if not _trusted_directory(metadata, allow_sticky_ancestor=False):
        _fail("NODE_RUNTIME_DIRECTORY_UNTRUSTED")
    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    child_fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        opened = os.fstat(child_fd)
        if _stat_snapshot(metadata) != _stat_snapshot(opened):
            _fail("NODE_RUNTIME_TREE_CHANGED")
        _scan_directory(child_fd, relative_parts, files, counters)
        final = os.fstat(child_fd)
        named_final = os.stat(
            name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (
            _stat_snapshot(opened) != _stat_snapshot(final)
            or _stat_snapshot(final) != _stat_snapshot(named_final)
        ):
            _fail("NODE_RUNTIME_TREE_CHANGED")
    finally:
        os.close(child_fd)


def _verify_excluded_directory(
    parent_fd: int,
    name: str,
    metadata: os.stat_result,
) -> None:
    if not _trusted_directory(metadata, allow_sticky_ancestor=False):
        _fail("NODE_RUNTIME_DIRECTORY_UNTRUSTED")
    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(name, flags, dir_fd=parent_fd)
    try:
        opened = os.fstat(descriptor)
        named_final = os.stat(
            name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (
            _stat_snapshot(metadata) != _stat_snapshot(opened)
            or _stat_snapshot(opened) != _stat_snapshot(named_final)
        ):
            _fail("NODE_RUNTIME_TREE_CHANGED")
    finally:
        os.close(descriptor)


def _read_file(
    parent_fd: int,
    name: str,
    relative_path: str,
    metadata: os.stat_result,
    counters: list[int],
) -> NodeRuntimeFile:
    if not _trusted_file(metadata):
        _fail("NODE_RUNTIME_FILE_UNTRUSTED")
    if metadata.st_size > _MAX_FILE_BYTES:
        _fail("NODE_RUNTIME_TREE_LIMIT_EXCEEDED")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=parent_fd,
    )
    try:
        opened = os.fstat(descriptor)
        if (
            _stat_snapshot(metadata) != _stat_snapshot(opened)
            or not _trusted_file(opened)
        ):
            _fail("NODE_RUNTIME_TREE_CHANGED")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, _READ_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_FILE_BYTES:
                _fail("NODE_RUNTIME_TREE_LIMIT_EXCEEDED")
            digest.update(chunk)
        final = os.fstat(descriptor)
        named_final = os.stat(
            name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (
            total != opened.st_size
            or _stat_snapshot(opened) != _stat_snapshot(final)
            or _stat_snapshot(final) != _stat_snapshot(named_final)
        ):
            _fail("NODE_RUNTIME_TREE_CHANGED")
    finally:
        os.close(descriptor)

    counters[0] += 1
    counters[1] += total
    if counters[0] > _MAX_FILE_COUNT or counters[1] > _MAX_TREE_BYTES:
        _fail("NODE_RUNTIME_TREE_LIMIT_EXCEEDED")
    return NodeRuntimeFile(relative_path, digest.hexdigest(), total)


def _directory_names(directory_fd: int) -> tuple[str, ...]:
    names = os.listdir(directory_fd)
    for name in names:
        if name in {"", ".", ".."} or "/" in name or "\\" in name:
            _fail("NODE_RUNTIME_PATH_INVALID")
        try:
            name.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise NodeRuntimeIntegrityError("NODE_RUNTIME_PATH_INVALID") from exc
    return tuple(sorted(names, key=lambda item: item.encode("utf-8")))


def _trusted_directory(
    metadata: os.stat_result,
    *,
    allow_sticky_ancestor: bool,
) -> bool:
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid not in {
        0,
        os.geteuid(),
    }:
        return False
    if metadata.st_mode & _SPECIAL_MODE_BITS:
        return bool(
            allow_sticky_ancestor
            and metadata.st_uid == 0
            and metadata.st_mode & stat.S_ISVTX
            and not metadata.st_mode & (stat.S_ISUID | stat.S_ISGID)
        )
    return not metadata.st_mode & _UNTRUSTED_WRITE_BITS


def _trusted_file(metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid in {0, os.geteuid()}
        and not metadata.st_mode & _UNTRUSTED_WRITE_BITS
        and not metadata.st_mode & _SPECIAL_MODE_BITS
        and metadata.st_size >= 0
    )


def _stat_snapshot(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _tree_digest(files: tuple[NodeRuntimeFile, ...]) -> str:
    digest = hashlib.sha256(_DIGEST_DOMAIN)
    for item in files:
        path_bytes = item.relative_path.encode("utf-8")
        digest.update(len(path_bytes).to_bytes(8, "big"))
        digest.update(path_bytes)
        digest.update(bytes.fromhex(item.sha256))
    return digest.hexdigest()


def _fail(code: str) -> None:
    raise NodeRuntimeIntegrityError(code)


def _loader_prelude(
    *,
    expected_digest: str,
    expected_manifest_sha256: str,
    esm: bool,
) -> str:
    if not _SHA256_RE.fullmatch(expected_digest) or not _SHA256_RE.fullmatch(
        expected_manifest_sha256
    ):
        _fail("NODE_RUNTIME_EXPECTED_DIGEST_INVALID")
    imports = (
        "import fs from 'node:fs';\n"
        "import path from 'node:path';\n"
        "import crypto from 'node:crypto';\n"
        "import { fileURLToPath } from 'node:url';\n"
        if esm
        else
        "const fs = require('node:fs');\n"
        "const path = require('node:path');\n"
        "const crypto = require('node:crypto');\n"
    )
    return imports + f"""
const EXPECTED_TREE_DIGEST = {json.dumps(expected_digest)};
const EXPECTED_MANIFEST_SHA256 = {json.dumps(expected_manifest_sha256)};
const MANIFEST_SCHEMA = {json.dumps(MANIFEST_SCHEMA)};
const MANIFEST_ENV = {json.dumps(MANIFEST_ENV)};
const DIGEST_DOMAIN = Buffer.from('nac-node-runtime-tree-v1\\0', 'utf8');
const SHA256_RE = /^[0-9a-f]{{64}}$/;
const REGULAR_FILE = 0o100000n;
const FILE_TYPE_MASK = 0o170000n;
const UNTRUSTED_WRITE_BITS = 0o22n;
const SPECIAL_MODE_BITS = 0o7000n;
const MAX_FILE_BYTES = {int(_MAX_FILE_BYTES)}n;

function integrityError(code) {{
  const error = new Error(code);
  error.code = code;
  return error;
}}

function sameStat(left, right) {{
  return left.dev === right.dev &&
    left.ino === right.ino &&
    left.mode === right.mode &&
    left.uid === right.uid &&
    left.gid === right.gid &&
    left.nlink === right.nlink &&
    left.size === right.size &&
    left.mtimeNs === right.mtimeNs &&
    left.ctimeNs === right.ctimeNs;
}}

function trustedFile(metadata) {{
  const effectiveUid = typeof process.geteuid === 'function'
    ? BigInt(process.geteuid())
    : -1n;
  return (metadata.mode & FILE_TYPE_MASK) === REGULAR_FILE &&
    (metadata.uid === 0n || metadata.uid === effectiveUid) &&
    (metadata.mode & UNTRUSTED_WRITE_BITS) === 0n &&
    (metadata.mode & SPECIAL_MODE_BITS) === 0n &&
    metadata.size >= 0n && metadata.size <= MAX_FILE_BYTES;
}}

function treeDigest(entries) {{
  const hash = crypto.createHash('sha256');
  hash.update(DIGEST_DOMAIN);
  entries.sort((left, right) => Buffer.compare(
    Buffer.from(left[0], 'utf8'), Buffer.from(right[0], 'utf8')));
  for (const [relative, digest] of entries) {{
    const relativeBytes = Buffer.from(relative, 'utf8');
    const length = Buffer.alloc(8);
    length.writeBigUInt64BE(BigInt(relativeBytes.length));
    hash.update(length);
    hash.update(relativeBytes);
    hash.update(Buffer.from(digest, 'hex'));
  }}
  return hash.digest('hex');
}}

function loadManifest() {{
  const manifestPath = process.env[MANIFEST_ENV];
  if (!manifestPath || !path.isAbsolute(manifestPath)) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_PATH_INVALID');
  }}
  const payload = fs.readFileSync(manifestPath);
  if (crypto.createHash('sha256').update(payload).digest('hex') !==
      EXPECTED_MANIFEST_SHA256) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_SHA256_MISMATCH');
  }}
  let parsed;
  try {{
    parsed = JSON.parse(payload.toString('utf8'));
  }} catch {{
    throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
  }}
  if (!parsed || Array.isArray(parsed) ||
      Object.keys(parsed).sort().join(',') !== 'digest,files,root,schema' ||
      parsed.schema !== MANIFEST_SCHEMA ||
      parsed.digest !== EXPECTED_TREE_DIGEST ||
      !path.isAbsolute(parsed.root) || path.resolve(parsed.root) !== parsed.root ||
      parsed.root === path.parse(parsed.root).root ||
      !parsed.files || Array.isArray(parsed.files) ||
      Object.getPrototypeOf(parsed.files) !== Object.prototype) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
  }}
  const entries = Object.entries(parsed.files);
  const allowed = new Map();
  for (const [relative, digest] of entries) {{
    const parts = relative.split('/');
    if (!relative || relative.includes('\\\\') || path.isAbsolute(relative) ||
        parts.some((part) => !part || part === '.' || part === '..') ||
        typeof digest !== 'string' || !SHA256_RE.test(digest) ||
        Buffer.from(relative, 'utf8').toString('utf8') !== relative) {{
      throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
    }}
    const absolute = path.resolve(parsed.root, ...parts);
    if (!absolute.startsWith(parsed.root + path.sep) || allowed.has(absolute)) {{
      throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
    }}
    allowed.set(absolute, digest);
  }}
  if (treeDigest(entries) !== EXPECTED_TREE_DIGEST) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_DIGEST_MISMATCH');
  }}
  return Object.freeze({{ root: parsed.root, allowed }});
}}

const runtimeManifest = loadManifest();

function assertAllowed(filename) {{
  if (typeof filename !== 'string' || path.resolve(filename) !== filename ||
      !runtimeManifest.allowed.has(filename)) {{
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }}
  if (filename.toLowerCase().endsWith('.node')) {{
    throw integrityError('NODE_RUNTIME_NATIVE_ADDON_REJECTED');
  }}
  return runtimeManifest.allowed.get(filename);
}}

function trustedRead(filename) {{
  const expected = assertAllowed(filename);
  if (!Number.isInteger(fs.constants.O_NOFOLLOW) ||
      !fs.existsSync('/proc/self/fd')) {{
    throw integrityError('NODE_RUNTIME_PLATFORM_UNSUPPORTED');
  }}
  let descriptor;
  try {{
    descriptor = fs.openSync(
      filename,
      fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_CLOEXEC
    );
    const before = fs.fstatSync(descriptor, {{ bigint: true }});
    const namedBefore = fs.lstatSync(filename, {{ bigint: true }});
    const openedPath = fs.readlinkSync(`/proc/self/fd/${{descriptor}}`);
    if (!trustedFile(before) || !sameStat(before, namedBefore) ||
        openedPath !== filename) {{
      throw integrityError('NODE_RUNTIME_MODULE_UNTRUSTED');
    }}
    const source = Buffer.alloc(Number(before.size));
    let offset = 0;
    while (offset < source.length) {{
      const count = fs.readSync(
        descriptor, source, offset, source.length - offset, offset
      );
      if (count <= 0) {{
        throw integrityError('NODE_RUNTIME_MODULE_CHANGED');
      }}
      offset += count;
    }}
    const after = fs.fstatSync(descriptor, {{ bigint: true }});
    const namedAfter = fs.lstatSync(filename, {{ bigint: true }});
    if (!sameStat(before, after) || !sameStat(after, namedAfter)) {{
      throw integrityError('NODE_RUNTIME_MODULE_CHANGED');
    }}
    if (crypto.createHash('sha256').update(source).digest('hex') !== expected) {{
      throw integrityError('NODE_RUNTIME_MODULE_SHA256_MISMATCH');
    }}
    return source;
  }} catch (error) {{
    if (error && typeof error.code === 'string' &&
        error.code.startsWith('NODE_RUNTIME_')) {{
      throw error;
    }}
    throw integrityError('NODE_RUNTIME_MODULE_READ_FAILED');
  }} finally {{
    if (descriptor !== undefined) {{
      try {{ fs.closeSync(descriptor); }} catch {{}}
    }}
  }}
}}
"""


def _commonjs_preloader_payload(
    *,
    expected_digest: str,
    expected_manifest_sha256: str,
) -> bytes:
    source = _loader_prelude(
        expected_digest=expected_digest,
        expected_manifest_sha256=expected_manifest_sha256,
        esm=False,
    )
    source += r"""
const Module = require('node:module');
const builtinModules = new Set();
for (const name of Module.builtinModules) {
  builtinModules.add(name);
  builtinModules.add(name.startsWith('node:') ? name.slice(5) : `node:${name}`);
}
const originalLoad = Module._load;
const originalResolveFilename = Module._resolveFilename;

Module._load = function integrityLoad(request, parent, isMain) {
  if (typeof request === 'string' && builtinModules.has(request)) {
    return originalLoad.call(this, request, parent, isMain);
  }
  const resolved = originalResolveFilename.call(this, request, parent, isMain);
  if (typeof resolved === 'string' && builtinModules.has(resolved)) {
    return originalLoad.call(this, request, parent, isMain);
  }
  assertAllowed(resolved);
  return originalLoad.call(this, request, parent, isMain);
};

function compileJavaScript(module, filename) {
  module._compile(trustedRead(filename).toString('utf8'), filename);
}

Module._extensions['.js'] = compileJavaScript;
Module._extensions['.cjs'] = compileJavaScript;
Module._extensions['.json'] = function integrityJson(module, filename) {
  let source = trustedRead(filename).toString('utf8');
  if (source.charCodeAt(0) === 0xFEFF) source = source.slice(1);
  module.exports = JSON.parse(source);
};
Module._extensions['.node'] = function rejectNativeAddon() {
  throw integrityError('NODE_RUNTIME_NATIVE_ADDON_REJECTED');
};
"""
    return source.encode("utf-8")


def _esm_loader_payload(
    *,
    expected_digest: str,
    expected_manifest_sha256: str,
) -> bytes:
    source = _loader_prelude(
        expected_digest=expected_digest,
        expected_manifest_sha256=expected_manifest_sha256,
        esm=True,
    )
    source += r"""
export async function resolve(specifier, context, nextResolve) {
  const resolved = await nextResolve(specifier, context);
  if (resolved.url.startsWith('node:')) return resolved;
  if (!resolved.url.startsWith('file:')) {
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }
  assertAllowed(fileURLToPath(resolved.url));
  return resolved;
}

export async function load(url, context, nextLoad) {
  if (url.startsWith('node:')) return nextLoad(url, context);
  if (!url.startsWith('file:')) {
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }
  const filename = fileURLToPath(url);
  assertAllowed(filename);
  const loaded = await nextLoad(url, context);
  if (loaded.format === 'commonjs') {
    return loaded;
  }
  if (loaded.format === 'module' || loaded.format === 'json') {
    return { ...loaded, source: trustedRead(filename), shortCircuit: true };
  }
  throw integrityError('NODE_RUNTIME_MODULE_FORMAT_REJECTED');
}
"""
    return source.encode("utf-8")
