from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PLUGIN_NAME = "nac-pkcs7-certbundle"
SCHEMA_VERSION = "nac.pkcs7-certbundle.evidence/v1"
MAX_INPUT_BYTES = 5 * 1024 * 1024
PKCS7_EXTENSIONS = {".p7b", ".p7c", ".pkcs7"}
CERT_BUNDLE_EXTENSIONS = PKCS7_EXTENSIONS | {".pem", ".cer", ".crt"}
OUT_OF_SCOPE_EXTENSIONS = {".pfx", ".p12", ".key"}
PEM_DASHES = "-" * 5
PEM_BEGIN = PEM_DASHES + "BEGIN "
PEM_END = PEM_DASHES + "END "
PEM_CLOSE = PEM_DASHES
PKCS7_LABEL = "PKCS" + "7"
PKCS7_SPACED_LABEL = "PKCS #7"
CERTIFICATE_LABEL = "CERTIFICATE"


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def check_result(
    check_id: str,
    title: str,
    status: str,
    severity: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "severity": severity,
        "message": message,
        "details": details or {},
    }


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_command(command: list[str], timeout: float = 5.0) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout, completed.stderr


def detect_container_format(path: Path, data: bytes) -> dict[str, Any]:
    suffix = path.suffix.lower()
    prefix = data[:4096].decode("utf-8", errors="ignore")
    is_pem = PEM_BEGIN in prefix
    pem_pkcs7 = (
        f"{PEM_BEGIN}{PKCS7_LABEL}" in prefix
        or f"{PEM_BEGIN}{PKCS7_SPACED_LABEL}" in prefix
    )
    pem_certs = prefix.count(f"{PEM_BEGIN}{CERTIFICATE_LABEL}{PEM_CLOSE}")
    der_asn1_candidate = bool(data[:1] == b"0")

    if suffix in OUT_OF_SCOPE_EXTENSIONS:
        kind = "out_of_scope_software_token"
    elif pem_pkcs7:
        kind = "pem_pkcs7"
    elif pem_certs:
        kind = "pem_certificate_bundle"
    elif suffix in PKCS7_EXTENSIONS and der_asn1_candidate:
        kind = "der_pkcs7_candidate"
    elif suffix in CERT_BUNDLE_EXTENSIONS:
        kind = "certificate_bundle_candidate"
    else:
        kind = "unknown"

    return {
        "extension": suffix,
        "extension_supported": suffix in CERT_BUNDLE_EXTENSIONS,
        "encoding": "pem" if is_pem else "der_or_binary",
        "kind": kind,
        "pem_certificate_markers": pem_certs,
        "der_asn1_candidate": der_asn1_candidate,
    }


def probe_local_tooling() -> dict[str, Any]:
    openssl = command_exists("openssl")
    certutil = platform.system() == "Windows" and (
        command_exists("certutil.exe") or command_exists("certutil")
    )
    if openssl or certutil:
        return check_result(
            "local_tooling",
            "Local PKCS#7 parser tooling",
            "passed",
            "info",
            "At least one local parser path is available.",
            {
                "openssl_available": openssl,
                "windows_certutil_available": certutil,
            },
        )
    return check_result(
        "local_tooling",
        "Local PKCS#7 parser tooling",
        "manual_review",
        "manual",
        "No local parser path was detected. Install OpenSSL or use Windows certutil.exe.",
        {
            "openssl_available": False,
            "windows_certutil_available": False,
        },
    )


