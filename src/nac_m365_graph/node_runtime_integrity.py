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


def build_node_runtime_manifest(
    root: Path,
    *,
    excluded_top_level_directories: frozenset[str] = frozenset(),
) -> NodeRuntimeManifest:
    """Scan a stable trusted input tree and return its manifest."""

    runtime_root = _normalized_absolute_root(root)
    excluded = _normalized_excluded_directories(excluded_top_level_directories)
    root_fd = _open_trusted_root(runtime_root)
    files: list[NodeRuntimeFile] = []
    counters = [0, 0]
    try:
        root_before = os.fstat(root_fd)
        _scan_directory(root_fd, (), files, counters, excluded)
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
    excluded_top_level_directories: frozenset[str] = frozenset(),
) -> NodeRuntimeManifest:
    """Build a manifest and fail closed unless its full-tree digest matches."""

    if not isinstance(expected_digest, str) or not _SHA256_RE.fullmatch(
        expected_digest
    ):
        _fail("NODE_RUNTIME_EXPECTED_DIGEST_INVALID")
    manifest = build_node_runtime_manifest(
        root,
        excluded_top_level_directories=excluded_top_level_directories,
    )
    if not hmac.compare_digest(manifest.digest, expected_digest):
        _fail("NODE_RUNTIME_DIGEST_MISMATCH")
    return manifest


