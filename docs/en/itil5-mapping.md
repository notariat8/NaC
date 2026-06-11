# ITIL 5 Mapping For NaC

## Purpose

This document maps `NaC` to ITIL 5. It is not a certification or maturity
claim. It is a bridge for conversations with IT leadership, audit, privacy,
operations owners and notary offices that expect IT service management
language.

NaC remains governed by:

- notarial responsibility,
- privacy and AVV/DPA gates,
- QMS/ISO 9001 evidence,
- `Notariat as Code` and `Enterprise GitOps`,
- versioned policies, pull requests, reviews, releases and the event journal.

ITIL 5 is therefore an interoperability and review language for NaC, not an
additional control regime.

## Source State

Reviewed on 2026-06-11:

- PeopleCert ITIL Framework:
  [peoplecert.org/Frameworks-Professionals/ITIL-framework](https://www.peoplecert.org/Frameworks-Professionals/ITIL-framework)
- PeopleCert ITIL Certifications:
  [peoplecert.org/browse-certifications/it-governance-and-service-management/ITIL-1](https://www.peoplecert.org/browse-certifications/it-governance-and-service-management/ITIL-1)

PeopleCert describes ITIL as a framework for digital product and service
management, AI-native governance, integrated lifecycles, experience,
governance, measurable value and continual improvement. These terms are useful
for NaC because the project already combines service, product, governance,
evidence and operation surfaces for notarial work.

## Short Conclusion

ITIL 5 matters for NaC, but not as a new mandatory process.

| Effect | NaC interpretation |
| --- | --- |
| Notary-office and IT leadership language | Helps explain NaC as an operable digital service, not only as a repository. |
| Operation and third-party operation | Important for service catalog, incidents, SLA/SLO, change, evidence and exit. |
| AI governance | Fits AI-SBOM, human review, privacy boundaries and the auditable control plane. |
| Auditability | Complements QMS/ISO 9001 evidence, but does not replace it. |
| Certification | Do not claim organizational certification; ITIL certificates relate to people and roles. |

## Mapping

| ITIL 5 term | NaC artifacts | State | Next useful addition |
| --- | --- | --- | --- |
| Digital Product and Service Management | [docs/en/README.md](README.md), [docs/en/service-model/README.md](service-model/README.md), [docs/en/architecture.md](architecture.md) | NaC already describes product core, service boundaries and control plane together. | Explain NaC in notary-office conversations as digital product and service operation, not only as an automation repository. |
| Service catalog | [docs/en/service-model/function8-service-catalog.md](service-model/function8-service-catalog.md) | Operating services, DPA relevance, runbooks and portability are named. | Add `service_owner`, support path, SLO class and escalation path per service. |
| Service ownership and tenant boundary | [docs/en/service-model/tenant-ownership-and-eventlock-service.md](service-model/tenant-ownership-and-eventlock-service.md), [policies/tenant-ownership-policy.yaml](../../policies/tenant-ownership-policy.yaml) | Operating and notary-office responsibilities are separated. | Add a compact RACI per service for production notary-office subinstances. |
| Change enablement | [docs/en/governance.md](governance.md), [policies/process-policy.yaml](../../policies/process-policy.yaml), [docs/en/operations/release-sync-playbook.md](operations/release-sync-playbook.md) | Change requests, pull requests, reviews, risk gates and release syncs are established. | Use the ITIL term `Change Enablement` as an alias in notary-office and audit material. |
| Release management | [docs/en/operations/release-checklist.md](operations/release-checklist.md), [docs/en/operations/parallelbetrieb-version-binding.md](operations/parallelbetrieb-version-binding.md), [docs/en/operations/oci-runtime.md](operations/oci-runtime.md) | Release, tag, rollout, fallback state and version binding are documented. | Link production release notes consistently to service impact, risks and rollback. |
| Incident management | [docs/en/issues/taxonomy.md](issues/taxonomy.md), [docs/en/security-and-dsgvo.md](security-and-dsgvo.md), [policies/data-protection-policy.yaml](../../policies/data-protection-policy.yaml) | Incident issues, privacy incidents and security paths are present. | Add a short incident playbook with severity, first response, escalation and closure criteria. |
| Problem management | [qms/nonconformities.schema.json](../../qms/nonconformities.schema.json), [qms/audit-program.md](../../qms/audit-program.md), [qms/management-review.md](../../qms/management-review.md) | Nonconformities, corrective actions and effectiveness checks exist in the QMS layer. | Mirror recurring incidents explicitly as problems or corrective actions in the QMS layer. |
| Monitoring and event evidence | [docs/en/eventstream/revisionssicherheit.md](eventstream/revisionssicherheit.md), [docs/en/eventstream/implementation-templates.md](eventstream/implementation-templates.md), [policies/revisionssicherheit-eventstream-policy.yaml](../../policies/revisionssicherheit-eventstream-policy.yaml) | Append-only journal, hash chain, WORM store, anchoring and evidence index are the target model. | Document operating metrics for ingest lag, anchor errors, DLQ and restore tests per service. |
| Service level management | [docs/en/service-model/tenant-ownership-and-eventlock-service.md](service-model/tenant-ownership-and-eventlock-service.md), [docs/en/avv-checkliste-eventlock-saas.md](avv-checkliste-eventlock-saas.md) | SLA/SLO is mentioned, but not yet maintained as a standardized table. | Define service level classes for pilot, production and audit-proof evidence operation. |
| Supplier and third-party management | [docs/en/service-model/third-party-operations-and-exit.md](service-model/third-party-operations-and-exit.md), [policies/provider-open-services-policy.yaml](../../policies/provider-open-services-policy.yaml) | Third-party operation, exit and replaceability are documented explicitly. | Mirror supplier review checkpoints per external platform or subprocessor in DPA and third-party-operation material. |
| AI governance | [docs/en/sbom-for-ai.md](sbom-for-ai.md), [docs/en/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md), [docs/en/codex-parallel-review-workflow.md](codex-parallel-review-workflow.md) | AI touchpoints, model/data/infrastructure transparency, human review and privacy gates are prepared. | For production AI surfaces, maintain review metrics, model change paths and drift/error rates as release evidence. |
| Continual improvement | [qms/quality-objectives.json](../../qms/quality-objectives.json), [qms/audit-program.md](../../qms/audit-program.md), [qms/management-review.md](../../qms/management-review.md), [roadmap/GANTT.md](../../roadmap/GANTT.md) | Quality objectives, internal audits, management review and roadmap form the improvement loop. | Classify improvement actions from incidents, audits and notary-office feedback consistently as issues. |

## Consequence For Audit-Proof NaC Operation

For audit-proof event evidence in NaC operation, ITIL 5 is most directly
relevant. Before productive use with personal data, the service catalog should
make at least these ITIL-compatible operating fields visible:

- `service_owner`
- `notary_office_owner`
- `support_channel`
- `incident_severity_model`
- `initial_response_target`
- `service_level_class`
- `change_window`
- `rollback_or_fallback_path`
- `evidence_and_audit_path`
- `exit_path`

These fields do not change the NaC architecture. They make clear who acts
during incidents, changes, audits, third-party-operation changes and
notary-office approvals.

## What We Do Not Do

- Do not claim that NaC or notariat8 is ITIL certified.
- Do not replace ISO 9001, privacy, professional law or notarial
  responsibility with ITIL.
- Do not add process bureaucracy for small documentation or reference-repo
  changes.
- Do not store real mandate data, secrets or confidential incident details in
  the public repository.

## Recommended Next Steps

| Priority | Task | Outcome |
| --- | --- | --- |
| P0 | Use this mapping as orientation in notary-office, review and service conversations. | Shared language without framework overhead. |
| P1 | Extend the service catalog with ITIL-compatible operating fields for audit-proof NaC operation. | Operation becomes easier to review. |
| P1 | Add an incident playbook for NaC operation and notary-office environments. | Severity, reporting path and closure are clear. |
| P2 | Define SLO classes for pilot, production and audit-proof evidence operation. | SLA/DPA conversations become more concrete. |
| P2 | Mirror recurring incidents and notary-office feedback into QMS nonconformities and management review. | Continual improvement is closed with evidence. |
