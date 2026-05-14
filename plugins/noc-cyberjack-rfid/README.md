# NoC Card SAK Gate

Installable local Codex plugin for notary card-readiness before XNP login and Online HRA work. It checks BNotK chip/signature card availability, REINER SCT cyberJack reader readiness, security-class-3 reader requirements, PC/SC state, BNotK SAK lite or XNP card path, secureFramework readiness, XNP local-interface prerequisites and evidence metadata without PIN capture, API-key capture or card data extraction.

## Status

Runnable local MVP. For notary-side Online HRA, this plugin comes before `noc-bnotk-xnp`, because XNP login cannot be tested until the local card path is ready. External write adapters are intentionally not enabled in this first version.

## Runnable MVP

Run the local readiness check from the repository root:

```powershell
python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json
```

For an operator-attested local workstation check:

```powershell
python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --manual-card-present yes --manual-rfid-off yes --output out\cyberjack-readiness.json
```

Use `--strict` in automation when any non-ready state should return a non-zero exit code. The generated JSON follows `contracts/readiness-evidence.schema.json` and records only metadata: local component status, manual attestations, anonymized reader fingerprints, localhost XNP port reachability and AusweisApp status reachability.

The check does not read PINs, card values, certificates, XNP API keys, portal sessions or mandate content. RFID-off is captured as a manual attestation until a reviewed vendor or operating-system interface can verify it deterministically.

## Windows DriverPackage Detection

On Windows, the readiness check now detects the local REINER SCT stack at the standard path:

```text
C:\Program Files\REINER SCT\DriverPackage
```

It checks for the DriverPackage control center, PC/SC library, Windows 10 x64 driver files, CT-API DLL and the installed REINER SCT SmartCardReader provider reported by `pnputil`. Connected reader hardware is checked separately. A successfully installed DriverPackage does not by itself prove that a cyberJack reader is currently attached.

## morris Browser Middleware

REINER SCT describes morris as middleware that allows browser applications to access the chip-card reader from the local customer PC. Where morris is installed, the readiness check now verifies the local middleware without invoking any card operation:

- `C:\Program Files (x86)\REINER SCT\morris`
- `morris` Windows service state
- `morrisServer` and `morrisDispatcherService` processes
- local named-pipe endpoints such as `net.pipe://localhost/morris`

This can be the easier integration path for browser-guided operator checks, but it stays local and metadata-only in NoC. The plugin must not use morris to request PINs, card data, certificates or productive portal actions.

## Linux Driver And Omnistation Lab

REINER SCT documents Linux support for cyberJack readers and notes that many Linux distributions already provide cyberJack drivers in their standard package repositories. On Linux, the readiness check now also probes the local driver stack:

- `cyberjack` package presence where a Debian/Ubuntu or RPM package database is available.
- `pcscd`, `pcsc-tools` and `libccid`/PCSC package signals where available.
- USB visibility via `lsusb`.
- PC/SC reader visibility via `pcsc_scan -n`.

Run on the target Linux machine:

```bash
python3 plugins/noc-cyberjack-rfid/scripts/check_readiness.py --json
```

Using Omnistation for this is only meaningful as a controlled hardware lab if the cyberJack USB reader is passed through to the Omnistation desktop. A cloud desktop without USB passthrough cannot verify the physical reader. The repository policy currently says Omnistation is not a NoC execution workspace; using it for this hardware lab therefore requires a documented policy exception or a policy update before driver installation.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Is installable from `.agents/plugins/marketplace.json` before `noc-bnotk-xnp`.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Treats BNotK chip/signature card availability, compatible class-3 reader, SAK lite/XNP, secureFramework and XNP local-interface readiness as the gate before XNP login tests.
- Treats RFID as a reader capability, not as the notarial card workflow. Where the reader has an RFID function, the BNotK guidance is to keep it disabled for chip-card workflows unless a specific contactless use is explicitly needed.
- Produces plan previews and evidence metadata before any sensitive action.
- Produces a local readiness evidence JSON via `scripts/check_readiness.py`.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm BNotK chip/signature card availability without reading card values.
- Confirm security-class-3 reader model, driver source, PC/SC service and local admin path.
- On Windows, confirm REINER SCT DriverPackage path, driver files and installed SmartCardReader provider.
- On Windows, confirm morris browser middleware installation and running local service where available.
- On Linux, confirm cyberJack driver package availability or installation, PC/SC daemon state and USB/PCSC reader visibility.
- Confirm whether the reader has an RFID function and whether it is disabled for the BNotK chip-card workflow.
- Confirm BNotK SAK lite or XNP card path and secureFramework readiness.
- Confirm XNP local web-service interface readiness only as metadata: active/inactive, localhost-only binding, configured port range and whether API-key setup is required. Do not store the API key.

## Day1

- Run `scripts/check_readiness.py` for card-reader, RFID-off, SAK-lite/XNP-card-path, secureFramework and XNP local-interface readiness before XNP login testing.

## Day2

- Recertify card-reader, driver, firmware, PC/SC service, SAK-lite/XNP-card-path and secureFramework readiness.

## Required Accounts And Approvals

- Approved hardware procurement
- BNotK chip/signature card availability
- Security-class-3 card reader
- RFID function disabled where present and not explicitly needed
- BNotK SAK lite or XNP card path
- secureFramework communication path
- XNP local interface configuration reviewed without storing API keys
- Local workstation admin approval
- Driver/vendor support channel

See `docs/de/plugin-operations/account-and-approval-requests.md` and `docs/en/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
