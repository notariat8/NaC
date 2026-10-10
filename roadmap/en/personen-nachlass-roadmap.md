# Roadmap: people, genograms, assets and temporal succession scenarios

Updated: 2026-10-10 · Status: planned backlog, not implemented  
Request and acceptance criteria: [Issue #772](https://github.com/notariat8/NaC/issues/772)  
Context: [Global roadmap](../GANTT.md)  
License: CC-BY-4.0

## Goal and NaC integration

NaC should support notarial succession planning through structured people and family relationships, derived genograms, assets and ownership shares, and traceable scenarios involving gifts, wills and different death dates. This addition neither claims implementation nor changes the current MVP delivery priorities.

Integration points include the [notarial software data model](../../docs/en/notarsoftware-datenmodell.md), [KG editor](../../docs/en/kg-editor-workstream.md), existing notarial succession/will usecases and the Legal Graph workstream. Static professional knowledge graphs remain separate from actual personal and asset data. Professional KG artifacts remain usecase-local; no central knowledge-graph directory.

## Storage and model direction

At the owner's request, SharePoint is included as the target candidate for production person storage within the existing M365 model. Exact list topology, payload storage and production approval remain part of the initial design phase.

| Layer | Planned content and responsibility |
| --- | --- |
| GitHub | Code, versioned JSON Schemas, ontology, validation rules, approved professional rules and synthetic examples. No actual personal or mandate data. |
| SharePoint lists | Purpose-bound person metadata, relationships, assets, ownership shares, disposition metadata and events as separate entity types with stable domain IDs. Access follows notary Team, role and mandate context. |
| Protected payloads and libraries | Large structured person payloads and documents with separate protection classes, versions and pointers. Storage and encryption require review before production use. Avoid mapping a huge schema to hundreds of exposed list columns. |
| Python graph projection | A case- and date-specific graph for family and ownership queries; NetworkX is a candidate for the in-memory prototype. |
| RDF/Turtle | Candidate for semantic ontology and graph exchange using RDFLib, SPARQL and SHACL. RDF is the data model; Turtle is a serialization. |
| Graph database | Optional later query/projection backend following benchmarks and an operating decision; the number 10,000 alone does not justify it. |

One authoritative model and defined mapping/version rules prevent divergent truths across lists, JSON and RDF. Split large person payloads into core data, relationships, roles, evidence and domain extensions. Missing facts remain unknown rather than becoming false or invented relationships.

For 10,000 people, plan indexes, selective queries and pagination from the start. SharePoint's 5,000-item list view threshold is not a cap on the entire population. Full exports need a separately tested strategy rather than assuming an unfiltered view. Technical sources: [List view threshold](https://learn.microsoft.com/en-us/troubleshoot/sharepoint/lists-and-libraries/items-exceeds-list-view-threshold), [Indexes and filters](https://learn.microsoft.com/en-us/troubleshoot/sharepoint/lists-and-libraries/fails-filtering-sharepoint-column).

## Domain building blocks

- Person: stable person_id, modular schema_version, relevant core data, evidence references and separate mandate roles.
- Relationship: relationship_id, type, person_ids, validity period, source, review status and uncertainty. Distinguish parenthood, adoption, marriage and separation; people may participate in multiple matters.
- Asset: asset_id, type (house, car, shares/holdings, cash/account), valuation date, currency, ownership shares, liabilities and encumbrances. Distinguish ownership, possession and usage rights.
- Disposition: will, succession agreement or gift agreement with version, temporal effect, beneficiary IDs, document reference and professional confirmation.
- Event: gift, ownership transfer, valuation, death or recorded correction. effective_at represents domain effect; recorded_at represents recording time. Unknown or approximate times remain explicit.
- Scenario: isolated assumptions, event order, rule version and results. Hypothetical deaths do not mutate confirmed master data.

## Phases and verifiable outcomes

Sequence indicates dependencies rather than promised calendar dates. All phases are planned.

| Phase | Scope | Deliverable and acceptance criterion |
| --- | --- | --- |
| P0: Design and storage boundary | Define SharePoint target, JSON/RDF roles, access, protection classes and jurisdiction. | Approved bilingual spec with AC IDs, plan and validation paths; one authoritative model, approved storage boundaries and explicit exclusions. |
| P1: People and family | Modular JSON Schemas, stable IDs, relationships and import/change contract. | Validate a small synthetic family; handle missing references, invalid self-relationships, conflicting dates and duplicates transparently. |
| P2: Storage adapter and 10,000-person prototype | Synthetic JSON files as reference dataset; SharePoint adapter offline first, then in an approved test tenant. | Import 10,000 synthetic people; verify paginated reads, ID preservation, migration, conflicts, restart and authorization boundaries. Record runtime, memory and query latency. |
| P3: Genogram | Deterministic family projection, legend, export and Codex integration. | Identical input yields identical nodes and relationships; show multiple partnerships, adoption, deceased people and unknown facts. No invented links. |
| P4: Asset graph | Assets, ownership history, valuations, liabilities and gifts. | Reconstruct ownership at a selected date; validate complete share totals and flag incomplete holdings. Values remain tied to valuation date and source. |
| P5: Temporal succession scenarios | Will-dependent simulation, death order and event history. | Reproduce both death orders and varying death dates; report assumptions, data/rule version, calculation path, open questions and notarial review points. |
| P6: Operation and backend decision | Central nac CLI, office UI, review flow and backend benchmark. | Approved CLI/UI views support reading, validation, visualization and scenarios; adopt a graph database only for demonstrated query, concurrency or operational benefits. |

P0 → P1 → P2 → P3 forms the family path. P4 builds on P1/P2; P5 requires P3/P4 and professionally approved rules. P6 integrates validated components.

## End-to-end synthetic reference case

1. A husband transfers a house or documented ownership share to his wife at T1.
2. The father gives his daughter a car at T2.
3. The father transfers shares to his son over several years; each completed transfer is a distinct event.
4. Include a documented will, or multiple versions, with their temporal effects.
5. Scenario A: father dies first, mother later. Scenario B: mother dies first, father later.
6. Vary death dates before and after individual transfers. Unclear ordering and missing dates must remain representable as uncertainty.

Show the genogram, assets immediately before each death, completed transfers and potential estate/claim consequences side by side. Ownership, succession allocation, compulsory-share questions and taxation are separate calculation layers. Implement concrete rules, periods and legal effects only after source verification and notarial approval; avoid universal ten-year treatment of all gifts.

## Codex and professional truth

Codex structures input and proposes traceable patches. Schema/reference validation, a diff and human confirmation precede changes. Genograms derive from evidenced relationships; calculations run deterministically in Python. Bind outputs to data version, date, rule version and source references. Missing facts or rules produce explicitly unresolved results.

Planned operations include validating people/relationships, exporting a genogram, showing assets at a selected date and comparing succession scenarios through the central nac CLI and office UI. P0 will define names and contracts; this roadmap does not claim existing commands.

## Next implementation step

Prepare P0: specify the SharePoint model and protection boundaries, compare JSON-first with a derived RDF projection against RDF-first with a JSON input contract, and define the small synthetic reference case. Existing NaC design, spec, review, privacy and quality rules apply before implementation. This roadmap records the ideas and does not authorize production tenant changes. German remains the leading professional language; English provides orientation.
