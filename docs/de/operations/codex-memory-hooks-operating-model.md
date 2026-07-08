# Codex Memory And Hooks Operating Model

## Zweck

Dieses Modell trennt persönliche Wiedererkennung, geteilte Wahrheit und
automatische Workflow-Hilfen. Es aktiviert keine Hooks und ändert keine
lokale `~/.codex/config.toml`.

## Memory-Quellen

| Art | Speicher | Regel |
| --- | --- | --- |
| Persönlich und stabil | Codex Memory | Präferenzen, wiederkehrende Arbeitsweise, Kommunikationsregeln. |
| Team-Regel oder Invariante | Repo-Artefakt | [AGENTS.md](../../../AGENTS.md), Policies, Contracts, Runbooks. |
| Änderbarer Arbeitsstand | GitHub Issue/PR | Status, Blocker, Scope, Akzeptanzkriterien. |
| Gesprächsnachweis | Thread/Issue-Kommentar | Nur als Evidence oder Abstimmungsverlauf. |
| Große Dokumentmenge | Suchindex oder MCP | Nur mit geprüfter Datenklasse und Zugriffspfad. |
| Secrets oder Mandatsdaten | nicht speichern | Nur in freigegebenen Secret-/Payload-Systemen. |

Wenn ein Fakt auditierbar sein muss oder sich ändern kann, ist Codex Memory
nicht die Quelle. Dann wird aus dem Repo, GitHub, SharePoint/M365 oder einem
freigegebenen MCP gelesen.

## Hook-Grenze

Hooks dürfen wiederholbare lokale Prüfungen anstoßen, aber keine Policy
ersetzen. Geeignet:

- Formatierung, Linting oder Tests vor Abschluss,
- Regeneration redigierter Artefakte,
- Prüfung, ob ein verpflichtender Validator fehlt.

Nicht geeignet:

- riskante Shell-Kommandos blockieren,
- Datei- oder Netzwerkrechte beschränken,
- Repo-Kontext erklären,
- Secrets oder Mandatsdaten prüfen,
- produktive M365-, Entra-, SharePoint- oder GitHub-Schreibaktionen starten.

Diese Grenzen bleiben Aufgabe von Regeln, Permissions, Owner-Gates,
Validatoren und Quality Gate.

## Beispielkonfiguration

Die Repo-Dateien unter [.codex/hooks/](../../../.codex/hooks/) sind Beispiele.
Sie werden erst aktiv, wenn ein Operator sie bewusst in seiner lokalen
Codex-Konfiguration referenziert.

Beispiel für lokale Aktivierung nach Review:

```toml
[[hooks.PreToolUse]]
matcher = "Bash"

[[hooks.PreToolUse.hooks]]
type = "command"
command = "/usr/bin/python3 /path/to/NaC/.codex/hooks/pre_tool_use_policy.example.py"
timeout = 30
statusMessage = "Checking NaC command hints"
```

Die Aktivierung braucht keine Repo-Änderung, aber die konkrete lokale
Konfiguration bleibt Betreiberentscheidung.

## Progressive Disclosure

Der Memory-/Hook-Pfad nutzt den Agent-Context-Index:

- Always-on: stabile Regeln und Navigation.
- Scoped: Verzeichnisregeln und Agentprofile.
- On-demand: Architektur, Entscheidungen, Guardrails, Runbooks.
- Runtime: aktueller Prompt, Toolausgabe, Logs, Diffs und Evidence.

Der maschinenlesbare Router steht in
[agent-context/index.json](../../../agent-context/index.json).

## Verification

Der Abschluss dieses Operating Models wird über
[codex-memory-hooks.verification.json](../../../workflows/verification-contracts/codex-memory-hooks.verification.json),
[codex-agent-context.verification.json](../../../workflows/verification-contracts/codex-agent-context.verification.json)
und `nac contracts verify` geprüft.

```bash
python3 scripts/validate_codex_memory_hooks_operating_model.py
python3 -m unittest tests.test_codex_memory_hooks_operating_model
python3 scripts/quality_gate.py --profile strict
```