def build_node_runtime_integrity_payloads(
    root: Path,
    *,
    expected_digest: str,
    excluded_top_level_directories: frozenset[str] = frozenset(),
) -> NodeRuntimeIntegrityPayloads:
    """Return manifest and loader bytes suitable for separate sealed memfds."""

    manifest = verify_node_runtime_manifest(
        root,
        expected_digest=expected_digest,
        excluded_top_level_directories=excluded_top_level_directories,
    )
    manifest_payload = manifest.payload_bytes()
    manifest_sha256 = hashlib.sha256(manifest_payload).hexdigest()
    return NodeRuntimeIntegrityPayloads(
        digest=manifest.digest,
        manifest=manifest_payload,
        commonjs_preloader=_commonjs_preloader_payload(
            expected_digest=manifest.digest,
            expected_manifest_sha256=manifest_sha256,
            generated_top_level_directories=excluded_top_level_directories,
        ),
        esm_loader=_esm_loader_payload(
            expected_digest=manifest.digest,
            expected_manifest_sha256=manifest_sha256,
            generated_top_level_directories=excluded_top_level_directories,
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


def _normalized_excluded_directories(values: frozenset[str]) -> frozenset[str]:
    if not isinstance(values, frozenset):
        _fail("NODE_RUNTIME_EXCLUSION_INVALID")
    for value in values:
        if (
            not isinstance(value, str)
            or not value
            or value in {".", "..", ".bin"}
            or "/" in value
            or "\\" in value
        ):
            _fail("NODE_RUNTIME_EXCLUSION_INVALID")
    return values


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
    excluded_top_level_directories: frozenset[str],
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
                if not relative_parts and name in excluded_top_level_directories:
                    _verify_excluded_directory(directory_fd, name, metadata)
                    continue
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
                    excluded_top_level_directories,
                )
                continue
            if not stat.S_ISREG(metadata.st_mode):
                _fail("NODE_RUNTIME_ENTRY_UNTRUSTED")
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
    excluded_top_level_directories: frozenset[str],
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
        _scan_directory(
            child_fd,
            relative_parts,
            files,
            counters,
            excluded_top_level_directories,
        )
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
    generated_top_level_directories: frozenset[str],
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
        "import { Readable } from 'node:stream';\n"
        "import util from 'node:util';\n"
        "import { isMainThread as NAC_IS_MAIN_THREAD, workerData as NAC_WORKER_DATA } from 'node:worker_threads';\n"
        if esm
        else
        "const fs = require('node:fs');\n"
        "const path = require('node:path');\n"
        "const crypto = require('node:crypto');\n"
        "const { fileURLToPath } = require('node:url');\n"
        "const { Readable } = require('node:stream');\n"
        "const util = require('node:util');\n"
        "const { isMainThread: NAC_IS_MAIN_THREAD, workerData: NAC_WORKER_DATA } = require('node:worker_threads');\n"
    )
    return imports + f"""
const NAC_INTERNAL_ESM_LOADER_THREAD = !NAC_IS_MAIN_THREAD &&
  NAC_WORKER_DATA === null && process.argv.length === 1;
const EXPECTED_TREE_DIGEST = {json.dumps(expected_digest)};
const LOADER_IS_ESM = {json.dumps(esm)};
const EXPECTED_MANIFEST_SHA256 = {json.dumps(expected_manifest_sha256)};
const MANIFEST_SCHEMA = {json.dumps(MANIFEST_SCHEMA)};
const MANIFEST_ENV = {json.dumps(MANIFEST_ENV)};
const GENERATED_TOP_LEVEL_DIRECTORIES = new Set(
  {json.dumps(sorted(generated_top_level_directories))}
);
const DIGEST_DOMAIN = Buffer.from('nac-node-runtime-tree-v1\\0', 'utf8');
const SHA256_RE = /^[0-9a-f]{{64}}$/;
const REGULAR_FILE = 0o100000n;
const FILE_TYPE_MASK = 0o170000n;
const UNTRUSTED_WRITE_BITS = 0o22n;
const SPECIAL_MODE_BITS = 0o7000n;
const MAX_FILE_BYTES = {int(_MAX_FILE_BYTES)}n;

const primitiveOpenSync = fs.openSync.bind(fs);
const primitiveReadSync = fs.readSync.bind(fs);
const primitiveWriteSync = fs.writeSync.bind(fs);
const primitiveFsyncSync = fs.fsyncSync.bind(fs);
const primitiveRenameSync = fs.renameSync.bind(fs);
const primitiveUnlinkSync = fs.unlinkSync.bind(fs);
const primitiveCloseSync = fs.closeSync.bind(fs);
const primitiveReadFileSync = fs.readFileSync.bind(fs);
const primitiveFstatSync = fs.fstatSync.bind(fs);
const primitiveLstatSync = fs.lstatSync.bind(fs);
const primitiveReadlinkSync = fs.readlinkSync.bind(fs);
const primitiveExistsSync = fs.existsSync.bind(fs);
const primitiveCreateHash = crypto.createHash.bind(crypto);
const primitiveReflectApply = Reflect.apply.bind(Reflect);
const primitiveReflectDeleteProperty = Reflect.deleteProperty.bind(Reflect);
const primitiveReflectOwnKeys = Reflect.ownKeys.bind(Reflect);
const primitiveObjectCreate = Object.create.bind(Object);
const primitiveObjectDefineProperty = Object.defineProperty.bind(Object);
const primitiveObjectEntries = Object.entries.bind(Object);
const primitiveObjectFreeze = Object.freeze.bind(Object);
const primitiveObjectGetOwnPropertyDescriptor =
  Object.getOwnPropertyDescriptor.bind(Object);
const primitiveObjectGetOwnPropertyDescriptors =
  Object.getOwnPropertyDescriptors.bind(Object);
const primitiveObjectGetPrototypeOf = Object.getPrototypeOf.bind(Object);
const primitiveObjectKeys = Object.keys.bind(Object);
const primitiveArrayFrom = Array.from.bind(Array);
const primitiveArrayIsArray = Array.isArray.bind(Array);
const primitiveArrayFilter = Array.prototype.filter;
const primitiveArraySome = Array.prototype.some;
const primitiveBufferAlloc = Buffer.alloc.bind(Buffer);
const primitiveBufferCompare = Buffer.compare.bind(Buffer);
const primitiveBufferFrom = Buffer.from.bind(Buffer);
const primitiveBufferIsBuffer = Buffer.isBuffer.bind(Buffer);
const primitiveBufferToString = Buffer.prototype.toString;
const primitiveJsonParse = JSON.parse.bind(JSON);
const primitiveMapDelete = Map.prototype.delete;
const primitiveMapGet = Map.prototype.get;
const primitiveMapHas = Map.prototype.has;
const primitiveMapSet = Map.prototype.set;
const primitiveSetAdd = Set.prototype.add;
const primitiveSetDelete = Set.prototype.delete;
const primitiveSetHas = Set.prototype.has;
const primitiveSetValues = Set.prototype.values;
const primitiveSetIteratorNext = primitiveObjectGetPrototypeOf(
  primitiveReflectApply(primitiveSetValues, new Set(), [])
).next;
const primitiveStringCharCodeAt = String.prototype.charCodeAt;
const primitiveStringEndsWith = String.prototype.endsWith;
const primitiveStringSlice = String.prototype.slice;
const PrimitiveBlob = globalThis.Blob;
const PrimitiveMap = Map;
const PrimitiveSet = Set;
for (const primordial of [
  Array.prototype,
  Buffer.prototype,
  Number,
  RegExp.prototype,
  String.prototype,
]) {{
  primitiveObjectFreeze(primordial);
}}
const primitiveHashPrototype = primitiveObjectGetPrototypeOf(
  primitiveCreateHash('sha256')
);
const primitiveHashUpdate = primitiveHashPrototype.update;
const primitiveHashDigest = primitiveHashPrototype.digest;
const primitivePathResolve = path.resolve.bind(path);
const primitivePathIsAbsolute = path.isAbsolute.bind(path);
const primitivePathParse = path.parse.bind(path);
const primitivePathRelative = path.relative.bind(path);
const primitivePathDirname = path.dirname.bind(path);
const primitivePathJoin = path.join.bind(path);
const primitivePathExtname = path.extname.bind(path);
const primitivePathRealpath = fs.realpathSync.bind(fs);
const primitiveGetCallSites = util.getCallSites.bind(util);
const primitiveNextTick = process.nextTick.bind(process);
const primitiveReadableAddListener = Readable.prototype.addListener;
const primitiveReadableEmit = Readable.prototype.emit;
const primitiveReadableFrom = Readable.from.bind(Readable);
const primitiveReadableOn = Readable.prototype.on;
const primitiveReadableOnce = Readable.prototype.once;
const primitiveReadablePush = Readable.prototype.push;
const primitiveReadableSetEncoding = Readable.prototype.setEncoding;
const PATH_SEPARATOR = path.sep;

function integrityError(code) {{
  const error = new Error(code);
  error.code = code;
  return error;
}}

function bufferToString(buffer, encoding) {{
  return primitiveReflectApply(primitiveBufferToString, buffer, [encoding]);
}}

function arrayFilter(array, callback) {{
  return primitiveReflectApply(primitiveArrayFilter, array, [callback]);
}}

function arraySome(array, callback) {{
  return primitiveReflectApply(primitiveArraySome, array, [callback]);
}}

function stringCharCodeAt(value, index) {{
  return primitiveReflectApply(primitiveStringCharCodeAt, value, [index]);
}}

function stringEndsWith(value, suffix) {{
  return primitiveReflectApply(primitiveStringEndsWith, value, [suffix]);
}}

function stringSlice(value, start, end) {{
  return primitiveReflectApply(primitiveStringSlice, value, [start, end]);
}}

function mapDelete(map, key) {{
  return primitiveReflectApply(primitiveMapDelete, map, [key]);
}}

function mapGet(map, key) {{
  return primitiveReflectApply(primitiveMapGet, map, [key]);
}}

function mapHas(map, key) {{
  return primitiveReflectApply(primitiveMapHas, map, [key]);
}}

function mapSet(map, key, value) {{
  primitiveReflectApply(primitiveMapSet, map, [key, value]);
}}

function setDelete(set, value) {{
  return primitiveReflectApply(primitiveSetDelete, set, [value]);
}}

function setHas(set, value) {{
  return primitiveReflectApply(primitiveSetHas, set, [value]);
}}

function setAdd(set, value) {{
  primitiveReflectApply(primitiveSetAdd, set, [value]);
}}

function setValuesArray(set) {{
  const iterator = primitiveReflectApply(primitiveSetValues, set, []);
  const values = [];
  while (true) {{
    const result = primitiveReflectApply(primitiveSetIteratorNext, iterator, []);
    if (result.done) return values;
    values.push(result.value);
  }}
}}

function hashUpdate(hash, payload) {{
  primitiveReflectApply(primitiveHashUpdate, hash, [payload]);
}}

function hashDigest(hash, encoding) {{
  return primitiveReflectApply(primitiveHashDigest, hash, [encoding]);
}}

function sha256(payload) {{
  const hash = primitiveCreateHash('sha256');
  hashUpdate(hash, payload);
  return hashDigest(hash, 'hex');
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
  const hash = primitiveCreateHash('sha256');
  hashUpdate(hash, DIGEST_DOMAIN);
  entries.sort((left, right) => primitiveBufferCompare(
    primitiveBufferFrom(left[0], 'utf8'), primitiveBufferFrom(right[0], 'utf8')));
  for (const [relative, digest] of entries) {{
    const relativeBytes = primitiveBufferFrom(relative, 'utf8');
    const length = primitiveBufferAlloc(8);
    length.writeBigUInt64BE(BigInt(relativeBytes.length));
    hashUpdate(hash, length);
    hashUpdate(hash, relativeBytes);
    hashUpdate(hash, primitiveBufferFrom(digest, 'hex'));
  }}
  return hashDigest(hash, 'hex');
}}

function loadManifest() {{
  const manifestPath = process.env[MANIFEST_ENV];
  if (!manifestPath || !primitivePathIsAbsolute(manifestPath)) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_PATH_INVALID');
  }}
  const payload = primitiveReadFileSync(manifestPath);
  if (sha256(payload) !== EXPECTED_MANIFEST_SHA256) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_SHA256_MISMATCH');
  }}
  let parsed;
  try {{
    parsed = primitiveJsonParse(bufferToString(payload, 'utf8'));
  }} catch {{
    throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
  }}
  if (!parsed || primitiveArrayIsArray(parsed) ||
      primitiveObjectKeys(parsed).sort().join(',') !== 'digest,files,root,schema' ||
      parsed.schema !== MANIFEST_SCHEMA ||
      parsed.digest !== EXPECTED_TREE_DIGEST ||
      !primitivePathIsAbsolute(parsed.root) || primitivePathResolve(parsed.root) !== parsed.root ||
      parsed.root === primitivePathParse(parsed.root).root ||
      !parsed.files || primitiveArrayIsArray(parsed.files) ||
      primitiveObjectGetPrototypeOf(parsed.files) !== Object.prototype) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
  }}
  const entries = primitiveObjectEntries(parsed.files);
  const allowed = new PrimitiveMap();
  const identities = new PrimitiveMap();
  for (const [relative, digest] of entries) {{
    const parts = relative.split('/');
    if (!relative || relative.includes('\\\\') || primitivePathIsAbsolute(relative) ||
        arraySome(parts, (part) => !part || part === '.' || part === '..') ||
        typeof digest !== 'string' || !SHA256_RE.test(digest) ||
        bufferToString(primitiveBufferFrom(relative, 'utf8'), 'utf8') !== relative) {{
      throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
    }}
    const absolute = primitivePathResolve(parsed.root, ...parts);
    if (!absolute.startsWith(parsed.root + PATH_SEPARATOR) || mapHas(allowed, absolute)) {{
      throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
    }}
    const metadata = primitiveLstatSync(absolute, {{ bigint: true }});
    if (!trustedFile(metadata)) {{
      throw integrityError('NODE_RUNTIME_MANIFEST_INVALID');
    }}
    const identity = `${{metadata.dev}}:${{metadata.ino}}`;
    if (!mapHas(identities, identity)) mapSet(identities, identity, absolute);
    mapSet(allowed, absolute, digest);
  }}
  if (treeDigest(entries) !== EXPECTED_TREE_DIGEST) {{
    throw integrityError('NODE_RUNTIME_MANIFEST_DIGEST_MISMATCH');
  }}
  return primitiveObjectFreeze({{ root: parsed.root, allowed, identities }});
}}

const runtimeManifest = loadManifest();
function assertAllowed(filename) {{
  if (typeof filename !== 'string' || primitivePathResolve(filename) !== filename ||
      !mapHas(runtimeManifest.allowed, filename)) {{
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }}
  if (filename.toLowerCase().endsWith('.node')) {{
    throw integrityError('NODE_RUNTIME_NATIVE_ADDON_REJECTED');
  }}
  return mapGet(runtimeManifest.allowed, filename);
}}

function trustedRead(filename) {{
  const expected = assertAllowed(filename);
  if (!Number.isInteger(fs.constants.O_NOFOLLOW) ||
      !primitiveExistsSync('/proc/self/fd')) {{
    throw integrityError('NODE_RUNTIME_PLATFORM_UNSUPPORTED');
  }}
  let descriptor;
  try {{
    descriptor = primitiveOpenSync(
      filename,
      fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_CLOEXEC
    );
    const before = primitiveFstatSync(descriptor, {{ bigint: true }});
    const namedBefore = primitiveLstatSync(filename, {{ bigint: true }});
    const openedPath = primitiveReadlinkSync(`/proc/self/fd/${{descriptor}}`);
    if (!trustedFile(before) || !sameStat(before, namedBefore) ||
        openedPath !== filename) {{
      throw integrityError('NODE_RUNTIME_MODULE_UNTRUSTED');
    }}
    const source = primitiveBufferAlloc(Number(before.size));
    let offset = 0;
    while (offset < source.length) {{
      const count = primitiveReadSync(
        descriptor, source, offset, source.length - offset, offset
      );
      if (count <= 0) {{
        throw integrityError('NODE_RUNTIME_MODULE_CHANGED');
      }}
      offset += count;
    }}
    const after = primitiveFstatSync(descriptor, {{ bigint: true }});
    const namedAfter = primitiveLstatSync(filename, {{ bigint: true }});
    if (!sameStat(before, after) || !sameStat(after, namedAfter)) {{
      throw integrityError('NODE_RUNTIME_MODULE_CHANGED');
    }}
    if (sha256(source) !== expected) {{
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
      try {{ primitiveCloseSync(descriptor); }} catch {{}}
    }}
  }}
}}
function generatedOutputRead(filename) {{
  const relative = primitivePathRelative(runtimeManifest.root, filename);
  const first = relative.split(PATH_SEPARATOR)[0];
  if (!relative || relative.startsWith('..' + PATH_SEPARATOR) ||
      !setHas(GENERATED_TOP_LEVEL_DIRECTORIES, first) ||
      filename.toLowerCase().endsWith('.node')) {{
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }}
  if (!Number.isInteger(fs.constants.O_NOFOLLOW) ||
      !primitiveExistsSync('/proc/self/fd')) {{
    throw integrityError('NODE_RUNTIME_PLATFORM_UNSUPPORTED');
  }}
  let descriptor;
  try {{
    descriptor = primitiveOpenSync(
      filename,
      fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_CLOEXEC
    );
    const before = primitiveFstatSync(descriptor, {{ bigint: true }});
    const namedBefore = primitiveLstatSync(filename, {{ bigint: true }});
    const openedPath = primitiveReadlinkSync(`/proc/self/fd/${{descriptor}}`);
    if (!trustedFile(before) || !sameStat(before, namedBefore) ||
        openedPath !== filename) {{
      throw integrityError('NODE_RUNTIME_GENERATED_OUTPUT_UNTRUSTED');
    }}
    const source = primitiveBufferAlloc(Number(before.size));
    let offset = 0;
    while (offset < source.length) {{
      const count = primitiveReadSync(
        descriptor, source, offset, source.length - offset, offset
      );
      if (count <= 0) {{
        throw integrityError('NODE_RUNTIME_GENERATED_OUTPUT_CHANGED');
      }}
      offset += count;
    }}
    const after = primitiveFstatSync(descriptor, {{ bigint: true }});
    const namedAfter = primitiveLstatSync(filename, {{ bigint: true }});
    if (!sameStat(before, after) || !sameStat(after, namedAfter)) {{
      throw integrityError('NODE_RUNTIME_GENERATED_OUTPUT_CHANGED');
    }}
    return source;
  }} catch (error) {{
    if (error && typeof error.code === 'string' &&
        error.code.startsWith('NODE_RUNTIME_')) {{
      throw error;
    }}
    throw integrityError('NODE_RUNTIME_GENERATED_OUTPUT_READ_FAILED');
  }} finally {{
    if (descriptor !== undefined) {{
      try {{ primitiveCloseSync(descriptor); }} catch {{}}
    }}
  }}
}}

// Dependency runtimes may load manifest-bound assets through synchronous,
// callback, promise or stream APIs. Preserve reads outside the attested tree,
// but force every read inside it through one no-follow, stable-stat and SHA-256
// verification path.
function normalizedReadPath(filename) {{
  if (typeof filename === 'string') return primitivePathResolve(filename);
  if (primitiveBufferIsBuffer(filename)) return primitivePathResolve(bufferToString(filename, 'utf8'));
  if (filename && filename.protocol === 'file:') {{
    return primitivePathResolve(fileURLToPath(filename));
  }}
  return undefined;
}}

function missingReadError(filename) {{
  const error = new Error("ENOENT: no such file or directory: " + filename);
  error.code = 'ENOENT';
  error.errno = -2;
  error.path = filename;
  error.syscall = 'open';
  return error;
}}

function runtimeAliasPath(filename) {{
  const normalized = normalizedReadPath(filename);
  if (!normalized) return undefined;
  if (normalized === runtimeManifest.root ||
      normalized.startsWith(runtimeManifest.root + PATH_SEPARATOR)) {{
    return normalized;
  }}
  try {{
    let candidate = normalized;
    let metadata = primitiveLstatSync(candidate, {{ bigint: true }});
    if ((metadata.mode & FILE_TYPE_MASK) === 0o120000n) {{
      candidate = primitivePathRealpath(candidate);
      if (candidate === runtimeManifest.root ||
          candidate.startsWith(runtimeManifest.root + PATH_SEPARATOR)) {{
        return candidate;
      }}
      metadata = primitiveLstatSync(candidate, {{ bigint: true }});
    }}
    return mapGet(
      runtimeManifest.identities, `${{metadata.dev}}:${{metadata.ino}}`
    );
  }} catch (error) {{
    if (error && error.code === 'ENOENT') return undefined;
    return undefined;
  }}
}}

function runtimeRead(filename, options) {{
  const normalized = normalizedReadPath(filename);
  const absolute = runtimeAliasPath(filename);
  if (absolute === undefined) return undefined;
  let payload;
  if (mapHas(runtimeManifest.allowed, absolute)) {{
    payload = trustedRead(absolute);
  }} else {{
    try {{
      primitiveLstatSync(absolute);
    }} catch (error) {{
      if (error && error.code === 'ENOENT') throw missingReadError(absolute);
      throw integrityError('NODE_RUNTIME_MODULE_READ_FAILED');
    }}
    payload = generatedOutputRead(absolute);
  }}
  const encoding = typeof options === 'string'
    ? options
    : options && typeof options === 'object'
      ? options.encoding
      : undefined;
  return {{
    absolute: normalized,
    payload,
    value: encoding ? bufferToString(payload, encoding) : payload,
  }};
}}

function pathIsInsideRuntime(filename) {{
  return runtimeAliasPath(filename) !== undefined;
}}

function pathIsGeneratedRuntimeOutput(filename) {{
  const absolute = normalizedReadPath(filename);
  if (!absolute || !absolute.startsWith(runtimeManifest.root + PATH_SEPARATOR)) {{
    return false;
  }}
  const relative = primitivePathRelative(runtimeManifest.root, absolute);
  return setHas(
    GENERATED_TOP_LEVEL_DIRECTORIES, relative.split(PATH_SEPARATOR)[0]
  );
}}

function readOnlyOpenFlags(flags) {{
  if (typeof flags === 'string') {{
    return (flags === 'r' || flags === 'rs' || flags === 'sr');
  }}
  if (!Number.isInteger(flags)) return false;
  const accessMode = flags & (
    fs.constants.O_RDONLY | fs.constants.O_WRONLY | fs.constants.O_RDWR
  );
  return accessMode === fs.constants.O_RDONLY &&
    (flags & (
      fs.constants.O_APPEND | fs.constants.O_CREAT |
      fs.constants.O_TRUNC | fs.constants.O_EXCL
    )) === 0;
}}


const originalOpenSync = fs.openSync.bind(fs);
const integrityOpenSync = function integrityOpenSync(filename, flags, ...args) {{
  if (!pathIsInsideRuntime(filename)) {{
    return originalOpenSync(filename, flags, ...args);
  }}
  if (!readOnlyOpenFlags(flags)) {{
    if (pathIsGeneratedRuntimeOutput(filename)) {{
      return originalOpenSync(filename, flags, ...args);
    }}
    throw integrityError('NODE_RUNTIME_DESCRIPTOR_WRITE_REJECTED');
  }}
  if (NAC_INTERNAL_ESM_LOADER_THREAD) {{
    return originalOpenSync(filename, flags, ...args);
  }}
  runtimeRead(filename);
  throw integrityError('NODE_RUNTIME_DESCRIPTOR_OPEN_REJECTED');
}};
if (!LOADER_IS_ESM &&
    primitiveObjectGetOwnPropertyDescriptor(fs, 'openSync')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs, 'openSync', {{
    value: integrityOpenSync,
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}

const originalOpen = fs.open.bind(fs);
const integrityOpen = function integrityOpen(filename, flags, ...args) {{
  if (!pathIsInsideRuntime(filename)) {{
    return originalOpen(filename, flags, ...args);
  }}
  const callback = args[args.length - 1];
  if (typeof callback !== 'function') {{
    throw new TypeError('callback must be a function');
  }}
  if (!readOnlyOpenFlags(flags)) {{
    if (pathIsGeneratedRuntimeOutput(filename)) {{
      return originalOpen(filename, flags, ...args);
    }}
    primitiveNextTick(
      callback, integrityError('NODE_RUNTIME_DESCRIPTOR_WRITE_REJECTED')
    );
    return;
  }}
  try {{
    runtimeRead(filename);
    primitiveNextTick(
      callback, integrityError('NODE_RUNTIME_DESCRIPTOR_OPEN_REJECTED')
    );
  }} catch (error) {{
    primitiveNextTick(callback, error);
  }}
}};
if (!LOADER_IS_ESM &&
    primitiveObjectGetOwnPropertyDescriptor(fs, 'open')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs, 'open', {{
    value: integrityOpen,
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}

const originalPromisesOpen = fs.promises.open.bind(fs.promises);
const integrityPromisesOpen = async function integrityPromisesOpen(
  filename, flags, ...args
) {{
  if (!pathIsInsideRuntime(filename)) {{
    return originalPromisesOpen(filename, flags, ...args);
  }}
  if (!readOnlyOpenFlags(flags)) {{
    if (pathIsGeneratedRuntimeOutput(filename)) {{
      return originalPromisesOpen(filename, flags, ...args);
    }}
    throw integrityError('NODE_RUNTIME_DESCRIPTOR_WRITE_REJECTED');
  }}
  runtimeRead(filename);
  throw integrityError('NODE_RUNTIME_DESCRIPTOR_OPEN_REJECTED');
}};
if (!LOADER_IS_ESM &&
    primitiveObjectGetOwnPropertyDescriptor(fs.promises, 'open')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs.promises, 'open', {{
    value: integrityPromisesOpen,
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}

const originalReadFileSync = fs.readFileSync.bind(fs);
const integrityReadFileSync = function integrityReadFileSync(filename, options) {{
  const verified = runtimeRead(filename, options);
  return verified === undefined
    ? originalReadFileSync(filename, options)
    : verified.value;
}};
if (primitiveObjectGetOwnPropertyDescriptor(fs, 'readFileSync')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs, 'readFileSync', {{
  value: integrityReadFileSync,
  writable: false,
  enumerable: true,
  configurable: false,
}});
}}

const originalReadFile = fs.readFile.bind(fs);
const integrityReadFile = function integrityReadFile(filename, options, callback) {{
  if (typeof options === 'function') {{
    callback = options;
    options = undefined;
  }}
  if (typeof callback !== 'function') {{
    throw new TypeError('callback must be a function');
  }}
  try {{
    const verified = runtimeRead(filename, options);
    if (verified === undefined) {{
      return options === undefined
        ? originalReadFile(filename, callback)
        : originalReadFile(filename, options, callback);
    }}
    primitiveNextTick(callback, null, verified.value);
  }} catch (error) {{
    primitiveNextTick(callback, error);
  }}
}};
if (primitiveObjectGetOwnPropertyDescriptor(fs, 'readFile')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs, 'readFile', {{
  value: integrityReadFile,
  writable: false,
  enumerable: true,
  configurable: false,
}});
}}

const originalPromisesReadFile = fs.promises.readFile.bind(fs.promises);
const integrityPromisesReadFile = async function integrityPromisesReadFile(
  filename, options
) {{
  const verified = runtimeRead(filename, options);
  return verified === undefined
    ? originalPromisesReadFile(filename, options)
    : verified.value;
}};
if (primitiveObjectGetOwnPropertyDescriptor(fs.promises, 'readFile')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs.promises, 'readFile', {{
  value: integrityPromisesReadFile,
  writable: false,
  enumerable: true,
  configurable: false,
}});
}}

if (typeof fs.openAsBlob === 'function') {{
  const originalOpenAsBlob = fs.openAsBlob.bind(fs);
  const integrityOpenAsBlob = async function integrityOpenAsBlob(
    filename, options
  ) {{
    const verified = runtimeRead(filename);
    if (verified === undefined) return originalOpenAsBlob(filename, options);
    if (typeof PrimitiveBlob !== 'function') {{
      throw integrityError('NODE_RUNTIME_BLOB_UNSUPPORTED');
    }}
    let blobOptions;
    if (options !== undefined) {{
      if (!options || typeof options !== 'object') {{
        throw integrityError('NODE_RUNTIME_BLOB_OPTIONS_REJECTED');
      }}
      const descriptors = primitiveObjectGetOwnPropertyDescriptors(options);
      if (arraySome(primitiveReflectOwnKeys(descriptors),
          (key) => key !== 'type' ||
            typeof descriptors[key].get === 'function' ||
            typeof descriptors[key].set === 'function' ||
            typeof descriptors[key].value !== 'string')) {{
        throw integrityError('NODE_RUNTIME_BLOB_OPTIONS_REJECTED');
      }}
      if (descriptors.type) blobOptions = {{ type: descriptors.type.value }};
    }}
    return blobOptions === undefined
      ? new PrimitiveBlob([verified.payload])
      : new PrimitiveBlob([verified.payload], blobOptions);
  }};
  if (primitiveObjectGetOwnPropertyDescriptor(fs, 'openAsBlob')?.configurable !== false) {{
    primitiveObjectDefineProperty(fs, 'openAsBlob', {{
      value: integrityOpenAsBlob,
      writable: false,
      enumerable: true,
      configurable: false,
    }});
  }}
}}

function verifiedRuntimeCopyPayload(source, destination) {{
  const sourceInside = pathIsInsideRuntime(source);
  const destinationInside = pathIsInsideRuntime(destination);
  if (sourceInside) {{
    if (!pathIsGeneratedRuntimeOutput(destination)) {{
      throw integrityError('NODE_RUNTIME_COPY_SOURCE_REJECTED');
    }}
    return runtimeRead(source).payload;
  }}
  if (destinationInside && !pathIsGeneratedRuntimeOutput(destination)) {{
    throw integrityError('NODE_RUNTIME_DESCRIPTOR_WRITE_REJECTED');
  }}
  return undefined;
}}

let verifiedCopyCounter = 0;
function writeVerifiedCopy(destination, payload, mode) {{
  const allowedMode = (fs.constants.COPYFILE_EXCL || 0) |
    (fs.constants.COPYFILE_FICLONE || 0) |
    (fs.constants.COPYFILE_FICLONE_FORCE || 0);
  if (mode !== undefined &&
      (!Number.isInteger(mode) || (mode & ~allowedMode) !== 0)) {{
    throw integrityError('NODE_RUNTIME_COPY_OPTIONS_REJECTED');
  }}
  const absolute = normalizedReadPath(destination);
  if (!absolute || !pathIsGeneratedRuntimeOutput(absolute)) {{
    throw integrityError('NODE_RUNTIME_COPY_DESTINATION_REJECTED');
  }}
  const parent = primitivePathDirname(absolute);
  let parentRealpath;
  try {{
    parentRealpath = primitivePathRealpath(parent);
  }} catch {{
    throw integrityError('NODE_RUNTIME_COPY_DESTINATION_REJECTED');
  }}
  if (parentRealpath !== parent || !pathIsGeneratedRuntimeOutput(parent)) {{
    throw integrityError('NODE_RUNTIME_COPY_DESTINATION_REJECTED');
  }}
  try {{
    const destinationMetadata = primitiveLstatSync(absolute, {{ bigint: true }});
    if ((destinationMetadata.mode & FILE_TYPE_MASK) === 0o120000n ||
        (mode && (mode & fs.constants.COPYFILE_EXCL))) {{
      throw integrityError('NODE_RUNTIME_COPY_DESTINATION_REJECTED');
    }}
  }} catch (error) {{
    if (!error || error.code !== 'ENOENT') throw error;
  }}
  verifiedCopyCounter += 1;
  const temporary = primitivePathJoin(
    parent, `.nac-runtime-copy-${{process.pid}}-${{verifiedCopyCounter}}`
  );
  let descriptor;
  let renamed = false;
  try {{
    descriptor = primitiveOpenSync(
      temporary,
      fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL |
        fs.constants.O_NOFOLLOW | fs.constants.O_CLOEXEC,
      0o600
    );
    let offset = 0;
    while (offset < payload.length) {{
      const count = primitiveWriteSync(
        descriptor, payload, offset, payload.length - offset, offset
      );
      if (count <= 0) throw integrityError('NODE_RUNTIME_COPY_WRITE_FAILED');
      offset += count;
    }}
    primitiveFsyncSync(descriptor);
    primitiveCloseSync(descriptor);
    descriptor = undefined;
    primitiveRenameSync(temporary, absolute);
    renamed = true;
  }} catch (error) {{
    if (error && typeof error.code === 'string' &&
        error.code.startsWith('NODE_RUNTIME_')) throw error;
    throw integrityError('NODE_RUNTIME_COPY_WRITE_FAILED');
  }} finally {{
    if (descriptor !== undefined) {{
      try {{ primitiveCloseSync(descriptor); }} catch {{}}
    }}
    if (!renamed) {{
      try {{ primitiveUnlinkSync(temporary); }} catch {{}}
    }}
  }}
}}

const originalCopyFileSync = fs.copyFileSync.bind(fs);
const integrityCopyFileSync = function integrityCopyFileSync(
  source, destination, mode
) {{
  const payload = verifiedRuntimeCopyPayload(source, destination);
  if (payload === undefined) {{
    return mode === undefined
      ? originalCopyFileSync(source, destination)
      : originalCopyFileSync(source, destination, mode);
  }}
  writeVerifiedCopy(destination, payload, mode);
}};
if (primitiveObjectGetOwnPropertyDescriptor(fs, 'copyFileSync')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs, 'copyFileSync', {{
    value: integrityCopyFileSync,
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}

const originalCopyFile = fs.copyFile.bind(fs);
const integrityCopyFile = function integrityCopyFile(
  source, destination, mode, callback
) {{
  if (typeof mode === 'function') {{
    callback = mode;
    mode = undefined;
  }}
  if (typeof callback !== 'function') {{
    throw new TypeError('callback must be a function');
  }}
  let payload;
  try {{
    payload = verifiedRuntimeCopyPayload(source, destination);
    if (payload === undefined) {{
      return mode === undefined
        ? originalCopyFile(source, destination, callback)
        : originalCopyFile(source, destination, mode, callback);
    }}
    writeVerifiedCopy(destination, payload, mode);
    primitiveNextTick(callback, null);
  }} catch (error) {{
    primitiveNextTick(callback, error);
  }}
}};
if (primitiveObjectGetOwnPropertyDescriptor(fs, 'copyFile')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs, 'copyFile', {{
    value: integrityCopyFile,
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}

const originalPromisesCopyFile = fs.promises.copyFile.bind(fs.promises);
const integrityPromisesCopyFile = async function integrityPromisesCopyFile(
  source, destination, mode
) {{
  const payload = verifiedRuntimeCopyPayload(source, destination);
  if (payload === undefined) {{
    return mode === undefined
      ? originalPromisesCopyFile(source, destination)
      : originalPromisesCopyFile(source, destination, mode);
  }}
  writeVerifiedCopy(destination, payload, mode);
}};
if (primitiveObjectGetOwnPropertyDescriptor(
      fs.promises, 'copyFile')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs.promises, 'copyFile', {{
    value: integrityPromisesCopyFile,
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}

function rejectRecursiveRuntimeCopy(source, destination) {{
  if (pathIsInsideRuntime(source)) {{
    throw integrityError('NODE_RUNTIME_COPY_SOURCE_REJECTED');
  }}
  if (pathIsInsideRuntime(destination) &&
      !pathIsGeneratedRuntimeOutput(destination)) {{
    throw integrityError('NODE_RUNTIME_DESCRIPTOR_WRITE_REJECTED');
  }}
}}
if (typeof fs.cpSync === 'function' &&
    primitiveObjectGetOwnPropertyDescriptor(fs, 'cpSync')?.configurable !== false) {{
  const originalCpSync = fs.cpSync.bind(fs);
  primitiveObjectDefineProperty(fs, 'cpSync', {{
    value: function integrityCpSync(source, destination, ...args) {{
      rejectRecursiveRuntimeCopy(source, destination);
      return originalCpSync(source, destination, ...args);
    }},
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}
if (typeof fs.cp === 'function' &&
    primitiveObjectGetOwnPropertyDescriptor(fs, 'cp')?.configurable !== false) {{
  const originalCp = fs.cp.bind(fs);
  primitiveObjectDefineProperty(fs, 'cp', {{
    value: function integrityCp(source, destination, ...args) {{
      try {{
        rejectRecursiveRuntimeCopy(source, destination);
      }} catch (error) {{
        const callback = args[args.length - 1];
        if (typeof callback !== 'function') throw error;
        primitiveNextTick(callback, error);
        return;
      }}
      return originalCp(source, destination, ...args);
    }},
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}
if (typeof fs.promises.cp === 'function' &&
    primitiveObjectGetOwnPropertyDescriptor(
      fs.promises, 'cp')?.configurable !== false) {{
  const originalPromisesCp = fs.promises.cp.bind(fs.promises);
  primitiveObjectDefineProperty(fs.promises, 'cp', {{
    value: async function integrityPromisesCp(source, destination, ...args) {{
      rejectRecursiveRuntimeCopy(source, destination);
      return originalPromisesCp(source, destination, ...args);
    }},
    writable: false,
    enumerable: true,
    configurable: false,
  }});
}}

const originalCreateReadStream = fs.createReadStream.bind(fs);
const integrityCreateReadStream = function integrityCreateReadStream(
  filename, options = {{}}
) {{
  const verified = runtimeRead(filename, options);
  if (verified === undefined) return originalCreateReadStream(filename, options);
  if (!options || typeof options !== 'object' || options.fd !== undefined) {{
    throw integrityError('NODE_RUNTIME_STREAM_OPTIONS_REJECTED');
  }}
  const start = options.start === undefined ? 0 : options.start;
  const end = options.end === undefined ? verified.payload.length - 1 : options.end;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) ||
      start < 0 || end < start || end >= verified.payload.length) {{
    throw integrityError('NODE_RUNTIME_STREAM_OPTIONS_REJECTED');
  }}
  const stream = primitiveReadableFrom([verified.payload.subarray(start, end + 1)]);
  for (const [name, primitive] of [
    ['addListener', primitiveReadableAddListener],
    ['emit', primitiveReadableEmit],
    ['on', primitiveReadableOn],
    ['once', primitiveReadableOnce],
  ]) {{
    primitiveObjectDefineProperty(stream, name, {{
      value: function integrityReadableMethod(...args) {{
        return primitiveReflectApply(primitive, this, args);
      }},
      writable: false,
      enumerable: false,
      configurable: false,
    }});
  }}
  primitiveObjectDefineProperty(stream, 'push', {{
    value: function integrityReadablePush(...args) {{
      return primitiveReflectApply(primitiveReadablePush, this, args);
    }},
    writable: false,
    enumerable: false,
    configurable: false,
  }});
  if (options.encoding) {{
    primitiveReflectApply(primitiveReadableSetEncoding, stream, [options.encoding]);
  }}
  return stream;
}};
if (primitiveObjectGetOwnPropertyDescriptor(fs, 'createReadStream')?.configurable !== false) {{
  primitiveObjectDefineProperty(fs, 'createReadStream', {{
  value: integrityCreateReadStream,
  writable: false,
  enumerable: true,
  configurable: false,
}});
}}

function verifyPackageMetadataPath(candidate) {{
  if (!candidate.startsWith(runtimeManifest.root + PATH_SEPARATOR)) return;
  if (mapHas(runtimeManifest.allowed, candidate)) {{
    trustedRead(candidate);
    return;
  }}
  try {{
    primitiveLstatSync(candidate);
  }} catch (error) {{
    if (error && error.code === 'ENOENT') return;
    throw integrityError('NODE_RUNTIME_PACKAGE_METADATA_READ_FAILED');
  }}
  throw integrityError('NODE_RUNTIME_PACKAGE_METADATA_NOT_ALLOWED');
}}

function verifyResolutionMetadata(specifier, parentFilename) {{
  const candidates = new PrimitiveSet();
  function addAncestors(start) {{
    let current = primitivePathResolve(start);
    while (current === runtimeManifest.root ||
           current.startsWith(runtimeManifest.root + PATH_SEPARATOR)) {{
      setAdd(candidates, primitivePathJoin(current, 'package.json'));
      if (current === runtimeManifest.root) break;
      current = primitivePathDirname(current);
    }}
  }}

  if (typeof parentFilename === 'string' && primitivePathIsAbsolute(parentFilename)) {{
    addAncestors(primitivePathDirname(parentFilename));
  }}
  if (typeof specifier === 'string' && primitivePathIsAbsolute(specifier)) {{
    addAncestors(primitivePathDirname(specifier));
  }} else if (typeof specifier === 'string' &&
             (specifier.startsWith('./') || specifier.startsWith('../')) &&
             typeof parentFilename === 'string' &&
             primitivePathIsAbsolute(parentFilename)) {{
    addAncestors(primitivePathDirname(primitivePathResolve(primitivePathDirname(parentFilename), specifier)));
  }} else if (typeof specifier === 'string' &&
             !specifier.startsWith('node:') &&
             !specifier.startsWith('#')) {{
    const parts = specifier.split('/');
    const packageName = specifier.startsWith('@')
      ? parts.slice(0, 2).join('/')
      : parts[0];
    if (packageName) {{
      setAdd(candidates, primitivePathJoin(runtimeManifest.root, packageName, 'package.json'));
      if (typeof parentFilename === 'string' && primitivePathIsAbsolute(parentFilename)) {{
        let current = primitivePathDirname(parentFilename);
        while (current === runtimeManifest.root ||
               current.startsWith(runtimeManifest.root + PATH_SEPARATOR)) {{
          setAdd(candidates, primitivePathJoin(
            current, 'node_modules', packageName, 'package.json'));
          if (current === runtimeManifest.root) break;
          current = primitivePathDirname(current);
        }}
      }}
    }}
  }}
  for (const candidate of setValuesArray(candidates)) {{
    verifyPackageMetadataPath(candidate);
  }}
}}

"""


