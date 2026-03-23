# AGENTS.md

Dieses Repository ist ein Muster fuer ein Git-basiertes Business-OS.

## Prioritaet der Vorgaben

1. Gesetzliche und regulatorische Pflichten
2. Verbindliche Prozess- und Governance-Regeln
3. Unternehmensspezifische Branchenregeln
4. Kultur- und Sprachregeln

## Arbeitsprinzip

- Das LLM ist Eingabeoberflaeche, nicht die fachliche Wahrheit.
- Fachliche Wahrheit entsteht durch versionierte Aenderung + Review + Freigabe.
- Sensible Schritte brauchen Vier-Augen-Freigabe.
- Prozessaenderungen werden immer mit Begruendung dokumentiert.
- Konzeptaenderungen werden IDE-uebergreifend synchron gepflegt (Cursor und VS Code + Copilot).
- Onboarding wird nie nur fuer eine Plattform gepflegt, sondern fuer alle unterstuetzten Plattformen.
- Der verbindliche Technikstack steht in `policies/technology-policy.yaml`.
- Keine realen Secrets oder personenbezogenen Daten im Repository speichern (`policies/data-protection-policy.yaml`).
- SBOM-Vorgaben sind verbindlich nach `policies/sbom-policy.yaml`.
- Rollen und Qualifikationsgrenzen sind verbindlich nach `policies/role-model-policy.yaml`.

## Erststart fuer neue Nutzer

1. `docs/START_HERE.md` lesen.
2. `policies/culture-policy.yaml`, `policies/process-policy.yaml`, `policies/technology-policy.yaml`, `policies/data-protection-policy.yaml` und `policies/role-model-policy.yaml` bestaetigen.
3. `python scripts/startup_check.py --ide auto --run-tests` erfolgreich ausfuehren.
4. Passendes Onboarding-Prompt unter `prompts/onboarding/` starten.
5. Erst danach mit produktiven Prozessaenderungen beginnen.

## Plattform-Synchronitaet

- Bei Regel- oder Konzeptaenderungen immer beide Pfade aktualisieren:
  - Cursor: `.cursor/rules/`
  - VS Code + Copilot: `.github/copilot-instructions.md` und `docs/vscode-copilot-start.md`
