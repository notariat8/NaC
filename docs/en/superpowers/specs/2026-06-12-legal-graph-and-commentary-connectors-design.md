# Legal Graph And Commentary Connector Design

Date: 2026-06-12

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: legal-graph-commentary-connectors
leading_issue: https://github.com/notariat8/NaC/issues/103
risk_gate: External Service
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
validation_commands:
  - env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests -p 'test_*.py'
  - GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

## Decision

NaC gets a domain-capable legal graph following the pattern
`official sources -> normalization -> legal knowledge graph -> review and
operating surface`. The first deliverable MVP is inheritance law. Family law
and corporate law follow on the same architecture.

The legal graph has two intentionally separate tracks:

1. **Primary-source graph:** official statutes, case law, citations, versions,
   effective dates, NaC usecase links, review points and evidence.
2. **Commentary connector track:** licensed commentaries and publisher
   databases are connected only through reviewed MCP or API integrations. NaC
   stores no commentary full text in the product repository.

Commentary hints must never be treated as the sole notarial truth. They are
external research and review signals with licensing, source, privacy,
professional-secrecy and attribution boundaries.

## Source Frame

The primary-source track only uses sources whose usage and update behavior can
be reviewed:

- [Rechtsprechung im Internet](https://www.rechtsprechung-im-internet.de/jportal/portal/page/bsjrsprod.psml):
  selected decisions from 2010 onward, anonymized, generally complete,
  updated daily and freely reusable in the offered formats.
- [Gesetze im Internet](https://www.gesetze-im-internet.de/): almost all
  current German federal law.
- [digitalservicebund/ris-search](https://github.com/digitalservicebund/ris-search):
  public NeuRIS/RIS search service stack for statutes and case law as a future
  integration and watchlist candidate.
- [TaxGraph](https://tax-graph.com/) as a product reference for the
  architecture type: primary sources are normalized, linked in a graph and
  made usable through MCP/A2A-capable AI environments.

The commentary connector track records candidates such as beck-online, juris,
Wolters Kluwer or other professional sources only as candidates first.
Activation requires at least licensing review, API/MCP contract, credential
boundary, AVV/DPA review where personal data is involved, professional-secrecy
review, AI-SBOM decision, source attribution and a human review gate.

## Architecture

1. **Source Watcher** reads official feeds, API, XML or search sources and
   stores retrieval metadata, URL, timestamp and hash.
2. **Normalizer** extracts statutory structure, citation, version, effective
   date, court, date, docket number, statutory citations and source hash.
3. **Legal Graph Builder** creates nodes and edges for statutes, decisions,
   legal domains, notarial usecases, review points, evidence and review status.
4. **Graph Patch Pipeline** creates structured change proposals: new nodes,
   changed versions, new citation edges, affected usecases and risk/review
   hints.
5. **Validators** check schema, source status, hashes, forbidden data,
   commentary full-text absence, credential absence and review requirements.
6. **Operating surfaces** are `nac legal-graph status`,
   `nac legal-graph review`, an operator reading surface and later MCP/A2A for
   AI environments.

Professional truth is created only through validated patch, diff, human review
and merge. An automatic source run must never merge an unreviewed professional
change directly into the approved graph.

## Graph Model

The MVP uses these nodes:

- `legal_domain`: inheritance law, later family law and corporate law.
- `source_document`: official source with URL, retrieval time, format, hash
  and usage status.
- `norm`: statute, section, paragraph, sentence, version, citation, effective
  date and end date.
- `decision`: court, date, docket number, decision type, statutory links,
  citation, URL and hash.
- `notarial_usecase`: NaC usecase such as testament/inheritance contract,
  certificate of inheritance, disclaimer of inheritance or compulsory-share
  waiver.
- `review_point`: form, capacity, parties, deadline, register link,
  instruction, evidence or another human gate.
- `commentary_connector`: provider, license status, MCP/API mode, permitted
  use, prohibited storage and review requirement.
- `graph_patch`: proposed change with source, affected nodes, risk, review
  status and PR reference.

Important edges are `cites`, `amends`, `valid_from`, `valid_until`,
`affects_usecase`, `supports_review_point`, `needs_commentary_review` and
`approved_by`.

## Inheritance-Law MVP

The first MVP covers:

- relevant BGB inheritance-law norms as structured norm nodes,
- NaC usecases testament/inheritance contract, certificate of inheritance,
  disclaimer of inheritance and compulsory-share/inheritance waiver,
- selected official decisions with statutory links,
- review points for form, capacity, parties, deadlines, estate link,
  instruction and evidence,
- `nac legal-graph status` as CLI status,
- `nac legal-graph review` or an equivalent review JSON output,
- validators for schema, sources, patches and connector boundaries.

The MVP does not provide legal advice, an automated final notarial decision or
commentary-content storage.

## Commentary Connector Boundaries

Commentaries and professional sources have hard boundaries:

- MCP/API instead of scraping or full-text import.
- No credentials, tokens, cookies or licensing secrets in the repository.
- No commentary full text stored in the product repository.
- Only citations, answer metadata, license status, usage status, source
  attribution and review notes may be stored.
- Each activation requires contract, licensing basis, data-class decision,
  AVV/DPA review where relevant, AI-SBOM decision and human approval.
- Commentary hints are external research hints and require notarial review.

## Updates And Error Handling

Updates run as a controlled pipeline:

1. Retrieve source.
2. Normalize contents.
3. Build hash and structure diff.
4. Propose graph patch.
5. Run validators.
6. Show diff and risk.
7. Obtain professional review.
8. Merge by PR or owner-direct mode.

Failure cases:

- Source unavailable: the last approved graph remains valid, and the update is
  logged as a blocker.
- Parser uncertain: patch status `needs_human_mapping`, no auto-merge.
- Conflicting versions: review gate requires citation comparison and effective
  date review.
- Commentary connector without valid license/API: status `blocked_contract`.
- Mandate data in query or answer: abort processing and create a privacy
  finding.

## Tests And Validation

Acceptance criteria:

- AC-001: Schema test for legal graph files and graph patches.
- AC-002: Golden-fixture test: known inheritance-law norms create stable nodes and
  edges.
- AC-003: Diff test: a source change creates a patch, but not an unreviewed graph
  merge.
- Connector policy test: no credential, no commentary full text, license
  status required.
- CLI test for `nac legal-graph status` and `nac legal-graph review`.
- The strict quality gate remains green.

## Deliverable Roadmap

1. **M1 Contract:** legal graph and commentary connector contracts, data
   classes, roadmap entry and validator interfaces.
2. **M2 Inheritance-law MVP:** norm/usecase nodes, validator, CLI status and
   review JSON.
3. **M3 Update run:** source diff, patch proposals and PR-ready review
   artifacts.
4. **M4 Expansion:** family law, corporate law and licensed commentary
   MCP/API pilots.

## Non-Goals

- No autonomous legal advice.
- No production commentary access without license/API contract.
- No real mandate data in the product repository.
- No publisher full texts in the product repository.
- No unreviewed automatic changes to approved NaC usecases.
