# Private-Payload Target Design

Status: logical design without apply
Last content update: 2026-07-06

## Purpose

This page describes the first logical target model for later private matter
payloads. It follows the
[private operating frame](private-operating-frame-gate.md), but it does not
activate productive storage, a DDL artifact or access to real matter data.

The machine-readable contract lives in
[workflows/contracts/private-payload-target-design.contract.json](../../../workflows/contracts/private-payload-target-design.contract.json)
and is checked by
[scripts/validate_private_payload_target_design.py](../../../scripts/validate_private_payload_target_design.py).

## Design Decision

NaC models private payloads as an envelope and pointer architecture:

- The envelope only holds binding, purpose, data class, storage target,
  pointer, hash, key reference, retention, access policy and audit.
- The private content is not stored in Git, GitHub artifacts, local target
  control or M365/SharePoint metadata lists without the private-payload gate.
- Access runs through purpose-bound access grants with expiry, revocation,
  role class, step-up and human review.
- Documents are referenced as encrypted objects or local specialist-system
  objects; NaC stores only redacted metadata for them.

The matching role, purpose and access matrix is defined in
[private-payload-access-policy.md](private-payload-access-policy.md).

This keeps the architecture checkable without placing a private payload in the
repository.

## Logical Components

| Component | Role | Content |
| --- | --- | --- |
| `private_payload_envelope` | metadata and policy shell | payload ID, tenant, matter, purpose, data class, storage target, pointer, hash, key, retention, access and audit references |
| `private_payload_access_grant` | purpose-bound access decision | role, purpose, expiry, revocation, step-up, human-review and audit references |
| `encrypted_document_object_pointer` | document reference without content | storage target, object pointer, hash, MIME class, scan, retention and audit reference |
| `redacted_private_payload_audit` | append-only evidence | event type, decision status, role class, purpose and attestation without payload |

None of these components contains plaintext payloads.

## Storage Targets

| Target | Status | Job |
| --- | --- | --- |
| Private-payload metadata store | future schema design | envelopes, access grants and redacted audit events. |
| Microsoft-365 protected document storage | future storage design | matter-bound document libraries, versions, hashes, short-lived links and redacted access evidence. |
| Encrypted object-storage payloads | future storage design | document objects, hashes and short-lived access paths. |
| On-prem private store | future integration design | local DMS/specialist-system references and redacted evidence back to NaC. |

## Still Blocked

Until a separate owner apply gate, the blocked actions are:

- creating private payload tables,
- writing or reading private payloads,
- issuing private document links,
- projecting private payloads into graphs,
- connecting live DMS or specialist systems,
- running migrations with real matter data.

## Relation To The Graph Model

Graph and ontology work may continue only over metadata. A graph can show
process dependencies, gates, roles, deadlines and audit relationships. Private
payloads themselves are not projected into the graph. If a later private graph
relation is needed, it must use envelope IDs, classification, purpose binding
and redacted audit edges.

## Next Step

The next step is not an apply. It is a review of the control questions:

- which data class needs which storage target,
- which roles may request which access,
- which retention and deletion rules apply,
- which key and backup boundaries apply,
- which evidence is sufficient for the notary office, privacy and operations.
