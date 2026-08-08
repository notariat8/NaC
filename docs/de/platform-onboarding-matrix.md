# Plattform-Onboarding-Matrix

## Ziel

Sicherstellen, dass Konzept-, Regel- und Onboarding-Änderungen für die aktiven
Agentenplattformen synchron gepflegt werden: Codex und pi.

## Pflichtpfade

| Plattform | Pflichtdateien |
| --- | --- |
| Codex | [AGENTS.md](../../AGENTS.md), [.codex/agents/](../../.codex/agents), [docs/de/START_HERE.md](START_HERE.md) |
| pi | [.pi/agents/](../../.pi/agents), [.pi/settings.json](../../.pi/settings.json), [.pi/README.md](../../.pi/README.md) |

## Gemeinsamer Kern

Die folgenden Inhalte müssen zwischen Policy, AGENTS.md, Codex-Profilen und
pi-Subagenten gleich bleiben:

- Compliance- und Governance-Prinzipien
- Review- und Freigabelogik
- Kultur- und Sprachpolicy
- Onboarding-Reihenfolge für Nicht-IT-Nutzer
- Notariats-Scope, kanonische Usecases und zugehörige Onboarding-Prompts
- lokaler Ausführungsort für NaC: `~/NaC` in WSL
- Plugin- und Connector-Planungsmodell

## Änderungsregel

Bei jeder konzeptuellen Änderung:

1. Kerninhalt aktualisieren
2. Codex-Agentenpfad aktualisieren
3. pi-Subagentenpfad aktualisieren
4. Verlinkungen im [README.md](../../README.md) und [docs/de/START_HERE.md](START_HERE.md) prüfen

## Plattformabbildung

Die pi-Subagenten unter [.pi/agents/](../../.pi/agents) sind Markdown-Spiegel
der Codex-Profile unter [.codex/agents/](../../.codex/agents). Beide sind
read-only und decken dieselben Review-Sichten ab: Scope-Mapper, KG-, BPMN-,
Policy-, Docs-Parity- und Validation-Reviewer. pi-spezifische Fähigkeiten
(Plan-Modus, Parallel Review, PR-Status, autonomer Abschluss) kommen über
empfohlene pi-Extensions, die Mitwirkende selbst installieren; siehe
[.pi/README.md](../../.pi/README.md).

## Aktueller synchroner MVP-Default

- `notary` -> [prompts/de/onboarding/notary-first-setup.md](../../prompts/de/onboarding/notary-first-setup.md)

Nicht-notarielle Produktpfade sind kein NaC-Scope. Fachliche Beispiele kommen
ausschließlich aus [usecases/](../../usecases), zum Beispiel Immobilienkaufvertrag oder
Unterschriftsbeglaubigung.
