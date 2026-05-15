# Knowledge Graph

This directory contains static knowledge graph data for NoC usecases.

## Purpose

The knowledge graph is the repo-native state model for notarial usecases. It is
kept as JSON so workflows can read and update it deterministically, and it is
rendered as Markdown/Mermaid so humans can review the open questions and gates
in GitHub.

## Files

| File | Purpose |
| --- | --- |
| `notarial-top10.graph.json` | Static DB for the ten most important notarial case types. |
| `notarial-top10.md` | Human review and Mermaid view of the same KG scope. |
| `notarial-next10.graph.json` | Static DB for the next ten frequent notarial case types. |
| `notarial-next10.md` | Human review and Mermaid view of the next-ten KG scope. |

## Operating Rule

- Required information nodes start with empty `value` fields.
- Real client, property, company, estate, health, or family data must not be
  committed to Git.
- Workflows may set node status and attach evidence metadata only with reviewed
  synthetic data or approved non-sensitive references.
- Every KG update must update `roadmap/GANTT.md`; when a usecase binding changes,
  `usecases/GANTT.md` must also be updated.
- `scripts/validate_knowledge_graph.py` is part of the strict quality gate.
