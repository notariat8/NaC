---
name: graft-context
description: Nutzen, bevor eine nichttriviale agentische Aufgabe das NaC-Repo erkundet; Graft baut einen deterministischen Code-Graphen (tree-sitter, kein LLM, kein Key) und macht ihn über die CLI verfügbar, damit das Repo nicht bei jeder Aufgabe neu erschlossen werden muss.
---

# Graft Context Layer

Status: verbindlicher Context-Layer für agentische Arbeit, siehe
[policies/graft-context-layer-policy.yaml](../../../policies/graft-context-layer-policy.yaml).

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen,
Variablennamen, Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Graft is the mandatory structural context layer for NaC
agent work. Tier 1 builds a deterministic tree-sitter code graph (no LLM, no
key, $0) and exposes it through the `graft` CLI. pi has no built-in MCP, so
pi agents invoke graft through the bash tool, not an MCP server.

## Einsatzgrenze

Laufzeitmodus: `agent-context-layer`.

Dieser Skill macht das NaC-Repo für Agenten greifbar, ohne es bei jeder
Aufgabe neu erkunden zu müssen. Er startet keine Netzwerk- oder LLM-Aufrufe
(Tier 1) und ersetzt keine Owner-Freigabe.

## Tier 1 ist Pflicht, Tier 2 ist optional

- **Tier 1 (structural, tree-sitter, kein LLM, kein Key, $0): verpflichtend.**
- **Tier 2 (`graft build --deep`, LLM-Summaries): optional.** Nur bei
  ausdrücklicher Nutzung muss der Provider im AI-SBOM nach
  [policies/sbom-policy.yaml](../../../policies/sbom-policy.yaml) und
  [docs/de/sbom-for-ai.md](../../../docs/de/sbom-for-ai.md) dokumentiert
  werden.

## Vor nichttrivialer Arbeit

1. `graft build` ausführen, um den lokalen Graphen zu erzeugen oder
   aufzufrischen (regenerierbar, nicht committed, siehe `.gitignore`).
2. Bei Bedarf `graft check` laufen lassen, um Drift festzustellen.
3. Dann erst erkunden: `graft ask`, `graft grep`, `graft callers`,
   `graft skeleton`, `graft map`.

## Befehle (Tier 1)

| Befehl | Zweck |
| --- | --- |
| `graft build` | Code-Graph aus tree-sitter bauen ($0, kein Key). |
| `graft check` | Deterministischer Drift-Check für CI; schlägt fehl, wenn der Graph vom Code abweicht. |
| `graft ask "<frage>"` | Token-sparende Frage an den Graphen. |
| `graft grep "<muster>"` | Strukturierte Suche im Graphen. |
| `graft callers "<symbol>"` | Aufrufer eines Symbols finden. |
| `graft skeleton "<datei>"` | Skelett/Signaturen einer Datei anzeigen. |
| `graft map` | Repo-Übersicht aus dem Graphen. |

## Daten- und Plattformgrenze

- Keine Secrets, keine realen Vorgangsdaten, keine Telemetrie.
- Tier 1 hat kein Netzwerk. Netzwerk-Aufrufe entstehen nur in Tier 2 und nur
  bei ausdrücklicher Konfiguration.
- pi hat keinen eingebauten MCP-Support. Graft wird in pi über die CLI
  (bash-Tool) und diesen Skill angebunden, nicht über einen MCP-Server.
- Codex bindet Graft über den Graft-Block in [AGENTS.md](../../../AGENTS.md).

## Harte Regeln

- `graft/` ist ein lokaler Cache und wird nicht committed.
- Der strict-Quality-Gate führt `graft check` verpflichtend aus
  ([scripts/validate_graft_context_layer.py](../../../scripts/validate_graft_context_layer.py)).
- Der Startup-Check führt `graft build` aus, sobald die `graft`-CLI verfügbar
  ist ([scripts/startup_check.py](../../../scripts/startup_check.py)).
