# Matter Data Classification And Redaction

Status: metadata-only boundary contract
Last content update: 2026-07-06

## Purpose

This page defines data classification between NaC GitOps, `notoclaw01` target
control, web-app status, M365/SharePoint metadata, redacted evidence and later
private runtime stores. It defines when a value is still safe process metadata
and when it becomes matter data that needs a separate private operating frame.
Earlier ATP metadata slices are archived legacy references, not active MVP
storage.

The machine-readable contract lives in
[workflows/contracts/matter-data-classification-redaction.contract.json](../../../workflows/contracts/matter-data-classification-redaction.contract.json)
and is checked by
[scripts/validate_matter_data_classification_redaction.py](../../../scripts/validate_matter_data_classification_redaction.py).

## Base Rule

GitHub, the product repository, the public demo, the protected start status,
M365/SharePoint metadata lists and local target-control smokes do not store
real matter data. They may only hold process metadata, synthetic examples,
policy references, hashes, pointers and redacted evidence.

Real matter content starts as soon as participants, property, registers, land
registers, payments, family or estate context, documents or identity data are
involved. Such data may be processed only after a separate private operating
frame, privacy/DPA review, role, tenant, matter and purpose binding,
encryption, retention and owner gates.

## Data Allowed Before The Private Gate

- `safe_metadata_only`: status, gate, process, template, role and audit data
  without private content values.
- `synthetic_demo_data`: clearly synthetic examples under the data protection
  policy.
- `policy_reference`: references to rules, runbooks, contracts and docs.
- `validation_evidence_without_secret_values`: validation results without
  secret values or raw content.
- `redacted_evidence_metadata`: redacted evidence with purpose, role, time,
  source and attestation.
- `approved_public_source_reference`: approved public source reference without
  matter binding.
- `hash_or_pointer_without_private_payload`: hash or pointer without embedded
  private payload.

## Data Blocked Before The Private Gate

The blocked classes include:

- real matter, deed, upload and document full text,
- identity, eID and identification raw data,
- register and land-register raw data,
- property, real-estate, purchase-price, account, payment and tax data,
- real family, estate, health, care or precautionary-power data,
- personal identifiers without a separate gate,
- external payloads from specialist systems, portals, uploads or provider APIs,
- tokens, credentials, card raw data, certificate secrets and provider claim
  dumps.

## Surfaces

| Surface | Boundary |
| --- | --- |
| Product repo and GitHub | Only source artifacts, policies, synthetic examples and redacted evidence. Private payloads are not allowed here. |
| Local target-control smokes | Only manifests, smokes, stubs and non-sensitive evidence. When private payloads are needed, work is handed back to the Project Manager. |
| Web-app start status | Only protected status without matter data. The full workspace stays closed until the private gate. |
| M365/SharePoint metadata layer | Only safe runtime metadata, events, bindings, hashes and pointers without raw content. Private payloads need a separate storage, role and apply gate. |
| Secure document link evidence | Only purpose, expiry, binding, revocation, audit and hash/pointer. Document content stays outside evidence. |

## Redaction Evidence

Every redacted evidence record must include at least:

- `schema_version`,
- `payload_type`,
- `redaction_class`,
- `purpose`,
- `tenant_binding`,
- `matter_binding_status`,
- `role_class`,
- `checked_at`,
- `checked_by_role`,
- `source_system_label`,
- `hash_or_reference`,
- `no_secret_attestation`,
- `no_matter_data_attestation`,
- `audit_event_ref`.

This evidence does not prove private content. It proves that a boundary was
checked and that no secrets or matter data were moved to the wrong surface.

## Relation To Local Smokes And M365

Local sidecars or target-control smokes may hold agents, connector stubs and
workstation checks. That does not make them the matter-data store or the source
of NaC contracts. The M365/SharePoint metadata layer may hold only metadata,
events, bindings, hashes and pointers in the MVP. Graph or ontology work can
build on that layer, but it must exclude matter content until the private gate
is approved.

The split stays clear:

- NaC GitOps owns contracts, BPMN, KG, policies, tests and PRs.
- local sidecars own workstation smokes and non-sensitive evidence.
- A later private runtime store may hold real matter data only after explicit
  owner, privacy, security and role gates under
  [private-operating-frame-gate.md](private-operating-frame-gate.md).
