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

- Bestehende generische Prozessdateien werden nach `processes/core/` ueberfuehrt.
- Branchenbezogene Inhalte werden in `processes/verticals/<vertical>/` ueberfuehrt.
- Gemeinsame Regeln bleiben in `policies/` und `docs/`.
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

## Risiken und Gegenmassnahmen

- **Risiko:** unklare Zuordnung Core vs. Vertical  
  **Massnahme:** Abgrenzungsregel aus `docs/service-business-core-vertical-blueprint.md` verbindlich anwenden.

- **Risiko:** Pfadumbrueche brechen Referenzen  
  **Massnahme:** Migration in kleinen PRs, Referenzpruefung pro PR.

- **Risiko:** Branchenspezifische Sonderfaelle verwischen Core  
  **Massnahme:** Vertical-spezifische Regeln nicht in Core mergen ohne Mehrbranchen-Nachweis.

## Rueckfallstrategie

- Migration nur ueber kleine, einzeln revertierbare PRs.
- Jeder Migrationsblock wird separat released.
- Bei Problemen Rollback auf letztes freigegebenes Release fuer neue Vorgaenge.
- Laufende Vorgaenge behalten gebundene Version.

## Abnahmekriterien

- Alle Prozesse sind eindeutig einem Zielpfad zugeordnet.
- Validierung und erforderliche Reviews sind erfolgreich.
- Doku und Policies referenzieren die neue Struktur korrekt.
- Mindestens ein erfolgreiches Pilotvertical produktiv nachgewiesen.

## Umsetzungsgrenze dieser Runde

Dieser Plan beschreibt den Umbau, fuehrt ihn aber nicht automatisch aus.
Er ist die Arbeitsgrundlage fuer die naechste, kontrollierte Migrationsrunde.
