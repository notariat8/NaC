# Copilot Quickstart in 15 Minuten

## Zielgruppe

Für Entscheider ohne IT-Spezialwissen, die mit VS Code und GitHub Copilot starten wollen.

## Minute 0-3: Basis prüfen

- VS Code ist installiert.
- GitHub Copilot ist aktiviert.
- Das Unternehmens-Repository ist in VS Code geöffnet.

## Minute 3-6: Pflichtdokumente lesen

Lesen Sie nacheinander:

1. `docs/de/START_HERE.md`
2. `docs/de/fachanwender-guide.md`
3. `policies/process-policy.yaml`
4. `policies/culture-policy.yaml`
5. `policies/technology-policy.yaml`

Ziel: gleiche Ausgangsbasis für Rollen, Prozesse und Sprache.

## Minute 6-9: Copilot mit Startprompt initialisieren

Nutzen Sie in Copilot Chat:

```text
Lies diese Dateien:
- docs/de/START_HERE.md
- docs/de/fachanwender-guide.md
- policies/process-policy.yaml
- policies/culture-policy.yaml

Erklaere mir dann ohne IT-Fachsprache:
1) Welche 3 Pilotprozesse ich zuerst starten sollte.
2) Welche Freigaben für diese Prozesse verpflichtend sind.
3) Welche offenen Entscheidungen ich heute treffen muss.
```

## Minute 9-12: Branchenpfad wählen

Wählen Sie den passenden Onboarding-Prompt:

- Kanzlei: `prompts/de/onboarding/law-firm-first-setup.md`
- Notariat: `prompts/de/onboarding/notary-first-setup.md`
- Hausverwaltung: `prompts/de/onboarding/property-management-first-setup.md`
- Softwareunternehmen: `prompts/de/onboarding/software-company-first-setup.md`
- Steuerbüro: `prompts/de/onboarding/tax-office-first-setup.md`
- Vermögensverwaltung: `prompts/de/onboarding/wealth-management-first-setup.md`

Synchroner MVP-Default im Referenzrepo:

- `software_company`
- `notary`
- `wealth_management`

Zusätzlicher MVP-Use-Case:

- `property_management`

## Minute 12-15: Pilot verbindlich starten

- Legen Sie einen Pilotprozess fest (z. B. Rechnung + Buchung).
- Definieren Sie Reviewer und Freigabepunkte.
- Starten Sie den ersten Change Request als Pull Request.

## Ergebnis nach 15 Minuten

Sie haben:

- einen konkreten Pilotfokus,
- klare Freigaberegeln,
- einen dokumentierten Startpunkt für den weiteren Rollout.
