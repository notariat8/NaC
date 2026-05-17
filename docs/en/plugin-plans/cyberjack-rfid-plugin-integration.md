# Card / cyberJack RFID Plugin Integration Plan

Status: `active`

## Goal

`noc-cyberjack-rfid` is the local `NoC Karten- und SAK-Pruefung` before XNP and other
notary-side workflows. The plugin checks whether the local workstation can see
the REINER SCT/cyberJack stack and whether the surrounding card-reader
prerequisites are plausible.

The plugin is allowed to return "no reader connected". That is a valid
readiness result and still proves that the local integration path works.

## Product And Interface Situation

The local Windows workstation can contain:

- REINER SCT DriverPackage, for example under
  `C:\Program Files\REINER SCT\DriverPackage`,
- cyberJack driver files, CT-API/PCSC components and the Windows smart-card
  reader provider,
- optional browser middleware such as morris,
- later a physical cyberJack reader and BNotK or compatible card.

For current development, the physical reader is not required. The plugin must
reach the local driver or morris gateway and distinguish "stack reachable, no
reader connected" from "stack not reachable".

## Leading Decision

The first implementation path is a **local companion**:

- local checks run on the user's workstation,
- the plugin records readiness and evidence metadata only,
- card, PIN and certificate material remain outside Git,
- XNP and notarial actions stay behind later approval gates.

Omnistation is not an execution location for this plugin.

## Plugin Roles

### Local Plugin

The local plugin may:

- check known REINER SCT installation paths,
- check Windows smart-card provider hints,
- query morris or a local loopback endpoint when available,
- detect whether a reader is connected,
- report "driver/middleware reachable but no reader connected",
- write redacted readiness evidence.

The local plugin must not:

- capture PINs,
- export private keys or certificates,
- read cardholder personal data into Git,
- submit notarial actions,
- bypass XNP or SAK security boundaries.

### NoC SaaS

NoC SaaS may:

- receive redacted readiness status,
- evaluate policy gates for follow-up workflows,
- store evidence metadata.

NoC SaaS must not:

- receive card secrets, PINs or private keys,
- reuse eID/card results for unrelated purposes,
- directly operate local hardware without explicit local consent.

## Proposed Plugin API

### Minimal Tools

- `card.readiness`
  - checks driver paths, morris availability and PC/SC hints.
- `card.reader_status`
  - returns reader connected/not connected/unknown.
- `card.middleware_status`
  - checks morris or equivalent browser middleware.
- `card.evidence`
  - returns redacted metadata for Git evidence.

### Later Optional Tools

- `card.sak_readiness`
- `card.xnp_path_check`
- `card.firmware_status`
- `card.day2_followup`

These later tools require separate review before any deeper card interaction.

## Evidence Data Model

Default evidence:

- `workstation_id_hash`
- `os_family`
- `driver_package_detected`
- `driver_package_path`
- `morris_detected`
- `pcsc_status`
- `reader_connected`
- `reader_model`
- `checked_at_utc`
- `tool_version`
- `redaction_status`

Personal attributes, card data, PINs, private keys and certificates are never
part of the default evidence object.

## MVP Scope

The MVP includes:

1. Windows readiness check for REINER SCT DriverPackage path.
2. Check for core driver or smart-card provider hints.
3. Optional morris loopback or browser-middleware status check.
4. Reader status with valid "no reader connected" result.
5. Redacted evidence output.
6. Human-readable readiness summary.

## Not In The MVP

- PIN prompt.
- Certificate export.
- Qualified signature.
- XNP login.
- Direct SAK operation.
- eID attribute release.
- Automated notarial filing.

## Security Requirements

- Debug logs use redaction by default.
- The user must consciously confirm any future attribute release.
- No secrets or personal card data in Git.
- Local workstation checks are separated from SaaS evidence.
- Follow-up workflows require explicit policy gates.

## Provider Runbook

1. Confirm local development remains on the user's workstation.
2. Confirm REINER SCT DriverPackage installation path.
3. Confirm morris installation or non-availability.
4. Run readiness check without physical reader.
5. Treat "no reader connected" as acceptable if the stack is reachable.
6. Only after plugin availability, test with physical reader.

## Tenant Onboarding Runbook

1. Confirm operating system and workstation profile.
2. Install REINER SCT driver package or vendor-supported equivalent.
3. Install morris if the browser-middleware path is chosen.
4. Run `card.readiness`.
5. Document redacted evidence.
6. Proceed to `noc-bnotk-xnp` only when `NoC Karten- und SAK-Pruefung` is green or explicitly
   waived for preflight.

## Implementation Phases

### Phase 0: Research And Spike

- Check official REINER SCT driver and morris behavior.
- Verify local filesystem and loopback access.

### Phase 1: MVP

- Implement readiness, middleware and reader-status tools.
- Return structured JSON plus human-readable summary.
- Add tests for installed stack, missing stack and no-reader state.

### Phase 2: XNP Gate Integration

- Feed readiness result into `noc-bnotk-xnp`.
- Record approval and evidence references.

### Phase 3: SaaS Binding

- Store only redacted readiness metadata.
- Add drift checks after driver, OS or browser updates.

### Phase 4: Extended Card Cases

- Evaluate beA/BNotK and signature cases separately.
- Add only after legal, security and vendor review.

## Open Decisions

- Which morris endpoint or browser integration is stable enough for MVP?
- Should PC/SC checks use Windows native APIs, PowerShell, Python packages or a
  small helper binary?
- Which evidence fields are sufficient for a notary-office pilot?
- Which physical reader models are supported first?

## Acceptance Criteria For The First PR

- The plugin can detect installed REINER SCT DriverPackage on Windows.
- The plugin can report morris availability or non-availability.
- The plugin can return "no reader connected" as valid diagnostic response.
- No card data, PINs, certificates or personal data are written.
- The XNP plugin can consume the readiness result.

## Sources

- REINER SCT driver information and local installation.
- REINER SCT morris software information.
- BNotK/XNP integration context:
  [bnotk-xnp-notariatssoftware.md](bnotk-xnp-notariatssoftware.md)
