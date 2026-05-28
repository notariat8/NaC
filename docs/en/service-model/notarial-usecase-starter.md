# Notarial Usecase Starter

## Purpose

This catalog replaces the earlier multi-domain model. It names only notarial
starter usecases that are described in the NaC repository.

The canonical full state is in [usecases/README.md](../../../usecases/README.md).
New examples must not be invented freely. They must either be created as
notarial usecases with KG, README and BPMN relation or refer to existing
usecases.

## Shared Status Values

- `draft`
- `validated`
- `needs_review`
- `approved`
- `executed`
- `archived`

## Shared Approval Points

- `validated -> needs_review`: when subject-matter, professional, privacy or
  technical relevance exists.
- `needs_review -> approved`: subject-matter review by the responsible role.
- `approved -> executed`: operational approval, with four-eyes review where
  required.

## Starter Set: Real-Estate Purchase Contract

Canonical folder:
[usecases/immobilienkaufvertrag/](../../../usecases/immobilienkaufvertrag)

Starter questions:

1. Which property, parties and register data are involved?
2. Which purchase-price, financing and maturity logic applies?
3. Which encumbrances, approvals and completion gates are open?

## Starter Set: Signature Certification

Canonical folder:
[usecases/unterschriftsbeglaubigung/](../../../usecases/unterschriftsbeglaubigung)

Starter questions:

1. Who signs and how is identity checked?
2. Which document and purpose are involved?
3. Is representation, register relation or special form review affected?

## Starter Set: Online GmbH Formation

Canonical folder:
[usecases/online-gmbh-gruendung/](../../../usecases/online-gmbh-gruendung)

Starter questions:

1. Which company data, founders and capital structure are available?
2. Which management appointment and representation rules apply?
3. Which register route, signature readiness and AML flags are open?

## Starter Set: Commercial-Register Filing

Canonical folder:
[usecases/handelsregisteranmeldung/](../../../usecases/handelsregisteranmeldung)

Starter questions:

1. Which entity and filing type are involved?
2. Which resolutions, attachments and signers are required?
3. Which XNP route and filing evidence are open?

## Pilot Notes

- Productively pilot only one or two notarial usecases first.
- All process changes run through branch, PR and review unless owner-direct mode
  has been explicitly approved.
- Release binding per matter start is mandatory.
- Deviations are documented as change requests.
