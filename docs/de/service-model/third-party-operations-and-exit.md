# Third-Party Betrieb und Exit ohne Lock-in

## Ziel

Dieses Dokument beschreibt, wie Kunden `NaC` und zugehörige Services auch ohne Function8 als SaaS-Betreiber sicher weiterführen oder zu einem Drittanbieter migrieren können.

## Grundsatz

- Function8 ist ein Angebot, kein technischer Zwang.
- Alle relevanten Betriebsinformationen müssen in diesem Repo liegen.
- Jede Leistung muss durch Kundenbetrieb oder Drittbetrieb ersetzbar sein.

## Betriebsoptionen

1. `function8_managed_service`
   - Function8 betreibt die Plattform nach den Policies dieses Repos.
2. `customer_self_operated`
   - Kunde betreibt auf eigener Infrastruktur/Tenant.
3. `third_party_operated`
   - ein anderer Dienstleister übernimmt Betrieb auf Basis derselben Doku.

## Pflichtartefakte für Ersetzbarkeit

- Servicekatalog: `docs/de/service-model/function8-service-catalog.md`
- Tenant-Modell: `docs/de/service-model/tenant-ownership-and-eventlock-service.md`
- Revisionssicherheitskonzept: `docs/de/eventstream/revisionssicherheit.md`
- Cloud-Runbooks: AWS/Azure/GCP/OCI
- AVV-Checkliste: `docs/de/avv-checkliste-eventlock-saas.md`

## Übergabe an Dritte (Standardablauf)

1. Scope und Zielmodell (`self` oder `third_party`) festlegen.
2. Rollen- und Zugriffsmatrix übergeben.
3. Event-Schema und Journal-Integritaetsverfahren übergeben.
4. Laufende Retention- und Legal-Hold-Zustände übergeben.
5. Betriebsschlüssel und Zertifikatsverantwortung geordnet migrieren.
6. Parallelbetrieb und Abnahmetest durchführen.
7. Altbetrieb geordnet abschalten.

## Mindestkriterien für risikoarmen Exit

- keine proprietären, undokumentierten Datenformate
- event_schema und hash-chain dokumentiert
- tenant-spezifische Daten klar isoliert
- Restore-Test unter neuem Betreiber erfolgreich
- Audit-Lesepfad unter neuem Betreiber verifiziert

## Verbotene Muster

- versteckte Betriebsabhängigkeiten ohne Repo-Dokumentation
- ungeklärte Schlüsselhoheit bei Betreiberwechsel
- fehlende Nachweisfähigkeit während Migration

## Governance

- Änderungen an Exit-/Drittbetriebsregeln nur per PR + Review.
- Bei SaaS-Leistungen mit personenbezogenen Daten ist AVV-Pflicht zu prüfen und zu dokumentieren.