def _commonjs_preloader_payload(
    *,
    expected_digest: str,
    expected_manifest_sha256: str,
    generated_top_level_directories: frozenset[str],
) -> bytes:
    source = _loader_prelude(
        expected_digest=expected_digest,
        expected_manifest_sha256=expected_manifest_sha256,
        generated_top_level_directories=generated_top_level_directories,
        esm=False,
    )
    source += r"""
const Module = require('node:module');
const builtinModules = new PrimitiveSet();
for (const name of Module.builtinModules) {
  setAdd(builtinModules, name);
  setAdd(builtinModules, name.startsWith('node:') ? name.slice(5) : `node:${name}`);
}
const cacheContainer = Module._cache;
const extensionContainer = Module._extensions;
const modulePrototype = Module.prototype;
const originalLoad = Module._load;
const originalModuleCompile = Module.prototype._compile;
const originalModulePrototypeLoad = Module.prototype.load;
const originalModulePrototypeRequire = Module.prototype.require;
const originalResolveFilename = Module._resolveFilename;
const activeModuleIdentities = new PrimitiveMap();
const completedModuleIdentities = new PrimitiveMap();
const pendingModuleLoads = new PrimitiveSet();
const trustedModuleCache = new PrimitiveMap();

function assertCacheContainerIntegrity() {
  if (primitiveObjectGetPrototypeOf(cacheContainer) !== null) {
    throw integrityError('NODE_RUNTIME_MODULE_CACHE_REJECTED');
  }
}

const integrityLoad = function integrityLoad(request, parent, isMain) {
  assertCacheContainerIntegrity();
  if (typeof request === 'string' && setHas(builtinModules, request)) {
    const builtinRequest = stringSlice(request, 0, 5) === 'node:'
      ? request
      : `node:${request}`;
    return primitiveReflectApply(
      originalLoad, this, [builtinRequest, parent, isMain]
    );
  }
  const parentFilename = parent && typeof parent.filename === 'string'
    ? parent.filename
    : undefined;
  verifyResolutionMetadata(request, parentFilename);
  const resolved = primitiveReflectApply(
    originalResolveFilename, this, [request, parent, isMain]
  );
  if (typeof resolved === 'string' && setHas(builtinModules, resolved)) {
    const builtinRequest = stringSlice(resolved, 0, 5) === 'node:'
      ? resolved
      : `node:${resolved}`;
    return primitiveReflectApply(
      originalLoad, this, [builtinRequest, parent, isMain]
    );
  }
  verifyResolutionMetadata(resolved, parentFilename);
  assertAllowed(resolved);
  const cached = primitiveObjectGetOwnPropertyDescriptor(cacheContainer, resolved);
  const trustedCachedModule = mapGet(trustedModuleCache, resolved);
  const activeCachedModule = mapGet(activeModuleIdentities, resolved);
  if (activeCachedModule !== undefined &&
      (!cached || !('value' in cached) || cached.value !== activeCachedModule)) {
    throw integrityError('NODE_RUNTIME_MODULE_CACHE_REJECTED');
  }
  if (cached && activeCachedModule === undefined &&
      (!('value' in cached) || cached.value !== trustedCachedModule)) {
    if (!primitiveReflectDeleteProperty(cacheContainer, resolved)) {
      throw integrityError('NODE_RUNTIME_MODULE_CACHE_REJECTED');
    }
  }
  mapDelete(completedModuleIdentities, resolved);
  setAdd(pendingModuleLoads, resolved);
  let exports;
  try {
    assertCacheContainerIntegrity();
    exports = primitiveReflectApply(
      originalLoad, this, [resolved, parent, isMain]
    );
  } finally {
    setDelete(pendingModuleLoads, resolved);
    assertCacheContainerIntegrity();
  }
  const loaded = primitiveObjectGetOwnPropertyDescriptor(cacheContainer, resolved);
  const completedModule = mapGet(completedModuleIdentities, resolved);
  if (completedModule !== undefined) {
    mapDelete(completedModuleIdentities, resolved);
  }
  const expectedModule = activeCachedModule !== undefined
    ? activeCachedModule
    : trustedCachedModule !== undefined
      ? trustedCachedModule
      : completedModule;
  if (!loaded || !('value' in loaded) || !expectedModule ||
      loaded.value !== expectedModule ||
      (completedModule !== undefined && completedModule !== expectedModule)) {
    throw integrityError('NODE_RUNTIME_MODULE_CACHE_REJECTED');
  }
  if (completedModule !== undefined && completedModule === expectedModule) {
    mapSet(trustedModuleCache, resolved, completedModule);
  }
  return exports;
};
primitiveObjectDefineProperty(Module, '_load', {
  get() { return integrityLoad; },
  set(value) {
    if (this === Module) return;
    primitiveObjectDefineProperty(this, '_load', {
      value,
      writable: true,
      enumerable: true,
      configurable: true,
    });
  },
  enumerable: true,
  configurable: false,
});
const integrityModulePrototypeLoad = function integrityModulePrototypeLoad(
  filename
) {
  assertAllowed(filename);
  const activeModule = mapGet(activeModuleIdentities, filename);
  const cached = primitiveObjectGetOwnPropertyDescriptor(cacheContainer, filename);
  if (!setHas(pendingModuleLoads, filename) ||
      (activeModule !== undefined && activeModule !== this) ||
      !cached || !('value' in cached) || cached.value !== this) {
    throw integrityError('NODE_RUNTIME_MODULE_CACHE_REJECTED');
  }
  primitiveObjectDefineProperty(this, 'require', {
    value: originalModulePrototypeRequire,
    writable: false,
    enumerable: false,
    configurable: false,
  });
  mapSet(activeModuleIdentities, filename, this);
  try {
    const result = primitiveReflectApply(
      originalModulePrototypeLoad, this, [filename]
    );
    mapSet(completedModuleIdentities, filename, this);
    return result;
  } finally {
    mapDelete(activeModuleIdentities, filename);
  }
};
primitiveObjectDefineProperty(Module.prototype, 'load', {
  value: integrityModulePrototypeLoad,
  writable: false,
  enumerable: false,
  configurable: false,
});
primitiveObjectDefineProperty(Module.prototype, '_compile', {
  value: originalModuleCompile,
  writable: false,
  enumerable: false,
  configurable: false,
});
primitiveObjectDefineProperty(Module.prototype, 'require', {
  get() { return originalModulePrototypeRequire; },
  set(_value) {
    // Compatibility instrumentation may assign a wrapper here. Keep the
    // verified loader authoritative without making strict-mode callers fail.
  },
  enumerable: false,
  configurable: false,
});
primitiveObjectDefineProperty(Module, 'prototype', {
  value: modulePrototype,
  writable: false,
  enumerable: false,
  configurable: false,
});

function compileJavaScript(module, filename) {
  primitiveReflectApply(
    originalModuleCompile, module,
    [bufferToString(trustedRead(filename), 'utf8'), filename]
  );
}

const expectedPiratesRegistrar = primitivePathJoin(
  runtimeManifest.root, 'node_modules', 'pirates', 'lib', 'index.js'
);
function authorizedJavaScriptRegistrar() {
  if (!mapHas(runtimeManifest.allowed, expectedPiratesRegistrar)) return false;
  let sites;
  try {
    sites = primitiveGetCallSites();
  } catch {
    return false;
  }
  for (let index = 0; index < sites.length; index += 1) {
    const scriptName = sites[index] && sites[index].scriptName;
    if (scriptName === expectedPiratesRegistrar) {
      trustedRead(expectedPiratesRegistrar);
      return true;
    }
  }
  return false;
}

let registeredJavaScriptExtension;
const activeJavaScriptCompiles = new PrimitiveMap();
const integrityJavaScriptExtension = function integrityJavaScriptExtension(
  module, filename
) {
  const verifiedSource = bufferToString(trustedRead(filename), 'utf8');
  const active = mapGet(activeJavaScriptCompiles, module);
  if (active !== undefined) {
    if (active.filename !== filename) {
      throw integrityError('NODE_RUNTIME_EXTENSION_LOADER_REJECTED');
    }
    return primitiveReflectApply(
      active.currentCompile, module, [verifiedSource, filename]
    );
  }
  if (registeredJavaScriptExtension === undefined) {
    return primitiveReflectApply(
      originalModuleCompile, module, [verifiedSource, filename]
    );
  }
  const previous = primitiveObjectGetOwnPropertyDescriptor(module, '_compile');
  const state = {
    filename,
    currentCompile: undefined,
    compiled: false,
  };
  const integrityBoundCompile = function integrityBoundCompile(
    source, compileFilename
  ) {
    if (typeof source !== 'string' || compileFilename !== filename) {
      throw integrityError('NODE_RUNTIME_EXTENSION_SOURCE_REJECTED');
    }
    state.compiled = true;
    return primitiveReflectApply(
      originalModuleCompile, module, [source, filename]
    );
  };
  state.currentCompile = integrityBoundCompile;
  primitiveObjectDefineProperty(module, '_compile', {
    get() { return state.currentCompile; },
    set(value) {
      if (typeof value !== 'function') {
        throw integrityError('NODE_RUNTIME_EXTENSION_LOADER_REJECTED');
      }
      state.currentCompile = value;
    },
    enumerable: false,
    configurable: true,
  });
  mapSet(activeJavaScriptCompiles, module, state);
  try {
    primitiveReflectApply(
      registeredJavaScriptExtension, extensionContainer, [module, filename]
    );
    if (!state.compiled) {
      throw integrityError('NODE_RUNTIME_EXTENSION_LOADER_REJECTED');
    }
  } finally {
    mapDelete(activeJavaScriptCompiles, module);
    if (previous) {
      primitiveObjectDefineProperty(module, '_compile', previous);
    } else {
      delete module._compile;
    }
  }
};
primitiveObjectDefineProperty(extensionContainer, '.js', {
  get() { return integrityJavaScriptExtension; },
  set(value) {
    if (typeof value !== 'function' || !authorizedJavaScriptRegistrar()) {
      throw integrityError('NODE_RUNTIME_EXTENSION_LOADER_REJECTED');
    }
    registeredJavaScriptExtension = value === integrityJavaScriptExtension
      ? undefined
      : value;
  },
  enumerable: true,
  configurable: false,
});
primitiveObjectDefineProperty(extensionContainer, '.cjs', {
  get() { return compileJavaScript; },
  set(value) {
    if (typeof value !== 'function') {
      throw integrityError('NODE_RUNTIME_EXTENSION_LOADER_REJECTED');
    }
    // Compatibility-only registration: the terminal remains compileJavaScript.
  },
  enumerable: true,
  configurable: false,
});
const integrityJsonExtension = function integrityJson(module, filename) {
  let source = bufferToString(trustedRead(filename), 'utf8');
  if (stringCharCodeAt(source, 0) === 0xFEFF) source = stringSlice(source, 1);
  module.exports = primitiveJsonParse(source);
};
primitiveObjectDefineProperty(extensionContainer, '.json', {
  get() { return integrityJsonExtension; },
  set(value) {
    if (typeof value !== 'function') {
      throw integrityError('NODE_RUNTIME_EXTENSION_LOADER_REJECTED');
    }
  },
  enumerable: true,
  configurable: false,
});
const rejectNativeAddon = function rejectNativeAddon() {
  throw integrityError('NODE_RUNTIME_NATIVE_ADDON_REJECTED');
};
primitiveObjectDefineProperty(extensionContainer, '.node', {
  get() { return rejectNativeAddon; },
  set(value) {
    if (typeof value !== 'function') {
      throw integrityError('NODE_RUNTIME_EXTENSION_LOADER_REJECTED');
    }
  },
  enumerable: true,
  configurable: false,
});
primitiveObjectDefineProperty(Module, '_cache', {
  get() { return cacheContainer; },
  set(value) {
    if (this === Module) return;
    primitiveObjectDefineProperty(this, '_cache', {
      value,
      writable: true,
      enumerable: true,
      configurable: true,
    });
  },
  enumerable: true,
  configurable: false,
});
primitiveObjectDefineProperty(Module, '_resolveFilename', {
  get() { return originalResolveFilename; },
  set(value) {
    if (this === Module) return;
    primitiveObjectDefineProperty(this, '_resolveFilename', {
      value,
      writable: true,
      enumerable: true,
      configurable: true,
    });
  },
  enumerable: true,
  configurable: false,
});
primitiveObjectDefineProperty(Module, '_extensions', {
  get() { return extensionContainer; },
  set(value) {
    if (this === Module) return;
    primitiveObjectDefineProperty(this, '_extensions', {
      value,
      writable: true,
      enumerable: true,
      configurable: true,
    });
  },
  enumerable: true,
  configurable: false,
});

primitiveObjectDefineProperty(process, 'dlopen', {
  value: function rejectDirectNativeAddon() {
    throw integrityError('NODE_RUNTIME_NATIVE_ADDON_REJECTED');
  },
  writable: false,
  enumerable: true,
  configurable: false,
});

// Child Node processes do not retain arbitrary inherited descriptors. Keep the
// sealed descriptors owned by this live parent and make descendants reopen the
// same immutable memfds through the parent's procfs view.
const inheritedProcPrefix = `/proc/${process.pid}/fd/`;
function pinSealedDescriptorPath(value) {
  return typeof value === 'string'
    ? value.replaceAll('/proc/self/fd/', inheritedProcPrefix)
    : value;
}
const inheritedPreloader = pinSealedDescriptorPath(
  process.env.NAC_NODE_RUNTIME_PRELOADER);
const inheritedLoader = pinSealedDescriptorPath(
  process.env.NAC_NODE_RUNTIME_ESM_LOADER);
const inheritedNode = pinSealedDescriptorPath(process.env.NODE);
const inheritedManifest = pinSealedDescriptorPath(process.env[MANIFEST_ENV]);
if (!inheritedPreloader || !inheritedLoader || !inheritedManifest) {
  throw integrityError('NODE_RUNTIME_CHILD_LOADER_BINDING_MISSING');
}
if (!inheritedNode || !primitivePathIsAbsolute(inheritedNode)) {
  throw integrityError('NODE_RUNTIME_CHILD_EXECUTABLE_BINDING_MISSING');
}
const inheritedNodeOptions = [
  '--preserve-symlinks',
  `--require=${inheritedPreloader}`,
  `--experimental-loader=${inheritedLoader}`,
].join(' ');
process.env.NODE = inheritedNode;
process.env[MANIFEST_ENV] = inheritedManifest;
process.env.NAC_NODE_RUNTIME_PRELOADER = inheritedPreloader;
process.env.NAC_NODE_RUNTIME_ESM_LOADER = inheritedLoader;
process.env.NODE_OPTIONS = inheritedNodeOptions;
primitiveObjectDefineProperty(process, 'execPath', {
  value: inheritedNode,
  writable: false,
  enumerable: true,
  configurable: false,
});
// fork() inherits process.execArgv in addition to NODE_OPTIONS. Clear the
// startup-only /proc/self/fd arguments so the sealed loader is not loaded twice
// and so descendants use only the parent-pinned procfs bindings below.
primitiveObjectDefineProperty(process, 'execArgv', {
  value: primitiveObjectFreeze([]),
  writable: false,
  enumerable: true,
  configurable: false,
});
const childProcess = require('node:child_process');
const originalFork = childProcess.fork.bind(childProcess);
const originalChildProcessSpawn = childProcess.ChildProcess.prototype.spawn;
let approvedForkSpawnDepth = 0;
childProcess.fork = function integrityFork(modulePath, args = [], options = {}) {
  if (!primitiveArrayIsArray(args)) {
    options = args || {};
    args = [];
  }
  if (!options || typeof options !== 'object') {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  const absolute = typeof modulePath === 'string'
    ? primitivePathResolve(modulePath)
    : undefined;
  assertAllowed(absolute);
  const optionDescriptors = primitiveObjectGetOwnPropertyDescriptors(options);
  const allowedOptionKeys = new PrimitiveSet([
    'cwd', 'detached', 'env', 'execArgv', 'execPath', 'gid', 'killSignal',
    'serialization', 'signal', 'silent', 'stdio', 'timeout', 'uid',
    'windowsHide', 'windowsVerbatimArguments',
  ]);
  if (arraySome(primitiveReflectOwnKeys(optionDescriptors),
      (key) => typeof key !== 'string' || !setHas(allowedOptionKeys, key) ||
        typeof optionDescriptors[key].get === 'function' ||
        typeof optionDescriptors[key].set === 'function')) {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  const optionValue = (name) => optionDescriptors[name]?.value;
  if (optionValue('detached') === true ||
      optionValue('windowsVerbatimArguments') === true ||
      optionValue('signal') !== undefined ||
      optionValue('uid') !== undefined ||
      optionValue('gid') !== undefined) {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  let normalizedCwd;
  if (optionValue('cwd') !== undefined) {
    if (typeof optionValue('cwd') !== 'string') {
      throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
    }
    normalizedCwd = primitivePathResolve(optionValue('cwd'));
    if (normalizedCwd !== runtimeManifest.root &&
        !normalizedCwd.startsWith(runtimeManifest.root + PATH_SEPARATOR)) {
      throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
    }
  }
  const serialization = optionValue('serialization');
  if (serialization !== undefined &&
      serialization !== 'json' && serialization !== 'advanced') {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  const timeout = optionValue('timeout');
  if (timeout !== undefined &&
      (!Number.isSafeInteger(timeout) || timeout < 0)) {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  const killSignal = optionValue('killSignal');
  if (killSignal !== undefined &&
      !(Number.isSafeInteger(killSignal) && killSignal > 0) &&
      !(typeof killSignal === 'string' && /^[A-Z0-9]+$/.test(killSignal))) {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  let normalizedStdio;
  const stdio = optionValue('stdio');
  if (stdio !== undefined) {
    if (typeof stdio === 'string') {
      if (!setHas(new PrimitiveSet(['pipe', 'inherit', 'ignore']), stdio)) {
        throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
      }
      normalizedStdio = stdio;
    } else if (primitiveArrayIsArray(stdio)) {
      const descriptors = primitiveObjectGetOwnPropertyDescriptors(stdio);
      const length = descriptors.length?.value;
      if (!Number.isSafeInteger(length) || length < 0 || length > 8 ||
          arraySome(primitiveReflectOwnKeys(descriptors), (key) => {
            if (key === 'length') return false;
            if (typeof key !== 'string' || !/^(0|[1-9][0-9]*)$/.test(key)) return true;
            const descriptor = descriptors[key];
            return typeof descriptor.get === 'function' ||
              typeof descriptor.set === 'function' ||
              !setHas(
                new PrimitiveSet(['pipe', 'inherit', 'ignore', 'ipc']),
                descriptor.value
              );
          })) {
        throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
      }
      normalizedStdio = primitiveArrayFrom(
        { length },
        (_, index) => descriptors[String(index)]?.value ?? 'ignore'
      );
      if (arrayFilter(normalizedStdio, (value) => value === 'ipc').length !== 1) {
        throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
      }
    } else {
      throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
    }
  }
  const envSource = optionValue('env') || process.env;
  const envDescriptors = primitiveObjectGetOwnPropertyDescriptors(envSource);
  if (arraySome(primitiveReflectOwnKeys(envDescriptors),
      (key) => typeof key !== 'string' ||
        typeof envDescriptors[key].get === 'function' ||
        typeof envDescriptors[key].set === 'function' ||
        typeof envDescriptors[key].value !== 'string')) {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  const normalizedArgs = primitiveArrayFrom(args);
  if (arraySome(normalizedArgs, (value) => typeof value !== 'string')) {
    throw integrityError('NODE_RUNTIME_FORK_OPTIONS_REJECTED');
  }
  const childEnvironment = primitiveObjectCreate(null);
  for (const key of primitiveReflectOwnKeys(envDescriptors)) {
    childEnvironment[key] = envDescriptors[key].value;
  }
  childEnvironment.NODE = inheritedNode;
  childEnvironment[MANIFEST_ENV] = inheritedManifest;
  childEnvironment.NAC_NODE_RUNTIME_PRELOADER = inheritedPreloader;
  childEnvironment.NAC_NODE_RUNTIME_ESM_LOADER = inheritedLoader;
  childEnvironment.NODE_OPTIONS = inheritedNodeOptions;
  const normalizedOptions = {
    silent: optionValue('silent') === true,
    env: childEnvironment,
    execPath: inheritedNode,
    execArgv: [],
    ...(normalizedCwd === undefined ? {} : { cwd: normalizedCwd }),
    ...(normalizedStdio === undefined ? {} : { stdio: normalizedStdio }),
    ...(serialization === undefined ? {} : { serialization }),
    ...(timeout === undefined ? {} : { timeout }),
    ...(killSignal === undefined ? {} : { killSignal }),
    ...(optionValue('windowsHide') === true ? { windowsHide: true } : {}),
  };
  approvedForkSpawnDepth += 1;
  try {
    return originalFork(absolute, normalizedArgs, normalizedOptions);
  } finally {
    approvedForkSpawnDepth -= 1;
  }
};
primitiveObjectDefineProperty(childProcess, 'fork', {
  value: childProcess.fork,
  writable: false,
  enumerable: true,
  configurable: false,
});

primitiveObjectDefineProperty(childProcess.ChildProcess.prototype, 'spawn', {
  value: function integrityChildProcessPrototypeSpawn(options) {
    if (approvedForkSpawnDepth !== 1) {
      throw integrityError('NODE_RUNTIME_NODE_SUBPROCESS_REJECTED');
    }
    return primitiveReflectApply(originalChildProcessSpawn, this, [options]);
  },
  writable: false,
  enumerable: false,
  configurable: false,
});

for (const name of [
  'spawn', 'spawnSync', 'exec', 'execSync', 'execFile', 'execFileSync'
]) {
  const guarded = function integrityChildProcess() {
    throw integrityError('NODE_RUNTIME_NODE_SUBPROCESS_REJECTED');
  };
  primitiveObjectDefineProperty(childProcess, name, {
    value: guarded,
    writable: false,
    enumerable: true,
    configurable: false,
  });
}

const workerThreads = require('node:worker_threads');
const OriginalWorker = workerThreads.Worker;
const integrityWorkerExecArgv = primitiveObjectFreeze([
  '--preserve-symlinks',
  `--require=${inheritedPreloader}`,
  `--experimental-loader=${inheritedLoader}`,
]);
function IntegrityWorker(filename, options = {}) {
  if (!new.target || !options || typeof options !== 'object') {
    throw integrityError('NODE_RUNTIME_WORKER_OPTIONS_REJECTED');
  }
  const optionDescriptors = primitiveObjectGetOwnPropertyDescriptors(options);
  const allowedOptionKeys = new PrimitiveSet([
    'env', 'eval', 'name', 'resourceLimits', 'stderr', 'stdin', 'stdout',
    'trackUnmanagedFds', 'workerData',
  ]);
  if (arraySome(primitiveReflectOwnKeys(optionDescriptors),
      (key) => typeof key !== 'string' || !setHas(allowedOptionKeys, key) ||
        typeof optionDescriptors[key].get === 'function' ||
        typeof optionDescriptors[key].set === 'function')) {
    throw integrityError('NODE_RUNTIME_WORKER_OPTIONS_REJECTED');
  }
  const optionValue = (name) => optionDescriptors[name]?.value;
  if (optionValue('eval') !== undefined && optionValue('eval') !== false) {
    throw integrityError('NODE_RUNTIME_WORKER_OPTIONS_REJECTED');
  }
  let absolute;
  if (typeof filename === 'string') {
    absolute = primitivePathResolve(filename);
  } else if (filename && filename.protocol === 'file:') {
    absolute = primitivePathResolve(fileURLToPath(filename));
  }
  assertAllowed(absolute);
  const envSource = optionValue('env') || process.env;
  if (envSource === workerThreads.SHARE_ENV ||
      !envSource || typeof envSource !== 'object') {
    throw integrityError('NODE_RUNTIME_WORKER_OPTIONS_REJECTED');
  }
  const envDescriptors = primitiveObjectGetOwnPropertyDescriptors(envSource);
  if (arraySome(primitiveReflectOwnKeys(envDescriptors),
      (key) => typeof key !== 'string' ||
        typeof envDescriptors[key].get === 'function' ||
        typeof envDescriptors[key].set === 'function' ||
        typeof envDescriptors[key].value !== 'string')) {
    throw integrityError('NODE_RUNTIME_WORKER_OPTIONS_REJECTED');
  }
  const workerEnvironment = primitiveObjectCreate(null);
  for (const key of primitiveReflectOwnKeys(envDescriptors)) {
    workerEnvironment[key] = envDescriptors[key].value;
  }
  workerEnvironment.NODE_OPTIONS = '';
  const normalizedOptions = {
    env: workerEnvironment,
    execArgv: integrityWorkerExecArgv,
  };
  for (const name of [
    'name', 'resourceLimits', 'stderr', 'stdin', 'stdout',
    'trackUnmanagedFds', 'workerData',
  ]) {
    if (optionValue(name) !== undefined) normalizedOptions[name] = optionValue(name);
  }
  return new OriginalWorker(filename, normalizedOptions);
}
IntegrityWorker.prototype = OriginalWorker.prototype;
primitiveObjectDefineProperty(OriginalWorker.prototype, 'constructor', {
  value: IntegrityWorker,
  writable: false,
  enumerable: false,
  configurable: false,
});
primitiveObjectDefineProperty(workerThreads, 'Worker', {
  value: IntegrityWorker,
  writable: false,
  enumerable: true,
  configurable: false,
});
const forbiddenProcessBindings = new PrimitiveSet(['spawn_sync', 'process_wrap']);
const originalProcessBinding = process.binding.bind(process);
primitiveObjectDefineProperty(process, 'binding', {
  value: function integrityProcessBinding(name) {
    if (setHas(forbiddenProcessBindings, name) ||
        (typeof name === 'string' && name.startsWith('fs'))) {
      throw integrityError('NODE_RUNTIME_LOW_LEVEL_SUBPROCESS_REJECTED');
    }
    return originalProcessBinding(name);
  },
  writable: false,
  enumerable: false,
  configurable: false,
});
if (typeof process._linkedBinding === 'function') {
  primitiveObjectDefineProperty(process, '_linkedBinding', {
    value: function integrityLinkedBinding() {
      throw integrityError('NODE_RUNTIME_LOW_LEVEL_SUBPROCESS_REJECTED');
    },
    writable: false,
    enumerable: false,
    configurable: false,
  });
}
"""
    return source.encode("utf-8")


