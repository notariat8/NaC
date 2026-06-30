# Legal Model Card AI-SBOM Delta

Status: delta gate without checkpoint
Last content update: 2026-06-30

## Purpose

This page defines the model-card and AI-SBOM delta gate for later
Legal-Nemotron model customization. It does not start training, run model
evaluation, publish a checkpoint or claim legal-answer quality.

The machine-readable contract lives in
[workflows/contracts/legal-model-card-ai-sbom-delta.contract.json](../../../workflows/contracts/legal-model-card-ai-sbom-delta.contract.json)
and is checked by
[scripts/validate_legal_model_card_ai_sbom_delta.py](../../../scripts/validate_legal_model_card_ai_sbom_delta.py).

## Model Card Delta

Before any later publication, the model card must cover at least:

- base model or checkpoint reference,
- intended use and prohibited use,
- source inventory, license/TDM status and data lineage,
- evaluation summary and known limitations,
- human review protocol,
- AI-SBOM reference and owner-apply reference,
- attestation that no mandate data was used.

## AI-SBOM Delta

The AI-SBOM delta remains planning evidence. It must record later changes to
model, dataset candidates, legal source inventory, training or evaluation
runtime, third parties, license/TDM status, risk controls and the human review
boundary.

## Hard Boundaries

- No checkpoint without a complete model card.
- No AI-SBOM delta with placeholders.
- No quality claim without evaluation and human review.
- No source text, publisher full text, secrets or mandate data in the model
  card or AI-SBOM.
- No training from this delta gate.
