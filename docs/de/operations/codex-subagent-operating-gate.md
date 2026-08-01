# Codex Subagent Operating Gate

Status: aktive MVP-Guardrail für parallele Codex-Review-Arbeit.

Slug: `codex-subagent-operating-gate`.

## Zweck

Subagents sparen nur dann Zeit, wenn sie begrenzt, registriert und für
unabhängige Review-Arbeit genutzt werden. NaC nutzt eine fail-closed Registry,
damit agentische Batches laufen können, ohne dieselbe Sicherheitsgrenze immer
wieder neu auszuhandeln.

Registry:
[agent-context/subagent-registry.json](../../../agent-context/subagent-registry.json).

Workflow-Vertrag:
[workflows/contracts/codex-parallel-review.contract.json](../../../workflows/contracts/codex-parallel-review.contract.json).

Runtime-Limits:
[.codex/config.toml](../../../.codex/config.toml) setzt `max_threads = 6`,
`max_depth = 1` und `job_max_runtime_seconds = 1800`.

## Einsatzschwelle

Subagents nutzen, wenn mindestens zwei unabhängige Review-Fragen existieren und
der Koordinationsaufwand niedriger ist als der erwartete Review-Wert. Worktrees
stattdessen nutzen, wenn parallele Implementierung getrennte Branches oder
isolierte Dateiänderungen braucht.

Der führende Codex-Lauf bleibt verantwortlich für finalen Diff,
Validierungsnachweise, Owner-Gate-Text und PR-Zustand.

## Kontextisolation

Jeder NaC-Subagent wird mit `fork_context: false` gestartet. Full-History-Forks
sind verboten. Der führende Lauf übergibt nur den abgegrenzten Auftrag,
relevante Pfade, Issue oder PR und die benötigten Regeln. Reicht dieser Kontext
nicht aus, wird der gezielte Prompt erweitert; der vollständige Haupttask wird
nicht kopiert. Abgeschlossene Subagents werden unverzüglich geschlossen.

Diese Vorgabe verhindert, dass lange Haupttasks pro Review-Agent als neue
Sessiondatei vervielfältigt werden. Sie ist Teil des fail-closed Validators und
nicht nur eine Bedienempfehlung.

## Registry-Grenze

- Nur Profile aus der Registry dürfen genutzt werden.
- `.codex/agents/*.toml` muss exakt zur Registry passen.
- Jedes registrierte Profil ist `read-only` und muss `Do not edit files.`
  enthalten.
- Unbekannte oder zusätzliche Agentenprofile scheitern fail-closed.
- Subagents dürfen Findings, Evidence-Lücken und Prüfvorschläge liefern; sie
  führen keine Live-Applies, Releases, Credential-Änderungen oder
  Cleanup-Aktionen aus.

## Verbotene Delegation

Secrets, Zertifikats-Privatmaterial, echte Mandatsdaten, produktive M365-Writes,
Entra-App-Credentials, Release-Apply-Arbeit und destruktiven Git-Cleanup nie an
Subagents delegieren.

## Verifikation

```bash
python3 scripts/validate_codex_subagent_operating_gate.py
python3 -m unittest tests.test_codex_subagent_operating_gate
python3 scripts/quality_gate.py --profile strict
```
