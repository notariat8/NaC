---
name: noc-pkcs7-certbundle
description: Inspect local PKCS#7/P7B/P7C certificate bundles as metadata-only evidence without signing, private-key access, PIN capture or external calls.
---

# NoC PKCS7 CertBundle Gate

Use this skill when the user asks for local PKCS#7, P7B or P7C certificate-bundle inspection and explicitly does not want signing or software-token handling.

## Operating Boundary

- Treat PKCS#7/P7B/P7C files as certificate-bundle evidence only.
- Do not request, import or inspect PFX/PKCS#12 software-token files.
- Do not request PINs, passwords, private keys, certificate values or client content.
- Do not create or verify signatures.
- Do not send certificate material to external services.

## Runnable Check

From the repository root:

```powershell
python plugins\noc-pkcs7-certbundle\scripts\inspect_certbundle.py --json
```

With a local bundle:

```powershell
python plugins\noc-pkcs7-certbundle\scripts\inspect_certbundle.py --input C:\path\to\bundle.p7b --json
```

The output is metadata-only evidence. If the user asks for private-key, PFX, signing or qualified-signature behavior, route that to a separate approved workstream.
