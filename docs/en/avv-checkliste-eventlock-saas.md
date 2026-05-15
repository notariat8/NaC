# DPA Checklist For EventLock SaaS, Function8 As Processor

## Purpose

This checklist helps prepare the data processing agreement under Art. 28 GDPR
for the EventLock-as-a-Service model in a structured and evidence-ready way. It
applies analogously to all other Function8 services that are classified as
processor services.

Note: this is an operational guide and does not replace legal advice.

## When Is A DPA Required?

A DPA is usually required when:

- Function8 processes eventstream or journal data for the customer,
- the customer determines the purposes and means of processing,
- personal data or personal metadata may be affected.

## Core Contract Contents

- Subject and duration of processing.
- Nature and purpose of processing.
- Categories of personal data.
- Categories of data subjects.
- Rights and obligations of the controller.
- Documented instruction binding.

## Technical And Organizational Measures

- Tenant-separated subinstance per customer.
- Dedicated key per customer.
- Immutable retention or WORM per customer.
- Role-based access on a need-to-know basis.
- Logging and audit-proof event chain.
- Key rotation and incident process.
- Four-eyes approval for critical changes such as retention or legal hold.

## Subprocessors And Cloud Locations

- Name the cloud platforms used, for example AWS, Azure, GCP or OCI.
- Name concrete services, for example broker, WORM store or KMS.
- Document locations and regions.
- Regulate the change procedure for subprocessors contractually.

## Third-Country Transfer

- Check whether data is processed outside the EU/EEA.
- If yes, document suitable safeguards such as SCCs.
- Document the transfer impact assessment.

## Data Subject Rights And Support Processes

- Access, rectification, erasure and restriction: process and SLA.
- Clear contact person on provider and customer side.
- Evidence of how instructions are implemented.

## Incident And Notification Duties

- Contractually define the first-notification deadline to the customer.
- Standardize notification content: scope, effect, countermeasures.
- Document the joint escalation chain.

## Audit And Evidence

- Clearly regulate the customer's audit right: remote/on-site and notice
  periods.
- Define the evidence package:
  - architecture,
  - TOM evidence,
  - access logs,
  - restore and integrity tests.
- Define the cadence for regular audits.

## Termination And Data Return

- Define return format and deadlines.
- Define deletion process after contract termination.
- Define handling of statutory retention obligations.
- Treat legal-hold cases separately.

## Role Model: Function8 vs Customer

- Function8:
  - platform operation, security baseline, SLA operation.
- Customer:
  - data classification, legal-hold decisions, approval of audit scope.

Reference:
[docs/en/service-model/tenant-ownership-and-eventlock-service.md](service-model/tenant-ownership-and-eventlock-service.md)

## Operational Approval Before Go-Live

- [ ] DPA signed.
- [ ] Subprocessor list complete and confirmed.
- [ ] TOM annex approved.
- [ ] Regions and transfer rules approved.
- [ ] Incident notification process tested.
- [ ] Audit process and contacts documented.
- [ ] Retention/legal-hold owner named.
