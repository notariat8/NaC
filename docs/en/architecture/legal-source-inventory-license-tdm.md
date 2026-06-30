# Legal Source Inventory And License/TDM Gate

Status: source-inventory readiness without ingestion
Last content update: 2026-06-30

## Purpose

This page defines the source-inventory, license and TDM gate for later
Legal-Nemotron or legal-graph work. It does not download source text, generate
a benchmark dataset, call a model or start training.

The machine-readable contract lives in
[workflows/contracts/legal-source-inventory-license-tdm.contract.json](../../../workflows/contracts/legal-source-inventory-license-tdm.contract.json)
and is checked by
[scripts/validate_legal_source_inventory_license_tdm.py](../../../scripts/validate_legal_source_inventory_license_tdm.py).
The current gate state is also available through
`nac legal-graph source-inventory --format json`. The command only reads the
inventory metadata model and remains without source-text ingestion, benchmark
generation, model calls or training.

## Inventory Rule

Each source needs at least these fields before productive use:

- stable source ID and canonical URL,
- source class and jurisdiction fit,
- license and use status,
- TDM and bulk-access decision,
- attribution plan,
- storage boundary,
- human review owner.

## Current Seed Sources

- NVIDIA Nemotron Pretraining Legal v1 remains an English baseline dataset
  candidate, not a German legal source.
- `recht.bund.de` remains an official publication candidate for later
  ingestion planning, but without bulk crawl or full-text training before
  review.
- Wikipedia `Rechtsquelle` remains concept help only for source hierarchy and
  collision rules.

## Hard Boundaries

- No full-text download without owner apply.
- No bulk crawl without terms and TDM review.
- No benchmark dataset without approved sources.
- No training or model run from this contract.
- No mandate data and no publisher full text in the product repository.
