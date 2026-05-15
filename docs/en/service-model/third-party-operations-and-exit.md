# Third-Party Operation And Exit Without Lock-In

## Goal

This document describes how customers can continue to operate `NoC` and related
services safely without Function8 as SaaS operator, or migrate them to a third
party.

## Principle

- Function8 is an offer, not a technical lock-in.
- All relevant operating information must live in this repository.
- Every service must be replaceable by customer operation or third-party
  operation.

## Operating Options

1. `function8_managed_service`
   - Function8 operates the platform according to the policies in this
     repository.
2. `customer_self_operated`
   - Customer operates on own infrastructure or tenant.
3. `third_party_operated`
   - Another provider takes over operation based on the same documentation.

## Mandatory Artifacts For Replaceability

- Service catalog:
  [docs/en/service-model/function8-service-catalog.md](function8-service-catalog.md)
- Tenant model:
  [docs/en/service-model/tenant-ownership-and-eventlock-service.md](tenant-ownership-and-eventlock-service.md)
- Audit-proof evidence concept:
  [docs/en/eventstream/revisionssicherheit.md](../eventstream/revisionssicherheit.md)
- Cloud runbooks: AWS, Azure, GCP, OCI under [docs/en/eventstream/](../eventstream)
- DPA checklist:
  [docs/en/avv-checkliste-eventlock-saas.md](../avv-checkliste-eventlock-saas.md)

## Handover To Third Parties, Standard Flow

1. Define scope and target model: `self` or `third_party`.
2. Transfer role and access matrix.
3. Transfer event schema and journal integrity procedure.
4. Transfer current retention and legal-hold states.
5. Migrate operating keys and certificate responsibility in an orderly way.
6. Run parallel operation and acceptance test.
7. Shut down old operation in an orderly way.

## Minimum Criteria For Low-Risk Exit

- no proprietary undocumented data formats,
- event schema and hash chain documented,
- tenant-specific data clearly isolated,
- restore test under new operator successful,
- audit read path under new operator verified.

## Prohibited Patterns

- hidden operating dependencies without repository documentation,
- unclear key ownership during operator change,
- missing evidence capability during migration.

## Governance

- Changes to exit or third-party operation rules only by PR and review.
- For SaaS services with personal data, DPA obligation must be checked and
  documented.
