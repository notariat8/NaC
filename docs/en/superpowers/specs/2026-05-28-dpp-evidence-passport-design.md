# DPP Evidence Passport Design

Date: 2026-05-28

Issue: https://github.com/notariat8/NaC/issues/38

## Decision

NaC will not introduce Digital Product Passports as a standalone notarial
product and will not treat them as a generic requirement for every use case.
The right NaC scope is a **DPP Evidence Passport**: a notarial trust, evidence
and audit layer for matters where product, construction-product, object or
supply-chain evidence becomes relevant to the legal workflow.

NaC remains fully scoped to notarial work. The module supports notarial matters
through verifiable sources, hashes, timestamps, roles, access classes and review
gates. It does not replace official DPP registries, manufacturers, market
surveillance authorities or product-data platforms.

## Source Frame

The minimum legal and technical context is:

- Regulation (EU) 2024/1781, Ecodesign for Sustainable Products Regulation
  (ESPR): framework for Digital Product Passports, with product-group specific
  obligations via delegated acts.
  <https://eur-lex.europa.eu/eli/reg/2024/1781/oj/eng>
- Regulation (EU) 2023/1542, Battery Regulation: first concrete battery
  passport for LMT batteries, industrial batteries above 2 kWh and electric
  vehicle batteries from 2027-02-18.
  <https://eur-lex.europa.eu/eli/reg/2023/1542/oj>
- Regulation (EU) 2024/3110, Construction Products Regulation: dedicated
  digital product passport system for construction products, compatible with
  the ESPR framework.
  <https://eur-lex.europa.eu/eli/reg/2024/3110/oj>
- CEN/CENELEC JTC 24 and Mandate M/604: technical standardization for
  identifiers, data carriers, access, security, interoperability, data formats,
  APIs, storage, archiving and integrity.
  <https://standards.iteh.ai/catalog/tc/cen/b2e63c3a-8446-4d3f-b148-51c2b3928ecd/jtc-24>
  <https://standards.iteh.ai/catalog/mandate/cen/e7165d1b-1a7a-47ed-b2eb-2b18d664fabe/m-604>

## NaC Fit

DPP is relevant to NaC when a notarial matter needs a reliable evidence chain
for an object, construction product, technical component, registry status or
supply-chain status. The value is not in storing full product data. The value
is in the verifiable connection:

1. Which DPP-like or product-related evidence was provided?
2. Which source did it come from?
3. Which version was checked at which point in time?
4. Which access class and legal basis applied?
5. Which notarial decision or question depends on it?

These facts fit the existing NaC architecture: knowledge graph, Secure Document
Link, event/evidence records and human gates.

## Use Case Priorities

### P1: Object and Construction-Related Matters

- `bautraegervertrag`: construction specification, construction-product
  evidence, completion and defect context, consumer releases.
- `immobilienkaufvertrag`: object, energy, renovation, equipment and
  documentation evidence where relevant to contract review or execution.
- `teilungserklaerung-weg`: unit, plan, construction and equipment evidence as
  object-related evidence.

### P2: Asset and Company Matters

- `geschaeftsanteilsuebertragung-gmbh`, `handelsregisteranmeldung` and related
  use cases when DPP data becomes part of due diligence, warranties or
  liability review.

### P3: Only With Concrete Relevance

- Inheritance, family, power-of-attorney and certification matters do not get a
  DPP gate by default. A DPP record can still appear as a normal document or
  evidence object if the individual matter requires it.

## Architecture

1. `nac-dpp-evidence` is planned as a domain module or as a capability of
   `nac-regulated-core`.
2. The module does not issue official DPPs. It captures and checks DPP-like
   records as evidence references.
3. The knowledge graph gets optional nodes for:
   - `asset.product_passport_subject`
   - `evidence.dpp_snapshot`
   - `decision.dpp_relevance`
   - `gate.dpp_evidence_review`
4. Secure Document Link remains the boundary for documents and files. The DPP
   module does not store secret links, access tokens or raw content in the
   product repository.
5. Event/evidence components store only mandate-data-free references, hashes,
   timestamps, source identifiers, access classes and review status.
6. A later `xyflow` view renders only the reviewed graph contract: object,
   DPP evidence, source, review status, open decision and gate.

## Minimal Data Model

A DPP evidence entry needs at least:

- `evidence_id`: stable NaC-internal evidence ID without secret material.
- `subject_type`: `building_product`, `building_unit`, `technical_asset`,
  `company_asset` or `other_notarial_asset`.
- `subject_reference`: mandate-data-free reference to the KG node.
- `source_type`: `official_registry`, `manufacturer_dpp`, `third_party_dpp`,
  `document_snapshot` or `manual_evidence`.
- `source_uri_hash`: hash of the source or DPP identifier, with no secret
  access data.
- `content_hash`: hash of the checked snapshot when a snapshot exists.
- `checked_at`: UTC timestamp of the check.
- `access_class`: `public`, `restricted`, `confidential` or `unknown`.
- `legal_basis_note`: short domain note explaining use in the concrete
  notarial matter.
- `review_status`: `not_relevant`, `needed`, `received`, `checked`,
  `question_open`, `approved` or `rejected`.
- `reviewed_by_role`: NaC role, not person data or secret data.

## Workflow

1. Use case intake identifies whether DPP-like evidence may be relevant.
2. Domain staff mark `decision.dpp_relevance` as not relevant, needed or open.
3. When relevant, DPP/evidence is referenced through Secure Document Link or a
   future connector.
4. NaC creates `evidence.dpp_snapshot` with hash, source, timestamp and access
   class.
5. `gate.dpp_evidence_review` stays open until the domain decision confirms
   whether the evidence is sufficient, triggers questions or must not be used.
6. GNotKG stays separate. A DPP record can be relevant to fees or billing, but
   it is not part of the fee calculation engine itself.

## Boundaries

- No official DPP registry operation by NaC.
- No claim of complete EU DPP compliance before final product-group specific
  rules are available.
- No real mandate data, raw product data, access tokens, API keys or secret
  links in the product repository.
- No standard gate for every notarial use case.
- No automatic notarial assessment without a human gate.
- NaC remains limited to notarial use cases.

## Acceptance

- DPP relevance is documented as an optional evidence track, not as a universal
  obligation.
- P1 use cases are limited to `bautraegervertrag`,
  `immobilienkaufvertrag` and `teilungserklaerung-weg`.
- The design references existing KG, Secure Document Link and evidence
  mechanisms instead of creating new data silos.
- Risks and non-goals are explicit.
- Strict Quality Gate remains green.
