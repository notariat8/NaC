# Third-Party Betrieb und Exit ohne Lock-in

## Ziel

Dieses Dokument beschreibt, wie Kunden `OaC8` und zugehoerige Services auch ohne Function8 als SaaS-Betreiber sicher weiterfuehren oder zu einem Drittanbieter migrieren koennen.

## Grundsatz

- Function8 ist ein Angebot, kein technischer Zwang.
- Alle relevanten Betriebsinformationen muessen in diesem Repo liegen.
- Jede Leistung muss durch Kundenbetrieb oder Drittbetrieb ersetzbar sein.

## Betriebsoptionen

1. `function8_managed_service`
   - Function8 betreibt die Plattform nach den Policies dieses Repos.
2. `customer_self_operated`
   - Kunde betreibt auf eigener Infrastruktur/Tenant.
3. `third_party_operated`
   - ein anderer Dienstleister uebernimmt Betrieb auf Basis derselben Doku.

## Pflichtartefakte fuer Ersetzbarkeit

- Servicekatalog: `docs/function8-service-catalog.md`
- Tenant-Modell: `docs/tenant-ownership-and-eventlock-service.md`
- Revisionssicherheitskonzept: `docs/revisionssicherheit-eventstreaming.md`
- Cloud-Runbooks: AWS/Azure/GCP/OCI
- AVV-Checkliste: `docs/avv-checkliste-eventlock-saas.md`

## Uebergabe an Dritte (Standardablauf)

1. Scope und Zielmodell (`self` oder `third_party`) festlegen.
2. Rollen- und Zugriffsmatrix uebergeben.
3. Event-Schema und Journal-Integritaetsverfahren uebergeben.
4. Laufende Retention- und Legal-Hold-Zustaende uebergeben.
5. Betriebsschluessel und Zertifikatsverantwortung geordnet migrieren.
6. Parallelbetrieb und Abnahmetest durchfuehren.
7. Altbetrieb geordnet abschalten.

## Mindestkriterien fuer risikoarmen Exit

- keine proprietaeren, undokumentierten Datenformate
- event_schema und hash-chain dokumentiert
- tenant-spezifische Daten klar isoliert
- Restore-Test unter neuem Betreiber erfolgreich
- Audit-Lesepfad unter neuem Betreiber verifiziert

## Verbotene Muster

- versteckte Betriebsabhaengigkeiten ohne Repo-Dokumentation
- ungeklaerte Schluesselhoheit bei Betreiberwechsel
- fehlende Nachweisfaehigkeit waehrend Migration

## Governance

- Aenderungen an Exit-/Drittbetriebsregeln nur per PR + Review.
- Bei SaaS-Leistungen mit personenbezogenen Daten ist AVV-Pflicht zu pruefen und zu dokumentieren.
