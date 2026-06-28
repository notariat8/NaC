# Legal Model Evaluation Benchmark

Status: benchmark blueprint without dataset
Last content update: 2026-06-28

## Purpose

This page describes the later German-law benchmark for Legal-Nemotron model
customization. It does not generate a benchmark dataset, call a model or claim
legal quality.

The machine-readable contract lives in
[workflows/contracts/legal-model-evaluation-benchmark.contract.json](../../../workflows/contracts/legal-model-evaluation-benchmark.contract.json)
and is checked by
[scripts/validate_legal_model_evaluation_benchmark.py](../../../scripts/validate_legal_model_evaluation_benchmark.py).

## Evaluation Goal

The future benchmark should test whether a model can:

- separate primary sources, concept references and commentary,
- cite source classes and citation metadata correctly,
- distinguish current, amended and historical law state,
- map notarial review points without mandate data,
- detect uncertainty and route to human review.

## Source Hierarchy

Official publications and normalized statutory versions may become ground truth
after license, terms and normalization review. Wikipedia remains concept help
only. NVIDIA Nemotron Pretraining Legal v1 is only for baseline and gap
analysis. Publisher texts and commentary stay excluded until license, API, DPA
and review gates are complete.

## Nemotron Routing

A later benchmark may be prepared through `byob/mcq` and evaluated through
`eval/model_eval`. Both remain blocked until approved sources, a holdout
manifest, task families, review owner, evaluation task IDs, target model or
endpoint, execution profile and output path are concrete.

## Hard Boundaries

- No benchmark dataset without owner apply.
- No model run without approved evaluation tasks.
- No training on holdout questions.
- No mandate data and no publisher full text.
- No quality claim from automatic scores alone.
