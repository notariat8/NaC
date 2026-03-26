# Plattform-Matrix fuer Onboarding und Regeln

## Ziel

Sicherstellen, dass Konzept-, Regel- und Onboarding-Aenderungen fuer alle Plattformen synchron gepflegt werden.

## Pflichtpfade

| Plattform | Pflichtdateien |
| --- | --- |
| Cursor | `AGENTS.md`, `.cursor/rules/`, `docs/START_HERE.md` |
| VS Code + Copilot | `AGENTS.md`, `.github/copilot-instructions.md`, `docs/vscode-copilot-start.md` |

## Gemeinsamer Kern

Die folgenden Inhalte muessen inhaltlich auf beiden Plattformen gleich bleiben:

- Compliance- und Governance-Prinzipien
- Review- und Freigabelogik
- Kultur- und Sprachpolicy
- Onboarding-Reihenfolge fuer Nicht-IT-Nutzer
- Default-MVP-Module und zugehoerige Onboarding-Prompts

## Aenderungsregel

Bei jeder konzeptuellen Aenderung:

1. Kerninhalt aktualisieren
2. Cursor-Pfad aktualisieren
3. VS-Code-Copilot-Pfad aktualisieren
4. Verlinkungen im `README.md` und `docs/START_HERE.md` pruefen

## Aktueller synchroner MVP-Default

- `software_company` -> `prompts/onboarding/software-company-first-setup.md`
- `notary` -> `prompts/onboarding/notary-first-setup.md`
- `wealth_management` -> `prompts/onboarding/wealth-management-first-setup.md`