def inspect_with_openssl(path: Path, encoding: str) -> dict[str, Any]:
    if not command_exists("openssl"):
        return check_result(
            "openssl_parse",
            "OpenSSL PKCS#7 parse",
            "manual_review",
            "manual",
            "OpenSSL is not available on PATH.",
            {"tool_available": False},
        )

    inform = "PEM" if encoding == "pem" else "DER"
    rc, stdout, stderr = run_command(
        ["openssl", "pkcs7", "-inform", inform, "-in", str(path), "-print_certs", "-noout"]
    )
    if rc == 0:
        return check_result(
            "openssl_parse",
            "OpenSSL PKCS#7 parse",
            "passed",
            "info",
            "OpenSSL parsed the certificate bundle without exposing certificate material.",
            {
                "tool_available": True,
                "inform": inform,
                "return_code": rc,
                "subject_line_count": stdout.lower().count("subject="),
                "issuer_line_count": stdout.lower().count("issuer="),
                "parser_output_hash": hash_text(stdout) if stdout else None,
            },
        )
    return check_result(
        "openssl_parse",
        "OpenSSL PKCS#7 parse",
        "manual_review",
        "manual",
        "OpenSSL could not parse the input as PKCS#7. Review whether it is a valid bundle.",
        {
            "tool_available": True,
            "inform": inform,
            "return_code": rc,
            "stderr_hash": hash_text(stderr) if stderr else None,
        },
    )


def inspect_with_windows_certutil(path: Path) -> dict[str, Any]:
    if platform.system() != "Windows":
        return check_result(
            "windows_certutil_parse",
            "Windows certutil parse",
            "manual_review",
            "manual",
            "Windows certutil is only checked on Windows.",
            {"tool_available": False},
        )

    command = "certutil.exe" if command_exists("certutil.exe") else "certutil"
    if not command_exists(command):
        return check_result(
            "windows_certutil_parse",
            "Windows certutil parse",
            "manual_review",
            "manual",
            "Windows certutil is not available.",
            {"tool_available": False},
        )

    rc, stdout, stderr = run_command([command, "-dump", str(path)])
    if rc == 0:
        return check_result(
            "windows_certutil_parse",
            "Windows certutil parse",
            "passed",
            "info",
            "Windows certutil parsed the local artifact without storing certificate material.",
            {
                "tool_available": True,
                "return_code": rc,
                "parser_output_hash": hash_text(stdout) if stdout else None,
            },
        )
    return check_result(
        "windows_certutil_parse",
        "Windows certutil parse",
        "manual_review",
        "manual",
        "Windows certutil could not parse the local artifact.",
        {
            "tool_available": True,
            "return_code": rc,
            "stderr_hash": hash_text(stderr) if stderr else None,
        },
    )


