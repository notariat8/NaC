# Repo-Refactor-Plan: Single-Repo Modules

## Ziel

Dieser Plan beschreibt die Zielstruktur und eine risikoarme Migration zu einem gemeinsamen Core mit Vertical Modules im selben Repository.

## Zielstruktur

```text
processes/
  core/
    intake/
    approvals/
    billing/
    accounting_tax/
    audit_close/
  verticals/
    law_firm/
    notary/
    tax_office/
    property_management/
    software_company/
    wealth_management/
    carpentry/
```

## Mapping von Bestand zu Zielbild

- Bestehende generische Prozessdateien werden nach `processes/core/` überführt.
- Branchenbezogene Inhalte werden in `processes/verticals/<vertical>/` überführt.
- Gemeinsame Regeln bleiben in `policies/` und `docs/de/`.
- Branchenaktivierung bleibt zentral in `policies/process-policy.yaml`.

## Migrationsreihenfolge

1. **Inventur**
   - alle vorhandenen Prozessdateien klassifizieren: `core` oder `vertical`.
2. **Zielpfade vorbereiten**
   - Ordnerstruktur anlegen und Naming-Konvention fixieren.
3. **Pilotvertical migrieren**
   - zuerst ein Vertical (empfohlen: `notary`) inklusive Kernprozesse migrieren.
4. **Validierung und Review**
   - Validierung/Tests und fachliche Freigabe auf Pilotvertical.
5. **Weitere Verticals migrieren**
   - law_firm, tax_office, property_management, software_company, wealth_management, carpentry in festem Takt.
6. **Abschluss**
   - Index-/Doku-Referenzen aktualisieren und Release taggen.

## Risiken und Gegenmaßnahmen

- **Risiko:** unklare Zuordnung Core vs. Vertical
  **Maßnahme:** Abgrenzungsregel aus `docs/de/service-model/core-vertical-blueprint.md` verbindlich anwenden.

- **Risiko:** Pfadumbrüche brechen Referenzen
  **Maßnahme:** Migration in kleinen PRs, Referenzprüfung pro PR.

- **Risiko:** Branchenspezifische Sonderfälle verwischen Core
  **Maßnahme:** Vertical-spezifische Regeln nicht in Core mergen ohne Mehrbranchen-Nachweis.

## Rückfallstrategie

- Migration nur über kleine, einzeln revertierbare PRs.
- Jeder Migrationsblock wird separat released.
- Bei Problemen Rollback auf letztes freigegebenes Release für neue Vorgänge.
- Laufende Vorgänge behalten gebundene Version.

## Abnahmekriterien

- Alle Prozesse sind eindeutig einem Zielpfad zugeordnet.
- Validierung und erforderliche Reviews sind erfolgreich.
- Doku und Policies referenzieren die neue Struktur korrekt.
- Mindestens ein erfolgreiches Pilotvertical produktiv nachgewiesen.

## Umsetzungsgrenze dieser Runde

Dieser Plan beschreibt den Umbau, führt ihn aber nicht automatisch aus.
Er ist die Arbeitsgrundlage für die nächste, kontrollierte Migrationsrunde.
