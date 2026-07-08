# Codex Parallel Review Workflow

This workflow is the NaC-shaped implementation of what other coding agents
surface as dynamic or agentic workflows. NaC does not wait for a single product
feature here. It uses the Codex building blocks available today: explicit
subagents, repository-local agent profiles, `codex exec`, Codex SDK, Codex as
an MCP server, and the existing NaC validators.

The workflow is deliberately not an autonomous production path. It is a review
harness for non-trivial changes to KGs, BPMN, contracts, policies,
documentation, and validators.

## When To Use It

Use it by default when the quick assessment shows net benefit over coordination cost. The lead run remains responsible and decides up front which subagents can review independently.

Use it when a task has at least one of these properties:

- several subject-matter layers are affected, for example KG and BPMN;
- the review needs different perspectives, such as privacy, roles,
  documentation parity, and tests;
- an issue or pull request should be stress-tested before implementation or
  before acceptance;
- the change could touch real mandate data, external services, license
  boundaries, or notarial approvals;
- many similar artifacts need repeated review.

Do not use it for small typos, pure link fixes, or clearly bounded single-file
changes without governance risk. Do not delegate secrets, OCI writes, apply,
release, or destructive gates to subagents.

## Agent Profiles

The repository-local profiles live under [`.codex/agents/`](../../.codex/agents):
the exact registry is
[agent-context/subagent-registry.json](../../agent-context/subagent-registry.json).

| Agent | Job |
| --- | --- |
| `nac_scope_mapper` | maps the request, artifacts, risks, and matching review agents. |
| `nac_kg_reviewer` | reviews usecase-local JSON KGs, stable IDs, aliases, provenance, and privacy classes. |
| `nac_bpmn_reviewer` | reviews BPMN models, NaC properties, and KG references. |
| `nac_policy_reviewer` | reviews privacy, roles, license, AI-SBOM, and provider boundaries. |
| `nac_docs_parity_reviewer` | reviews German/English parity, links, and agent-facing rule mirrors. |
| `nac_validation_reviewer` | reviews which validators and tests actually cover the request. |

All profiles are `read-only` at first. File changes stay with the lead Codex
run or with an explicitly approved implementation step.

Unknown or extra `.codex/agents/*.toml` profiles fail closed. The
`codex-subagent-operating-gate` registry must match the local TOML files
exactly, and `.codex/config.toml` limits subagent runs to `max_threads = 6`,
`max_depth = 1` and `job_max_runtime_seconds = 1800`.

## Flow

1. The lead Codex run states the request, scope, risk, and intended result.
2. `nac_scope_mapper` creates a review matrix with artifacts, specialist
   agents, and validation commands.
3. The matching specialist agents review independently and return concrete
   findings with file paths, IDs, and check commands.
4. The lead run consolidates findings, separates blockers from notes, and
   decides which changes to implement.
5. Implementation stays small and traceable in the normal NaC workflow.
6. `nac_validation_reviewer` or the lead run checks fresh validator output.
7. Completion remains possible only with human review, Git diff, and matching
   NaC gates.

## Example Prompt

```text
Use the NaC Parallel Review Workflow.
Have nac_scope_mapper first map scope, affected artifacts, risks, and validators
for this change. Then review in parallel with nac_kg_reviewer,
nac_bpmn_reviewer, nac_policy_reviewer, nac_docs_parity_reviewer, and
nac_validation_reviewer where they fit the scope. Summarize blockers, review
notes, and concrete next changes. No productive write actions without my
approval.
```

## Contract And Validation

The machine-readable contract lives in
[workflows/contracts/codex-parallel-review.contract.json](../../workflows/contracts/codex-parallel-review.contract.json).
It defines agent profiles, guardrails, inputs, prohibited data classes, review
gates, evidence fields, and validation commands.

Check:

```bash
python scripts/validate_codex_parallel_review.py
python scripts/validate_codex_subagent_operating_gate.py
```

For broader changes, these commands also remain relevant:

```bash
python scripts/validate_language_parity.py
python scripts/validate_governance_sync.py
python scripts/validate_knowledge_graph.py
python scripts/validate_bpmn_models.py
python scripts/quality_gate.py --profile strict
```

## Boundary

The workflow may prepare findings and speed up changes. It must not determine
notarial truth, auto-merge KG nodes, process real mandate data, use external
services without DPA/AVV and AI-SBOM gates, or replace productive approval.
