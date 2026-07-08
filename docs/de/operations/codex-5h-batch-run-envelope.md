# Codex 5h Batch Run Envelope

## Zweck

Der 5h Batch Run Envelope ist die Arbeitsgrenze für lange autonome Codex-
Läufe. Er verhindert, dass ein mehrstündiger Batch wieder in einzelne
Minischritte zerfällt, und macht gleichzeitig sichtbar, welche Lanes parallel
laufen dürfen.

Der Envelope ist ein Offline-Vertrag. Er führt keine Microsoft-365-, Entra-,
SharePoint-, Teams- oder GitHub-Merge-Aktion aus.

## Einsatz

Nutzen, wenn mindestens zwei unabhängige Arbeitsspuren parallel vorbereitet
werden können:

- mehrere Offline-PRs,
- getrennte Worktrees für schreibende Lanes,
- read-only Subagent-Scouts für Scope, Review oder Validierung,
- gebündelte Owner-Gates am Ende statt laufender Einzelrückfragen.

Nicht nutzen für kleine Ein-Datei-Änderungen oder einen einzelnen klaren
Bugfix.

## Pflichtgrenzen

- No live tenant apply: keine Live-Tenant-Aktion ohne explizite Owner-Freigabe.
- No secrets or credentials: keine Secret-, Zertifikats- oder Entra-Credential-
  Änderung.
- No destructive git or filesystem: keine destruktive Bereinigung ohne
  explizite Freigabe.
- No merge without owner approval: PRs dürfen vorbereitet, aber nicht ohne
  Freigabe gemergt werden.

## Kontext

Der Envelope folgt dem Router in
[agent-context/index.json](../../../agent-context/index.json):

- Always-on: `AGENTS.md`, Policies, zentrale Invarianten.
- Scoped: betroffene Ordnerregeln und Contract-Hinweise.
- On-demand: Worktree-, Subagent-, Memory/Hooks- und Command-Rules-Modelle.
- Runtime: frischer Git-Status, frische Tests, frische PR-/CI-Ausgaben.

Runtime-Logs, Rohoutputs, Secrets, Tokens, Kunden- oder Mandatsdaten werden
nicht als persistenter geteilter Kontext gespeichert.

## Worktrees und Subagents

Jede schreibende Lane braucht einen eigenen Worktree. Überschneidende
`write_scope`-Einträge blockieren den Envelope. Bei zwei oder mehr
unabhängigen Review-Fragen muss ein Subagent-Plan oder eine ausdrückliche
Begründung gegen Split vorliegen.

Subagents bleiben read-only, außer sie besitzen eine eigene Worktree-Grenze.

## Verification

Standardprüfung:

```bash
python3 scripts/validate_codex_5h_batch_run_envelope.py
python3 scripts/nac.py agent-batch validate --format json
python3 scripts/nac.py contracts verify
```

Der Verification Contract steht unter
[codex-5h-batch-run-envelope.verification.json](../../../workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json).
