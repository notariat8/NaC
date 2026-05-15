# NoC PKCS7 CertBundle Gate

Installable local Codex plugin for metadata-only PKCS#7/P7B/P7C certificate-bundle evidence. This workstream is intentionally not a signature provider. It does not load private keys, import PFX/PKCS#12 software tokens, request PINs, create signatures, verify signatures or call external services.

## Status

Runnable local MVP. The plugin can prove that a local workstation has a supported parser path and can inspect a local PKCS#7 certificate bundle as evidence metadata only.

## Runnable MVP

Run the local check from the repository root:

```powershell
python plugins\noc-pkcs7-certbundle\scripts\inspect_certbundle.py --json
```

Inspect a local bundle:

```powershell
python plugins\noc-pkcs7-certbundle\scripts\inspect_certbundle.py --input C:\path\to\bundle.p7b --json
```

Use `--strict` in automation when a missing or unparsable bundle should return a non-zero exit code. The generated JSON follows `contracts/certbundle-evidence.schema.json` and records only metadata such as file size, extension, hashes, parser availability and certificate-count signals where the local parser exposes them.

## Boundary

- Local-only PKCS#7/P7B/P7C certificate-bundle evidence.
- No PFX/PKCS#12 import.
- No private-key access.
- No PIN capture.
- No certificate material storage in Git.
- No signature creation or signature verification.
- No external network calls.
- No replacement for BNotK card, XNP, SAK-lite or qualified-signature workflows.

## Day0

- Confirm whether the source artifact is a PKCS#7/P7B/P7C certificate bundle, not a software token.
- Confirm local parser availability through Windows `certutil.exe` or OpenSSL.
- Confirm the evidence output path is outside client-data folders unless explicitly approved.

## Day1

- Run `scripts/inspect_certbundle.py` against the local certificate bundle.
- Store only the metadata evidence needed for review.
- Route any software-token, PFX, private-key or signing requirement to a separate approved workstream.

## Day2

- Re-run the evidence check after certificate-chain changes, workstation changes or parser updates.
- Compare bundle fingerprints and parser status as drift evidence.

## Required Accounts And Approvals

- Local workstation approval.
- Certificate-bundle source approval.
- Security review before any expansion beyond metadata-only inspection.
- Separate approval for any future software-token, private-key, remote-signature or qualified-signature integration.