def _esm_loader_payload(
    *,
    expected_digest: str,
    expected_manifest_sha256: str,
    generated_top_level_directories: frozenset[str],
) -> bytes:
    source = _loader_prelude(
        expected_digest=expected_digest,
        expected_manifest_sha256=expected_manifest_sha256,
        generated_top_level_directories=generated_top_level_directories,
        esm=True,
    )
    source += r"""
const VIRTUAL_BUILTINS = new PrimitiveMap([
  ['node:fs', {
    url: 'nac-integrity:fs',
    source: `
      import fs from 'node:fs';
      export * from 'node:fs';
      export default fs;
      export const openSync = (...args) => fs.openSync(...args);
      export const open = (...args) => fs.open(...args);
      export const readFileSync = (...args) => fs.readFileSync(...args);
      export const readFile = (...args) => fs.readFile(...args);
      export const copyFileSync = (...args) => fs.copyFileSync(...args);
      export const copyFile = (...args) => fs.copyFile(...args);
      export const cpSync = (...args) => fs.cpSync(...args);
      export const cp = (...args) => fs.cp(...args);
      export const createReadStream = (...args) => fs.createReadStream(...args);
      export const openAsBlob = (...args) => fs.openAsBlob(...args);
    `,
  }],
  ['node:fs/promises', {
    url: 'nac-integrity:fs-promises',
    source: `
      import fs from 'node:fs';
      const promises = fs.promises;
      export * from 'node:fs/promises';
      export default promises;
      export const open = (...args) => promises.open(...args);
      export const readFile = (...args) => promises.readFile(...args);
      export const copyFile = (...args) => promises.copyFile(...args);
      export const cp = (...args) => promises.cp(...args);
    `,
  }],
  ['node:child_process', {
    url: 'nac-integrity:child-process',
    source: `
      import childProcess from 'node:child_process';
      export * from 'node:child_process';
      export default childProcess;
      export const fork = (...args) => childProcess.fork(...args);
      export const spawn = (...args) => childProcess.spawn(...args);
      export const spawnSync = (...args) => childProcess.spawnSync(...args);
      export const exec = (...args) => childProcess.exec(...args);
      export const execSync = (...args) => childProcess.execSync(...args);
      export const execFile = (...args) => childProcess.execFile(...args);
      export const execFileSync = (...args) => childProcess.execFileSync(...args);
    `,
  }],
  ['node:worker_threads', {
    url: 'nac-integrity:worker-threads',
    source: `
      import workerThreads from 'node:worker_threads';
      export * from 'node:worker_threads';
      export default workerThreads;
      export const Worker = workerThreads.Worker;
    `,
  }],
]);
const VIRTUAL_BUILTIN_BY_URL = new PrimitiveMap(
  [...VIRTUAL_BUILTINS.values()].map((item) => [item.url, item])
);

export async function resolve(specifier, context, nextResolve) {
  const parentIsVirtual = typeof context.parentURL === 'string' &&
    context.parentURL.startsWith('nac-integrity:');
  const normalizedBuiltin = typeof specifier === 'string'
    ? specifier.startsWith('node:') ? specifier : `node:${specifier}`
    : undefined;
  const virtualBuiltin = mapGet(VIRTUAL_BUILTINS, normalizedBuiltin);
  if (virtualBuiltin && !parentIsVirtual) {
    return { url: virtualBuiltin.url, shortCircuit: true };
  }
  if (typeof specifier === 'string' && specifier.startsWith('nac-integrity:')) {
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }
  const parentFilename = context.parentURL && context.parentURL.startsWith('file:')
    ? fileURLToPath(context.parentURL)
    : undefined;
  verifyResolutionMetadata(specifier, parentFilename);
  const resolved = await nextResolve(specifier, context);
  if (resolved.url.startsWith('node:')) return resolved;
  if (!resolved.url.startsWith('file:')) {
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }
  const filename = fileURLToPath(resolved.url);
  verifyResolutionMetadata(filename, parentFilename);
  assertAllowed(filename);
  return resolved;
}

function verifiedModuleFormat(filename) {
  const extension = primitivePathExtname(filename).toLowerCase();
  if (extension === '.mjs') return 'module';
  if (extension === '.cjs') return 'commonjs';
  if (extension === '.json') return 'json';
  if (extension !== '.js' && extension !== '') {
    throw integrityError('NODE_RUNTIME_MODULE_FORMAT_REJECTED');
  }
  let current = primitivePathDirname(filename);
  while (current === runtimeManifest.root ||
         current.startsWith(runtimeManifest.root + PATH_SEPARATOR)) {
    const packageMetadata = primitivePathJoin(current, 'package.json');
    if (mapHas(runtimeManifest.allowed, packageMetadata)) {
      let parsed;
      try {
        parsed = primitiveJsonParse(
          bufferToString(trustedRead(packageMetadata), 'utf8')
        );
      } catch (error) {
        if (error && typeof error.code === 'string' &&
            error.code.startsWith('NODE_RUNTIME_')) throw error;
        throw integrityError('NODE_RUNTIME_PACKAGE_METADATA_INVALID');
      }
      return parsed && parsed.type === 'module' ? 'module' : 'commonjs';
    }
    verifyPackageMetadataPath(packageMetadata);
    if (current === runtimeManifest.root) break;
    current = primitivePathDirname(current);
  }
  return 'commonjs';
}

export async function load(url, context, nextLoad) {
  const virtualBuiltin = mapGet(VIRTUAL_BUILTIN_BY_URL, url);
  if (virtualBuiltin) {
    return {
      format: 'module',
      source: virtualBuiltin.source,
      shortCircuit: true,
    };
  }
  if (url.startsWith('node:')) return nextLoad(url, context);
  if (!url.startsWith('file:')) {
    throw integrityError('NODE_RUNTIME_MODULE_NOT_ALLOWED');
  }
  const filename = fileURLToPath(url);
  verifyResolutionMetadata(filename, filename);
  assertAllowed(filename);
  const format = verifiedModuleFormat(filename);
  const verified = trustedRead(filename);
  if (format === 'commonjs') {
    const loaded = await nextLoad(url, context);
    if (loaded.format !== 'commonjs') {
      throw integrityError('NODE_RUNTIME_MODULE_FORMAT_REJECTED');
    }
    return loaded;
  }
  return {
    format,
    source: verified,
    shortCircuit: true,
  };
}
"""
    return source.encode("utf-8")