def build_parser_checks(path: Path, encoding: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if command_exists("openssl"):
        checks.append(inspect_with_openssl(path, encoding))

    windows_certutil_available = platform.system() == "Windows" and (
        command_exists("certutil.exe") or command_exists("certutil")
    )
    if windows_certutil_available:
        checks.append(inspect_with_windows_certutil(path))

    if checks:
        return checks
    return [
        check_result(
            "pkcs7_parse",
            "PKCS#7 certificate-bundle parse",
            "manual_review",
            "manual",
            "No local PKCS#7 parser path is available for this input.",
            {"openssl_available": False, "windows_certutil_available": False},
        )
    ]


def evaluate_overall_status(checks: list[dict[str, Any]]) -> str:
    if any(item["status"] == "failed" and item["severity"] == "blocker" for item in checks):
        return "blocked"
    if any(item["status"] != "passed" for item in checks):
        return "manual_review"
    return "ready"


def next_required_action(status: str) -> str:
    if status == "blocked":
        return "Stop and resolve the out-of-scope or invalid local artifact before review."
    if status == "manual_review":
        return "Review local parser availability and confirm the artifact is a PKCS#7/P7B/P7C certificate bundle."
    return "Use the metadata evidence for review; keep signing and private-key handling in a separate approved workstream."


def build_evidence(args: argparse.Namespace) -> dict[str, Any]:
    checks = [probe_local_tooling()]
    input_metadata: dict[str, Any] = {
        "provided": bool(args.input),
    }

    if not args.input:
        checks.append(
            check_result(
                "input_bundle",
                "Local certificate bundle input",
                "manual_review",
                "manual",
                "No local PKCS#7/P7B/P7C certificate bundle was provided.",
            )
        )
    else:
        path = args.input
        suffix = path.suffix.lower()
        input_metadata["path_hash"] = hash_text(str(path.resolve()))
        input_metadata["extension"] = suffix

        if suffix in OUT_OF_SCOPE_EXTENSIONS:
            checks.append(
                check_result(
                    "input_bundle",
                    "Local certificate bundle input",
                    "failed",
                    "blocker",
                    "PFX, PKCS#12 and key files are out of scope for this non-signing workstream.",
                    {"extension": suffix},
                )
            )
        elif not path.exists() or not path.is_file():
            checks.append(
                check_result(
                    "input_bundle",
                    "Local certificate bundle input",
                    "failed",
                    "blocker",
                    "The input path does not exist or is not a file.",
                    {"extension": suffix},
                )
            )
        else:
            data = path.read_bytes()
            size = len(data)
            detected = detect_container_format(path, data)
            input_metadata.update(
                {
                    "size_bytes": size,
                    "sha256": sha256_hex(data),
                    "detected": detected,
                }
            )
            if size > args.max_bytes:
                checks.append(
                    check_result(
                        "input_bundle",
                        "Local certificate bundle input",
                        "failed",
                        "blocker",
                        "The input file is larger than the configured metadata-only limit.",
                        {"size_bytes": size, "max_bytes": args.max_bytes},
                    )
                )
            elif detected["kind"] == "out_of_scope_software_token":
                checks.append(
                    check_result(
                        "input_bundle",
                        "Local certificate bundle input",
                        "failed",
                        "blocker",
                        "The input looks like a software-token/private-key artifact and is out of scope.",
                        detected,
                    )
                )
            else:
                checks.append(
                    check_result(
                        "input_bundle",
                        "Local certificate bundle input",
                        "passed" if detected["kind"] != "unknown" else "manual_review",
                        "info" if detected["kind"] != "unknown" else "manual",
                        "Local artifact was classified without storing certificate material.",
                        detected,
                    )
                )
                if detected["kind"] in {
                    "pem_pkcs7",
                    "der_pkcs7_candidate",
                    "certificate_bundle_candidate",
                }:
                    checks.extend(build_parser_checks(path, detected["encoding"]))
                elif detected["kind"] == "pem_certificate_bundle":
                    checks.append(
                        check_result(
                            "certificate_bundle_parse",
                            "PEM certificate-bundle parse",
                            "passed",
                            "info",
                            "PEM certificate markers were counted without storing certificate values.",
                            {"certificate_marker_count": detected["pem_certificate_markers"]},
                        )
                    )

    status = evaluate_overall_status(checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "plugin": PLUGIN_NAME,
        "evidence_id": f"PKCS7-CERTBUNDLE-{uuid.uuid4()}",
        "generated_at": utc_now(),
        "overall_status": status,
        "mode": "local_metadata_only",
        "input": input_metadata,
        "policy": {
            "local_only": True,
            "external_network_calls": False,
            "private_key_loaded": False,
            "pkcs12_pfx_imported": False,
            "pin_captured": False,
            "signature_created": False,
            "signature_verified": False,
            "certificate_material_stored": False,
        },
        "checks": checks,
        "next_required_action": next_required_action(status),
    }


def write_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect local PKCS#7/P7B/P7C certificate-bundle evidence without signing."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Local PKCS#7/P7B/P7C certificate-bundle path. Do not pass PFX/P12/private-key files.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=MAX_INPUT_BYTES,
        help="Maximum local input size for metadata-only inspection.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON evidence output path.")
    parser.add_argument("--json", action="store_true", help="Print full JSON evidence to stdout.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code unless the certificate-bundle gate is ready.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    evidence = build_evidence(args)

    if args.output:
        write_output(args.output, evidence)

    if args.json:
        print(json.dumps(evidence, indent=2, ensure_ascii=True))
    else:
        print(f"{PLUGIN_NAME}: {evidence['overall_status']}")
        print(evidence["next_required_action"])

    if args.strict and evidence["overall_status"] != "ready":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
