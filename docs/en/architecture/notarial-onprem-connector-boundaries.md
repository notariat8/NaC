# Notarial On-Prem Connector Boundaries

Status: contract boundary without live apply
Last content update: 2026-06-28

## Purpose

This page describes the first verifiable boundary for XNP/SNP, XNotar, local
card workstation and register paths in the NaC on-prem target model. It turns
the prepared `notoclaw01` stubs from the
[NaC on-prem agent runtime](nac-onprem-agent-runtime.md) into a
machine-readable NaC contract without claiming production specialist-system
coupling.

The contract is
[workflows/contracts/notarial-onprem-connector-boundaries.contract.json](../../../workflows/contracts/notarial-onprem-connector-boundaries.contract.json)
and is validated by
[scripts/validate_notarial_onprem_connector_boundaries.py](../../../scripts/validate_notarial_onprem_connector_boundaries.py).

## Core Rule

At this boundary, NaC is the BPMN, audit and evidence frame. The actual
specialist-system action remains in the designated local notarial work
environment.

Allowed:

- local readiness checks,
- redacted status or user attestations,
- BPMN gates and dependencies,
- evidence without matter data, PINs, tokens, raw card data or certificate
  secrets,
- test-environment planning without production filing.

Blocked:

- production dispatch to registers, land registers or other specialist systems,
- remote control of XNP, XNotar, card readers or signature steps,
- automated data intake from XNP/XNotar into NaC,
- storage of credentials, PINs, card values, certificate contents, raw register
  data or matter content,
- any write action without a separate private operating frame, privacy review,
  human approval and owner gate.

## Connector Boundaries

| Connector | Allowed NaC status | Blocked boundary |
| --- | --- | --- |
| XNP/SNP and XNotar | External access point, local readiness, redacted status attestation, BPMN gate | no direct production coupling, no NaC-controlled dispatch, no raw-data intake |
| cyberJack/card workstation | local hardware, PC/SC, morris and card-path readiness | no PIN capture, no signature trigger, no card or certificate readout |
| Register and land register | external status and wait-gate modeling, redacted package or callback attestation | no production filing, no retrieval or storage of raw register or land-register data |

## Evidence Shape

Evidence at this boundary is redacted metadata only:

- `connector_id`,
- `readiness_status`,
- `checked_at`,
- `checked_by_role`,
- `source_system_label`,
- `redaction_class`,
- `no_secret_attestation`,
- `no_matter_data_attestation`,
- `human_review_status`,
- `audit_event_ref`.

Evidence must not contain a technical secret or real matter content. Local
paths, operating details, production endpoints, tokens and personal details
stay outside the product repository.

## Relation To notoclaw01

`notoclaw01` may validate connector stubs and smokes in
`/home/ubuntu/nac-target-control`. As soon as real connector details,
credentials, specialist-system access or production write actions are needed,
the Target Operator scope ends. The Project Manager on `brev01` then handles
GitOps, review, privacy clarification and owner gates.

## Next Approvals

This contract is enough only for architecture, tests and local readiness
stubs. Before production connectors, every path needs at least:

1. private operating frame with role and responsibility model,
2. privacy/DPA clarification for personal data,
3. test mode and fallback path,
4. human subject-matter approval,
5. owner apply gate for every production write action.
