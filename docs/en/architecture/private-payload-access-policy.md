# Private-Payload Access Policy

Status: policy contract without live access
Last content update: 2026-06-28

## Purpose

This page defines the logical access matrix for later private matter payloads.
It extends the [private-payload target design](private-payload-target-design.md)
with roles, purposes, data classes, actions, step-up, human review and audit.

The machine-readable contract lives in
[workflows/contracts/private-payload-access-policy.contract.json](../../../workflows/contracts/private-payload-access-policy.contract.json)
and is checked by
[scripts/validate_private_payload_access_policy.py](../../../scripts/validate_private_payload_access_policy.py).

## Base Rule

This contract does not activate live access. It only describes which access may
become allowed after a private operating frame, privacy approval, role binding,
tenant/matter/purpose binding and owner apply.

Automation must not read private payloads or approve access. Guests have no
default read access. `notoclaw01`, GitHub, the public demo and quality-gate
artifacts always stay blocked for private payloads.

## Role Classes

| Role | Basic permission shape |
| --- | --- |
| `notar_fachlich` | notarial review and approval after step-up and audit |
| `notariatsfachkraft` | casework and preparation; sensitive classes need notarial or owner approval |
| `kostenverantwortung` | cost review with limited financial, property and identification data |
| `revision_audit` | redacted audit and evidence view, no private payloads |
| `owner` | owner apply and policy exceptions, without bypassing privacy or audit boundaries |
| `automation` | evaluate policy metadata, record denials and write redacted audit |
| `client_guest_user` | upload link or own document status after a separate secure-document gate |

## Access Purposes

Access is purpose-bound. The contract knows:

- notarial review,
- casework preparation,
- cost review,
- matter attachment,
- external upload,
- redacted audit,
- owner apply,
- incident response.

Every access needs a grant with expiry, revocation, role class, purpose, audit
event and attestation that no private payload was written to GitHub or target
control.

## Global Denials

The always-denied cases are:

- reading, writing or exporting private payloads through GitHub, `notoclaw01`,
  the public demo or quality-gate artifacts,
- private-payload approval by automation,
- default read access for guests or auditors,
- browsing private payloads without matter and purpose binding.

## Evidence Form

Access evidence contains metadata only:

- `grant_id`,
- `payload_id`,
- `tenant_id`,
- `matter_id`,
- `role_class`,
- `purpose`,
- `data_classes`,
- `decision_status`,
- `decision_reason`,
- `expires_at`,
- `revocation_status`,
- `step_up_status`,
- `human_review_ref`,
- `audit_event_ref`,
- `no_github_payload_attestation`,
- `no_target_control_payload_attestation`.

The evidence is not a payload transport. It only records decision, purpose and
boundary.
