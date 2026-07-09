# First-Wave BPMN Gap Review

This decision note describes the offline gap review for the four first-wave
BPMN outlines.

## Purpose

`nac kg first-wave-gap-review --format json` compares the first-wave outlines
with the existing SharePoint MVP schema file, the ontology storage contract and
the current BPMN sources.

The review creates plan-only artifacts for:

- SharePoint field gaps and choice/taxonomy reviews
- BPMN gaps such as missing critical-path annotations or unclear gate mapping
- ontology projection patches without values
- later verification contracts before any apply action

## Redacted Evidence

`nac kg first-wave-gap-review-artifact --format json` also writes redacted
evidence artifacts:

- `out/notary-kg/first-wave-gap-review.redacted.json`
- `out/notary-kg/first-wave-gap-review.redacted.md`

The artifact mode contains only counts, slugs, source references and gap/patch
types. It contains no raw review items, no `planned_value` fields, no matter
values, no document full text, no raw Graph responses and no secrets. The
artifact is release-readiness attachable but remains optional; making it a
mandatory release/readiness gate requires a separate decision.

## Current Findings

The current offline smoke reports:

- 4 first-wave cases
- 9 SharePoint field gaps
- 10 BPMN gaps
- 12 ontology projection patches

One concrete MVP gap is `Akten.Vorgangstyp`: the choice list already contains
multiple first-wave slugs, but `vorsorgevollmacht-patientenverfuegung` needs a
planned extension review before a live schema apply.

## Boundaries

The gap review is offline-only:

- no Microsoft Graph requests
- no SharePoint writes
- no SharePoint schema changes
- no BPMN mutation
- no ontology patch apply
- no matter values in Git or ontology
- no document content
- no secrets

The validator
[scripts/validate_first_wave_bpmn_outline_gap_review.py](../../../scripts/validate_first_wave_bpmn_outline_gap_review.py)
checks these boundaries in the strict quality gate.

The artifact validator
[scripts/validate_first_wave_bpmn_outline_gap_review_artifact.py](../../../scripts/validate_first_wave_bpmn_outline_gap_review_artifact.py)
also checks the redaction shape, file suffixes and optional evidence attachment
boundary.
