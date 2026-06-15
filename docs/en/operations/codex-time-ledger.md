# Codex Time Ledger

Status: introduced on 2026-06-15

## Purpose

The Codex Time Ledger makes agentic NaC work measurable. It records completed
work blocks as JSONL and then summarizes how much time went into local I/O,
local CPU, remote calls, approvals, user waiting, review, validation and
estimated LLM backend time.

The ledger does not replace OpenAI or workspace telemetry. It does not expose
the exact OpenAI-internal split between queueing, model compute and token
streaming. It is the local work log for answering: where does a NaC day lose
time, and which repeated frictions should we improve permanently?

## Storage

The default path is generated output and is not versioned as subject-matter
truth:

```bash
out/observability/codex-time-ledger.jsonl
```

For reviewable reports, a summary can be copied as Markdown or JSON into an
evidence artifact path. Raw logs must not contain mandate data, personal data,
secrets, full prompt text or command output.

## Categories

| Category | Meaning | Boundary |
| --- | --- | --- |
| `llm_backend` | estimated time for model response, streaming and agentic synthesis | no exact OpenAI-internal split |
| `local_cpu` | local tests, builds, validators and compute-heavy commands | exact CPU share needs an additional system tool |
| `local_io` | reading the repo, searching files, opening local logs | can include small CPU shares |
| `remote_io` | GitHub, web, registry, API or CI retrieval | remote system time is usually only indirectly visible |
| `remote_cpu` | CI or cloud runtime when known as a duration | not automatically derivable from local wall-clock time |
| `approval_wait` | waiting for sandbox, network or tool approval | record only blocks that are actually waiting |
| `user_wait` | waiting for user input, scope decision or review | do not mix with LLM reasoning time |
| `editing` | local code, documentation or contract edits | excludes subject-matter review time |
| `review` | diff review, result check, architecture comparison | excludes test runtime |
| `validation` | quality gate, privacy lint, link check, parity, unit tests | use `local_cpu` for CPU-heavy individual runs |
| `other` | fallback for blocks that cannot be separated cleanly | repeated use should trigger a new category decision |

## Commands

Record a manual block:

```bash
python scripts/nac.py time-ledger add \
  --session-id 2026-06-15-nac \
  --task "NaC Time Ledger" \
  --phase context-read \
  --category local_io \
  --started-at 2026-06-15T10:00:00Z \
  --ended-at 2026-06-15T10:08:00Z
```

Run and time a command:

```bash
python scripts/nac.py time-ledger run \
  --session-id 2026-06-15-nac \
  --task "NaC Time Ledger" \
  --phase unit-tests \
  --category local_cpu \
  -- /home/ubuntu/.venvs/nac/bin/python -m unittest tests/test_codex_time_ledger.py
```

Summarize a session:

```bash
python scripts/nac.py time-ledger summary \
  --session-id 2026-06-15-nac
```

Machine-readable summary:

```bash
python scripts/nac.py time-ledger summary \
  --session-id 2026-06-15-nac \
  --format json
```

## Working Rule

During longer NaC sessions, the lead Codex run maintains the ledger for
material blocks:

1. Context and research phases are recorded as `local_io` or `remote_io`.
2. Tests, validators and quality gates should use `time-ledger run` where
   practical.
3. Approval and user waiting time is kept separate from LLM and tool time.
4. At the end of a larger block, `time-ledger summary` is summarized in the
   response.
5. Repeated time sinks lead to concrete improvements: narrower test command,
   cache, runbook, command rule, parallel agents or clearer done criteria.
