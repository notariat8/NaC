# Private Operating Frame And Private-Payload Gate

Status: boundary contract without productive apply
Last content update: 2026-06-28

## Purpose

This page defines what must happen before real matter data may leave the NaC
metadata-only boundary. It extends the
[matter-data classification](matter-data-classification-redaction.md) with the
private operating frame for later ATP private-payload schemas, encrypted
document storage or local specialist-system/DMS paths.

The machine-readable contract lives in
[workflows/contracts/private-operating-frame-gate.contract.json](../../../workflows/contracts/private-operating-frame-gate.contract.json)
and is checked by
[scripts/validate_private_operating_frame_gate.py](../../../scripts/validate_private_operating_frame_gate.py).

## Decision

This contract does not activate productive processing. It is a gate: until it
is fulfilled with concrete privacy, security, role, retention and owner
evidence, real matter data remains excluded from GitHub, `notoclaw01`, the
public demo, quality-gate artifacts and metadata-only ATP slices.

After this gate, private runtime designs can be created. That may be a separate
ATP private-payload schema, encrypted object storage or a local specialist
system/DMS path. Each of those paths still needs its own apply or live gate.

The first logical target model for those later designs is defined in
[private-payload-target-design.md](private-payload-target-design.md).

## Minimum Controls

Before productive processing, the minimum requirements are:

- recorded owner decision,
- privacy/DPA review and DSFA screening,
- role, tenant, matter and purpose binding,
- field classification and private payload schema,
- encryption at rest and in transit,
- key management,
- retention and deletion concept,
- access review,
- append-only audit,
- data-subject rights process,
- incident-response and backup/restore boundary,
- test-data and production-data separation,
- human review before subject-matter attachment.

## Blocked Without Gate

Without this private operating frame, the blocked actions are:

- productive processing of personal matter data,
- storing deed, document, identity, register or land-register raw data,
- XNP or XNotar payloads,
- private secure-document links,
- ATP private-payload schema apply,
- object-storage document writes,
- local DMS or specialist-system writes,
- graph projections over private payloads.

## Storage Targets

| Target | Status | Minimum boundary |
| --- | --- | --- |
| ATP private-payload schema | future design | tenant, matter, purpose, role, encryption, retention, audit and owner apply gate |
| Encrypted document storage | future design | document classification, short-lived link, revocation, malware/file-type check, retention, audit and human review |
| On-prem DMS or specialist system | future design | local operator boundary, credential vault, human review, no remote control by default, redacted evidence back to NaC |

## Evidence Form

Gate evidence contains metadata only:

- `gate_id`,
- `decision_status`,
- `decided_at`,
- `decided_by_role`,
- `scope`,
- `data_classes`,
- `storage_target`,
- `tenant_binding`,
- `matter_binding`,
- `purpose_binding`,
- `retention_policy_ref`,
- `encryption_policy_ref`,
- `access_policy_ref`,
- `audit_event_ref`,
- `no_github_payload_attestation`,
- `no_target_control_payload_attestation`.

The evidence must not contain the private payload itself. It only records that
the approval boundary has been met.

## Relation To ATP And NemoClaw

ATP remains metadata-only until a separate schema apply. `notoclaw01` remains
target control for smokes, stubs and redacted evidence. This contract does not
automatically turn either surface into a matter-data store.

Only a later, explicitly approved private operating frame may hold real matter
data. NaC GitOps still remains the source for contracts, tests, BPMN, KG,
policies and reviews.
