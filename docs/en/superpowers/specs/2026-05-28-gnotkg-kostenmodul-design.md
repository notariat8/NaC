# GNotKG Cost Module Design

Date: 2026-05-28

## Decision

NaC gets one central GNotKG cost module. Every notarial usecase receives a
cost and billing gate, while real business values, parties, invoice data and
mandate values stay outside this product repository.

Calculation is deterministic Python code. A later `xyflow` surface only
renders the validated graph contract: usecase, business value, value rule,
KV item, table A/B, fee rate, expenses, review gate and draft cost note.

## Source Frame

The minimum source frame is:

- GNotKG section 3 for business value and the cost schedule.
- GNotKG section 34 for value fees and rounding.
- GNotKG section 35 for general value caps.
- GNotKG annex 1 for KV items.
- GNotKG annex 2 for table A/B.

NaC only produces technical drafts and review views. The notarial cost review
remains a human gate with documented qualification.

## Architecture

1. `nac_gnotkg.costs` calculates value fees with `Decimal`, official table
   logic and cent rounding.
2. `nac_gnotkg.views` creates a mandate-data-free cost review view and
   `xyflow`-ready nodes and edges.
3. `notary_kg` exposes the view through `cost-view` for each usecase.
4. Every usecase KG contains `cost.business_value`,
   `decision.gnotkg_cost_path`, `gate.gnotkg_cost_review` and
   `evidence.gnotkg_cost_note`.
5. `scripts/validate_knowledge_graph.py` enforces these baseline nodes for
   all usecases.

## Boundaries

- No automatic final cost assessment without notarial review.
- No real mandate values in the product repository.
- No second source of truth in `xyflow`.
- No portal, payment or invoice integration in this track.

## Acceptance

- Table values for GNotKG section 34 and annex 2 are tested against known
  values.
- Every usecase contains the cost and billing gate.
- `nac kg cost-view <slug>` returns a safe graph view.
- `nac gnotkg quote` returns a reproducible cost draft for entered,
  non-persisted values.
- The strict quality gate remains green.
