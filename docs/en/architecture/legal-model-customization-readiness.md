# Legal Nemotron Readiness

Status: readiness contract without training
Last content update: 2026-06-28

## Purpose

This page describes how NaC may later prepare a Legal-Nemotron fine-tune or
domain model customization. It does not start training, publish a checkpoint or
turn model answers into notarial legal truth.

The machine-readable contract lives in
[workflows/contracts/legal-model-customization-readiness.contract.json](../../../workflows/contracts/legal-model-customization-readiness.contract.json)
and is checked by
[scripts/validate_legal_model_customization_readiness.py](../../../scripts/validate_legal_model_customization_readiness.py).

## Source Role

The contract separates three roles:

- NVIDIA Nemotron Pretraining Legal v1 is an English legal baseline and
  evaluation candidate, but not a German legal source.
- `recht.bund.de` is an official publication and later ingestion candidate for
  Federal Law Gazette data through ELI, PDF, ZIP and RSS.
- The Wikipedia article on legal sources is only a concept anchor for source
  hierarchy, collision rules and source-of-law evidence.

## Gate Order

Before any runnable configuration, NaC needs:

1. Source inventory plus license, terms and TDM review.
2. Source hierarchy with primary sources, concept references and commentary
   exclusion rules.
3. Normalization schema with citation preservation, deduplication and storage
   boundary.
4. German-law benchmark with held-out sources and wrong-answer taxonomy.
5. Model card, AI-SBOM, evaluation and known limitations.
6. Owner apply with cost, runtime, rollback and security evidence.

## Nemotron Planning

The possible Nemotron chain remains planning-only:

- `curate/nemo_curator` for later source curation,
- `data_prep/pretrain_prep` for later pretraining data preparation,
- `pretrain/automodel` or `pretrain/megatron_bridge` only after owner apply,
- `eval/model_eval` for evaluation before quality claims,
- `byob/mcq` for a German-law benchmark.

No runnable training command may be produced without a concrete model, approved
corpus path, tokenizer, sequence length, hardware profile, execution profile,
output path and evaluation task IDs.

## Hard Boundaries

- No real mandate data.
- No publisher full text in the product repository.
- No training without owner apply.
- No checkpoint publication without model card and AI-SBOM.
- No legal answer without human notarial review.
