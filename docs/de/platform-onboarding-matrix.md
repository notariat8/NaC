# Codex-Onboarding-Matrix

## Ziel

Sicherstellen, dass Konzept-, Regel- und Onboarding-Änderungen für den aktiven
Codex-Pfad synchron gepflegt werden.

## Pflichtpfade

| Plattform | Pflichtdateien |
| --- | --- |
| Codex | `AGENTS.md`, `.codex/agents/`, `docs/de/START_HERE.md` |

## Gemeinsamer Kern

Die folgenden Inhalte müssen zwischen Policy, AGENTS.md und Codex-Profilen
gleich bleiben:

- Compliance- und Governance-Prinzipien
- Review- und Freigabelogik
- Kultur- und Sprachpolicy
- Onboarding-Reihenfolge für Nicht-IT-Nutzer
- Notariats-Scope, kanonische Usecases und zugehörige Onboarding-Prompts

## Änderungsregel

Bei jeder konzeptuellen Änderung:

1. Kerninhalt aktualisieren
2. Codex-Agentenpfad aktualisieren
3. Verlinkungen im `README.md` und `docs/de/START_HERE.md` prüfen

## Aktueller synchroner MVP-Default

- `notary` -> `prompts/de/onboarding/notary-first-setup.md`

Nicht-notarielle Produktpfade sind kein NaC-Scope. Fachliche Beispiele kommen
ausschließlich aus `usecases/`, zum Beispiel Immobilienkaufvertrag oder
Unterschriftsbeglaubigung.
