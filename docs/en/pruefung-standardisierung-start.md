# Review And Standardization: How To Assess NaC

This document is for people and organizations that evaluate NaC from a control,
standardization, certification, supervisory-adjacent or comparability
perspective. It does not name any specific institution; it describes the review
path in the repository.

## What Can Be Assessed

NaC makes visible more than prompts:

- roles and approvals,
- technical and subject-matter gates,
- privacy and data-class rules,
- SBOM and AI-SBOM components,
- plugin boundaries and integration assumptions,
- usecase-local knowledge graphs,
- tests, validators and quality gates.

## What Should Not Be Assessed Here

- real mandate data, because it does not belong in this public repository,
- productive workstation configuration of individual offices,
- external system content that is only referenced,
- AI output as the final legal decision.

## Review Path

1. Read language and role rules.
2. Check privacy and storage boundaries.
3. Read usecase KGs against subject-matter minimum requirements.
4. Check plugin boundaries and local readiness checks.
5. Run the quality gate locally.
6. Assess version, release, fork and feedback model.

## Relevant Files

- [docs/en/reifegrad.md](reifegrad.md)
- [docs/en/glossar.md](glossar.md)
- [docs/en/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md)
- [policies/language-policy.yaml](../../policies/language-policy.yaml)
- [policies/data-protection-policy.yaml](../../policies/data-protection-policy.yaml)
- [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)
- [docs/en/security-and-dsgvo.md](security-and-dsgvo.md)
- [docs/en/sbom-for-ai.md](sbom-for-ai.md)
- [docs/en/quality-gate.md](quality-gate.md)
- [usecases/README.md](../../usecases/README.md)
- [roadmap/GANTT.md](../../roadmap/GANTT.md)

## Local Reproducibility

```bash
python scripts/nac.py doctor --profile strict
python scripts/validate_language_parity.py
python scripts/validate_knowledge_graph.py
python scripts/nac.py plugins validate
```

## Standardization Question

NaC is suitable for discussing repeatable subject-matter patterns in versioned
form: Which case nodes are required, which approvals are mandatory, which
evidence may only be referenced, and which automation remains deliberately
blocked?
