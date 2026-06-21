# qmd Agent Memory Search

Status: optional local pilot for Codex working memory.

## Purpose

`qmd` can be used as a local Agent Memory Search for recurring rule, runbook and
release-memory questions. Its use is optional and does not replace governance
rules. GitHub remains the single source of truth; qmd is only a local search
index over already versioned, non-sensitive documentation.

## Allowed Index Scope

The index may only contain narrowly scoped working documentation:

- `docs/de/operations`
- `docs/de/superpowers`
- `docs/en/operations`
- `docs/en/superpowers`
- `oci-landing-zone/runbooks`
- repository-specific `AGENTS.md` after explicit pattern verification

Do not add the repo root as a collection. A qmd test showed that an expected
pattern was not applied and the resulting collection was too broad. Root
collections stay forbidden until the pattern behavior is reproducibly verified.

## Forbidden Content

The following paths or content must not be indexed by qmd:

- `.terraform`
- `out/`
- `attachments`
- wallet files or `wallet`
- `Secret`, Secret values or Secret OCIDs
- `private key`
- credentials, tokens, session values or OAuth state
- Mandatsdaten or mandate data
- customer, case, deed or identity-document data
- repo root as collection

This boundary applies even when qmd runs locally. Local indexing is not a
permission to include confidential data.

## Recommended Usage

Fast rule and runbook lookup:

```bash
qmd search "read-only GitHub OCI evidence no owner approval" --format json -n 5
```

More semantic lookup when terms are fuzzy:

```bash
qmd query --no-rerank "release approval stack variable refresh image digest" --format json -n 5
```

Retrieve one document:

```bash
qmd get qmd://oci-runbooks/no-ssh-functions-release.md:560:30
```

## Default Rules

- BM25 (`qmd search`) is the default for clear technical terms.
- `qmd query --no-rerank` is allowed when BM25 does not provide enough context.
- Embeddings are allowed, but only for the allowed scope.
- No reranking by default.
- No MCP/HTTP daemon by default.
- No automatic `qmd embed` on broad collections.
- No `git pull` through qmd update commands.

## Platform Decision From The Pilot

The local test on the current Codex/Brev environment showed:

- BM25-only was fast and stable.
- Embeddings worked, but initially took several minutes and downloaded a local
  model.
- Warm `qmd query --no-rerank` was usable for targeted memory questions.
- Local CPU reranking was too slow and unstable for the default path.
- The MCP/HTTP daemon was not reliably reachable in the test.

Recommendation: use qmd as an optional CLI helper, not as a required build,
release or agent-gate component.

## Governance Boundary

qmd must not replace Owner gates. Design, Review/Merge, Release, Apply, Secret
and destructive gates remain unchanged. qmd may only help find the relevant rule
location faster and reduce unnecessary questions.
