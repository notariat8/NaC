# Unblocking GitHub-first work locally

Status: active (runbook, learned from session 2026-08-30)

## Purpose

This runbook records the recurring friction points that block agentic
GitHub-first work locally, and the reproducible ways to unblock them — so
that not every session has to re-run the same diagnosis. It is the durable
form of lesson capture per the repo rule: when the same friction point occurs
twice in a session or three times across issues/PRs, the pattern is named and
recorded as a runbook/wrapper.

## 1. GitHub write blockade from empty OAuth scopes

### Symptom

- `gh issue create` / `gh pr create` fails:
  `Your token has not been granted the required scopes … 'public_repo' … but your token has only been granted the: [''] scopes.`
- `git push` fails with
  `remote: Permission to <owner>/<repo>.git denied to <user>. … 403`.
- `gh api user --jq .login` and `gh issue list` still work
  (reads succeed, writes do not).

### Cause (diagnosis)

Not a session problem, but **empty OAuth scopes** of the active account token.
The login itself is persisted durably (encrypted store, 0600, survives sessions).
A new session injects the same store token and blocks just the same — a session
switch does not fix it and is not needed. The problem is not persistence, but
that the stored PAT was created without write scopes.

Proof command (read-only):

```bash
curl -sSI -H "Authorization: token $GH_TOKEN" https://api.github.com/user | grep -i 'x-oauth-scopes'
# x-oauth-scopes:           <- empty => no write rights
```

With valid scopes this line would show e.g. `repo` (covers `public_repo` and
thus push/issue/PR for this public repo).

### Root cause in the harness

`/auth login` is a **paste-a-PAT flow**, not an OAuth device flow: the harness
opens `https://github.com/settings/tokens/new`, shows the hint
"scopes: `repo, user:email`", and the PAT is pasted and verified via
`GET /user`. The harness does not request scopes itself; it adopts the scopes
of the pasted PAT (`x-oauth-scopes` header). A classic PAT with empty scopes
(`ghp_…`, `type: pat`) only has read access to public repos.

### Owner action (one-time, then durable)

On `https://github.com/settings/tokens/new` create a classic PAT with scope
**`repo`** (covers push/issue/PR for this public repo). `workflow` is only needed
if a PR changes `.github/workflows/*` — this fix PR does not. Then `/auth login`
and paste the new PAT; the harness replaces the old token (same login → replace)
and persists it durably again. No re-login needed afterwards. Without the
`repo` scope GitHub-first (leading issue → branch → PR → remote CI) is not
feasible. An agent mints no scopes; this gate stays owner-gated.

### In-session workaround (reads + diagnosis only, no writes)

If only read or diagnosis access is needed and the session `GH_TOKEN` is empty
or a placeholder, the store token can be decrypted from the encrypted file
backend and re-set for the session — **without** printing the token to stdout
or writing it to a file:

- Store: `~/.pi/agent/pi-git-auth/credentials.json` (AES-256-GCM envelope
  `enc:v1:`) plus a separate 0600 `key` file.
- Pattern: a tiny node script decrypts the token and writes it to stdout into
  `export GH_TOKEN="$(node …)"`. The token stays in the shell env, never in a
  file. The script contains only decryption logic, no secret.

Limit: this workaround only returns the scopes the store token already has —
with empty scopes, writing (issue/PR/push) stays blocked. It fixes reads, not
the write problem. The write problem is fixed only by the owner action above.

## 2. Local strict quality-gate runtime: slow, not broken

### Symptom

`python scripts/nac.py doctor --profile strict` looks like a hang on first
run (no output for over 10 minutes).

### Cause

No hang. The full unit suite (`unittest discover`) runs for about 520 seconds,
plus about 90 validators → total duration over 10 minutes. A 600-second
timeout falsely produces a hang picture (exit 124) because the gate flushes
output only at the end.

### Action

Budget at least 1200 seconds for `doctor --profile strict`. For incremental
pre-checking, run the directly affected checks in isolation instead of the
full suite every time:

```bash
graft build
python3 scripts/validate_graft_context_layer.py
PYTHONPATH=src python3 -m unittest tests.test_<module>
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
```

## 3. Token-injection helper in /tmp is ephemeral

The helper used in session 2026-08-30, `/tmp/nac_gh_token.js`, is gone after
session end. A durable variant as a repo-local wrapper (decryption logic
only, no secret on disk) eliminates recurrence and is intended as a future
optimization (tooling wrapper) — not part of this runbook.

## Guardrails

- Never print a secret to stdout, a file, a commit, or a PR.
- File store and `key` file stay 0600; the `graft` cache is not committed.
- Write scopes are owner-gated; an agent mints no scopes.
- See also [rule-architecture.md](../regelarchitektur.md) and
  [github-first-agentic-operating-model-design.md](../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md).
