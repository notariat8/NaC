# Notarkammer Demo: XNP/SNP API And Test Access For ISVs

Status: 2026-06-22

This demo artifact prepares the discussion question for BNotK and the
Notarkammer: which XNP/SNP API or test access does NaC need as an ISV so that
the real estate purchase agreement can be connected to the official notarial
system boundaries in a clean, auditable and data-minimizing way?

The source basis remains the existing
[XNP source matrix](notarkammer-xnp-quellenmatrix.md). It supports XNP,
XNotar, land-register, commercial-register and card-reader references as the
notarial operating environment, but it does not support a productive NaC
integration claim. This page therefore only formulates the need for test and
API access clarification.

## Primary Real Estate Purchase Agreement Flow

For the Notarkammer demo, the real estate purchase agreement is the primary
flow. NaC uses it to show why an ISV needs more than a polished user interface:
it needs reliable access to test systems, interface agreements and clear
professional boundary definitions.

1. Create the matter and model roles and participant communication only with
   synthetic data.
2. Track draft, documents, approvals and financing as BPMN gates.
3. Mark notarization as a human notarial approval.
4. Track closing in parallel: land register, financing, municipality/tax,
   deletion documents and responses.
5. Show XNP, XNotar, beN, card reader and signature path only as local or
   external professional system boundaries.

The demo goal is not productive automation. The demo goal is to ask the right
questions for a later approved integration path.

## Why NaC Needs Test Access

NaC can already show professional process accountability as BPMN, evidence
gates and audit status. Without official XNP/SNP test access, important details
remain open:

- Which matter, status or evidence objects may ISVs read or write?
- Which test data, test certificates, roles and notarial activity contexts are
  allowed for a real estate purchase agreement?
- Which local workstation checks are permitted without touching PINs, card
  values, tokens, register data or land-register content?
- Which export, import, callback, event or API surfaces are intended for
  evidence and status?
- Which certification, security review, logging and approval does BNotK or the
  responsible chamber require before a pilot?

NaC needs this access as an ISV because the real estate purchase agreement
crosses several official boundaries: XNP workstation, XNotar land-register
path, beN, signature/card reader, return evidence and notarial approvals.
Without a test environment NaC can only name the boundary; with approved test
access NaC can integrate it correctly, with minimal data and auditable status.

## API Questions For BNotK And The Notarkammer

These questions are suitable for the appointment. They deliberately ask for
test and approval paths, not for productive live use.

| Area | Question |
| --- | --- |
| ISV onboarding | Is there an official ISV or vendor program for XNP/SNP test access, including technical contacts, usage terms and security review? |
| Test environment | Is there a dedicated XNP/SNP test environment for real estate purchase agreements, land-register closing, beN status and signature path without real matter or register data? |
| API scope | Which XNP/SNP APIs, local interfaces, export/import formats or event/status mechanisms are documented and approvable for ISVs? |
| Roles and rights | Which test roles, notarial activity contexts, organization assignments and card/certificate profiles may be used in an ISV test environment? |
| Evidence | Which status and evidence fields may be stored in a third-party system when raw documents, matter data and access credentials are not imported? |
| Real estate purchase agreement | Which professional status points of a real estate purchase agreement are suitable for API/evidence integration: priority notice, deletion documents, right of first refusal, tax clearance certificate, transfer of title or beN dispatch status? |
| Land register and register | Are land-register or commercial-register paths limited to XNotar/XJustiz/beN handoffs, or are there additional approved test callbacks or status queries for ISVs? |
| Local workstation | May a local companion check readiness, for example installed components, role status or reachability, as long as no PINs, tokens, card values, document contents or matter data are read? |
| Logging | Which audit fields does BNotK/the chamber expect for test and pilot operation: time, role, system boundary, hash, status, approval, error class? |
| Certification | Which steps are required before a pilot with a notary office or chamber: privacy review, DPA, penetration test, vendor approval, chamber approval, BNotK acceptance? |
| Operations | Which separation is required between test, pilot and production access, and how are keys, certificates, client IDs or local configurations issued and revoked? |
| Support | Which error classes and escalation paths should ISVs use when XNP/SNP test access, beN status or local components are unavailable? |

## Demo Talk Track

Allowed:

> NaC shows the real estate purchase agreement as the primary BPMN flow. The
> sources support XNP, XNotar, land register, commercial register and card
> reader as the professional environment. For a real ISV integration we need an
> approved XNP/SNP test access path, API agreements and clear boundaries from
> BNotK or the chamber for which status and evidence data may be processed
> without matter data.

Not allowed:

- "NaC has productive XNP/SNP access."
- "NaC controls XNP from the cloud."
- "NaC automatically imports land-register or commercial-register content."
- "NaC stores card, PIN, token, document or matter data."

## Work Boundary For This PR

- No productive XNP/SNP claims.
- No matter data, no register data, no property data.
- No OCI, runtime, adapter or app change.
- Only demo guidance, BPMN profile wording and source references.
