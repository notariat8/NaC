# beA Portal Plugin Integration Plan

Status: `draft`

## Goal

This plan defines how NoC can support workflows around the German special
electronic attorney mailbox, `beA`, without bypassing the official client
security, mailbox ownership or professional responsibility model.

The target is a local companion that checks readiness, prepares send/receive
workflows, records evidence metadata and supports later integration decisions.
It is not a portal-scraping or autonomous filing tool.

## Source And Integration Anchors

- beA is the regulated electronic mailbox for lawyers in Germany.
- The beA Client Security boundary and mailbox access model remain binding.
- Any direct integration path must be checked against the official beA and
  professional-software terms.
- eEB, export, receipt and dispatch evidence must be handled with clear
  retention and responsibility.

## Leading Decision

The first implementation path is a **local companion**:

- it checks local workstation prerequisites,
- it structures the workflow and evidence package,
- it keeps user actions in the official beA/client-security path,
- it records only metadata, hashes and attestations by default.

Direct mailbox automation or dispatch automation is out of scope until legal,
technical and professional responsibility have been approved in writing.

## Plugin Boundaries

The plugin may:

- check local prerequisites for beA and Client Security,
- create plan previews for send, receive, export and eEB workflows,
- prepare checklists and approval gates,
- record evidence metadata such as timestamp, case ID, hash and user
  attestation,
- make missing prerequisites visible.

The plugin must not:

- store mailbox credentials, cards, PINs or private keys,
- send, receive or acknowledge beA messages without explicit approved adapter
  scope,
- bypass beA Client Security,
- scrape protected portal content,
- store real mandate content in the repository,
- replace professional responsibility or human approval.

## Integration Paths

### Path A: Local Companion For The beA Web Application

This is the MVP path. The user works in the official beA environment while NoC
tracks readiness, workflow state, approvals and evidence.

### Path B: Law-Firm Software Interface Or KSW Toolkit

This path is evaluated only after vendor/interface terms are known. It may be
appropriate where the law-firm software already exposes a supported interface.

### Path C: Export/Import Bridge

This path imports exported evidence, hashes documents and links metadata to a
NoC matter. It remains metadata-first and avoids uncontrolled content storage.

## Proposed Plugin API

### Readiness And Diagnosis

- `bea.readiness`
- `bea.client_security_status`
- `bea.mailbox_prerequisites`
- `bea.export_path_check`

### Process Preparation

- `bea.send_plan`
- `bea.receive_plan`
- `bea.eeb_plan`
- `bea.export_evidence_plan`

### Evidence And Audit

- `bea.evidence_record`
- `bea.hash_document`
- `bea.attestation`
- `bea.day2_followup`

Later optional functions require a separate reviewed connector scope.

## Evidence Data Model

Default evidence is metadata-only:

- `case_id`
- `workflow_type`
- `mailbox_role`
- `actor_role`
- `action_time_utc`
- `document_hash`
- `source_system`
- `attestation_text`
- `approval_ref`
- `retention_class`
- `legal_hold`

Message content is stored only when a customer policy explicitly allows it and
defines purpose, retention, access control and export path.

## NoC Process Model

Typical states:

- `draft`
- `readiness_checked`
- `approval_needed`
- `ready_for_bea_action`
- `user_action_completed`
- `evidence_recorded`
- `day2_followup`

## MVP Scope

- Local readiness check.
- Send/receive/eEB plan preview.
- Evidence metadata and hash model.
- Human approval gates.
- Support runbook for missing Client Security, mailbox access and export path.

## Not In The MVP

- Direct sending or receiving.
- PIN, card or credential handling.
- Full mailbox synchronization.
- Scraping protected beA portal content.
- Autonomous legal or professional decisions.

## Security Requirements

- No secrets in Git.
- Redaction by default in logs.
- Hash-first evidence for documents.
- Tenant and case separation.
- Four-eyes approval for sensitive dispatch or acknowledgement workflows.

## Provider Runbook

1. Confirm customer usecase and professional responsibility boundary.
2. Confirm local workstation prerequisites.
3. Confirm evidence storage and retention policy.
4. Confirm support channel for Client Security issues.
5. Enable the companion only after approval gates are documented.

## Tenant Onboarding Runbook

1. Identify mailbox owners and authorized users.
2. Confirm local Client Security installation.
3. Define eEB/export/dispatch workflows.
4. Define retention and DMS target.
5. Run the readiness check.
6. Execute first workflow manually in official beA and record evidence.

## Implementation Phases

1. Legal and technical discovery.
2. Companion MVP with readiness and plan preview.
3. Evidence and archive import.
4. Law-firm software or KSW interface assessment.
5. Productive integration path after separate approval.

## Open Decisions

- Which beA operating mode is used first: web, law-firm software, or export
  bridge?
- Which DMS or evidence store is authoritative?
- Which message content, if any, may be stored outside the official system?
- Which role can approve eEB or dispatch workflows?

## Acceptance Criteria For The First PR

- Plugin plan and manifest exist.
- Readiness output is metadata-only.
- No credentials, PINs, mailbox IDs or mandate content are stored.
- Evidence model contains hash, case, actor, time and approval reference.
- The first workflow remains a local companion workflow.
