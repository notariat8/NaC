# Plattform-Matrix fuer Onboarding und Regeln

## Ziel

Sicherstellen, dass Konzept-, Regel- und Onboarding-Aenderungen fuer alle Plattformen synchron gepflegt werden.

## Pflichtpfade

| Plattform | Pflichtdateien |
| --- | --- |
| Cursor | `AGENTS.md`, `.cursor/rules/`, `docs/en/START_HERE.md`, `docs/en/plugin-plans/README.md` |
| VS Code + Copilot | `AGENTS.md`, `.github/copilot-instructions.md`, `docs/en/vscode-copilot-start.md`, `docs/en/plugin-plans/README.md` |

## Gemeinsamer Kern

Die folgenden Inhalte muessen inhaltlich auf beiden Plattformen gleich bleiben:

- Compliance- und Governance-Prinzipien
- Review- und Freigabelogik
- Kultur- und Sprachpolicy
- Onboarding-Reihenfolge fuer Nicht-IT-Nutzer
- Default-MVP-Module und zugehoerige Onboarding-Prompts
- lokaler Ausfuehrungsort fuer NoC (`~/NoC` in WSL)
- Plugin-/Connector-Planungsmodell

## Aenderungsregel

Bei jeder konzeptuellen Aenderung:

1. Kerninhalt aktualisieren
2. Cursor-Pfad aktualisieren
3. VS-Code-Copilot-Pfad aktualisieren
4. Verlinkungen im `README.md` und `docs/en/START_HERE.md` pruefen

## Aktueller synchroner MVP-Default

- `software_company` -> `prompts/en/onboarding/software-company-first-setup.md`
- `notary` -> `prompts/en/onboarding/notary-first-setup.md`
- `wealth_management` -> `prompts/en/onboarding/wealth-management-first-setup.md`

Zusaetzlicher MVP-Use-Case:

- `property_management` -> `prompts/en/onboarding/property-management-first-setup.md`
