# GitHub Copilot Instructions

Dieses Repository ist ein Muster fuer ein Git-basiertes Business-OS.

## Verbindliche Prioritaet

1. Compliance und rechtliche Pflichten
2. Prozessgovernance (Review, Freigaben, Nachvollziehbarkeit)
3. Branchenmodule
4. Kultur- und Sprachvorgaben

## Arbeitsweise

- Behandle das LLM als Assistent fuer Eingaben, nicht als finale fachliche Autoritaet.
- Schlage keine direkten Aenderungen an `main` vor.
- Erzwinge Vorschlaege ueber Branch + Pull Request + Review.
- Sensible Prozessschritte (z. B. Steuer, Zahlungsfreigaben) brauchen Vier-Augen-Prinzip.
- Jede Prozessaenderung muss begruendet und versioniert sein.
- Konzept- und Regelupdates muessen plattformuebergreifend synchronisiert werden (Cursor und VS Code + Copilot).
- Onboarding-Updates muessen fuer alle unterstuetzten Plattformen parallel gepflegt werden.

## Pflichtquellen im Repository

- `docs/START_HERE.md`
- `docs/fachanwender-guide.md`
- `policies/culture-policy.yaml`
- `policies/process-policy.yaml`
- `policies/technology-policy.yaml`
- `policies/data-protection-policy.yaml`
- `policies/sbom-policy.yaml`
- `policies/role-model-policy.yaml`
- `docs/governance.md`

## Sprache und Kultur

- Folge immer `policies/culture-policy.yaml`.
- Bei Genderfragen gilt die konfigurierte Policy.
- Wenn keine Policy gesetzt ist, nutze neutrale Sprache und bitte einmal um Entscheidung.

## Datenschutz und Sicherheit

- Keine echten Zugangsdaten, Keys oder Tokens in Vorschlaegen speichern.
- Keine echten personenbezogenen Daten in Prozessbeispielen speichern.
- Fuer Beispieldaten nur Testdomains und Platzhalter verwenden.

## Technikvorgaben

- Folge `policies/technology-policy.yaml` als verbindlichem Stack.
- Markdown ist die einzige manuell gepflegte Doku-Quelle.
- BPMN-2.0 ist die fachliche Quellnotation fuer Prozesse.
- Mermaid darf nur als Uebersicht eingesetzt werden.

## Erststart fuer VS Code + Copilot

1. Lies `docs/vscode-copilot-start.md`.
2. Fuehre `python scripts/startup_check.py --ide vscode --run-tests` aus.
3. Waehle das passende Branchen-Onboarding unter `prompts/onboarding/`.
4. Beginne mit einem Pilotprozess statt Vollausrollung.
