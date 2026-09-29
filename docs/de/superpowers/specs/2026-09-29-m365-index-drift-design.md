# Issue #760: Reproduzierbare SharePoint-Indizes und lesende Drift-Prüfung

Status: Design zur Owner-Review, keine Live-Ausführung.

## Zweck und Befund

Die Teams-MVP-Konfiguration deklariert indizierte SharePoint-Spalten in
`indexed_columns`. Der Provisionierungsplan setzt `indexed=true` derzeit aber
nur für Spalten mit `enforce_unique_values=true`. Für drei der vier zur
Teams-403-Diagnose betrachteten Spalten widerspricht der erzeugte Payload
damit dem Sollschema. Die vorhandene Runtime-Prüfung erkennt fehlende Listen,
aber keine fehlenden Indizes; die CLI-Kante `drift` ist noch ein gesperrter
MVP-Platzhalter. Issue #760 behebt diese Reproduzierbarkeitslücke, nicht
automatisch die gesamte Teams-403-Ursache.

## Scope und Entscheidung

1. Das bestehende deklarative Schema bleibt die einzige Sollquelle. Für jede
   Liste werden nur Namen in `indexed_columns` als indiziert erzeugt;
   `enforce_unique_values=true` impliziert weiterhin einen Index. Ein
   deklarierter Index ohne passende Spalte, doppelte Namen oder ein
   widersprüchliches Eindeutigkeitsmerkmal blockieren die Validierung.
2. Der `ensure_column`-Plan übernimmt den aus der übergeordneten Liste
   abgeleiteten Indexstatus. Synthetische Tests prüfen alle deklarierten
   Indexspalten, besonders `Akten.NacCaseId`,
   `Vertretungsfreigaben.NacCaseId`, `AuditJournalLite.NacCaseId` und
   `AuditJournalLite.CorrelationId`.
3. `nac m365 teams-sharepoint drift` wird eine ausschließlich lesende,
   workspace-gebundene Metadatenprüfung. Sie vergleicht Site-ID, Listen-ID und
   Listenname aus dem gebundenen Provisionierungsstand sowie die erwarteten
   Spaltennamen und deren `indexed`-Wert über fest aufgebaute Microsoft-Graph-
   GET-Pfade. Sie liest weder Listeneinträge noch Dateien.
4. Fehlende oder mehrdeutige Bindungen, fehlende oder doppelte Spalten,
   `indexed=false`, unvollständige/paginierte Metadaten, Graph-Fehler und
   unerwartete Antwortformen ergeben einen deterministischen, redigierten
   Fehlerstatus. Es gibt keinen automatischen PATCH, kein Deployment und
   keinen Berechtigungswechsel. Ein echter Tenant-Read benötigt eine eigene
   gebundene Freigabe; in Issue #760 laufen nur synthetische Tests.

Bevorzugt ist diese gezielte Korrektur gegenüber einem vollständigen
Neu-Deployment: Sie repariert den Soll-/Ist-Abgleich ohne Teams-App oder BFF
neu auszuliefern. Ein vollständiger Neuaufbau würde mit dem bisherigen
Provisionierungscode drei Indizes erneut auslassen.

## Akzeptanzkriterien

- **AC-760-1:** Schema-Validierung blockiert fehlende, doppelte oder
  widersprüchliche Indexdeklarationen.
- **AC-760-2:** Jede in `indexed_columns` deklarierte Spalte erhält im
  Erzeugungsplan `indexed=true`; nicht deklarierte Spalten erhalten nicht
  unbeabsichtigt einen Index.
- **AC-760-3:** Die Drift-Prüfung meldet nur dann `PASSED`, wenn alle gebundenen
  Listen und Indexspalten im ausgewählten Workspace exakt passen. Negative
  Tests decken fehlende, doppelte und nicht indizierte Spalten, falsche
  Bindungen und unvollständige Antworten ab.
- **AC-760-4:** Die Drift-Prüfung erzeugt ausschließlich GET-Anfragen für
  Metadaten und eine redigierte Ausgabe. Synthetische Tests belegen null
  Schreibaufrufe, null Item-/Dateiabrufe und null echte Provideraufrufe.
- **AC-760-5:** DE/EN-Dokumentation, CLI, Spec-Traceability und Pflichtprüfungen
  sind synchron; vollständiger PR-Diff und Remote-CI werden geprüft.

## Risiken und Nicht-Ziele

Der zuvor beobachtete Berechtigungsfehler beim Index-PATCH bleibt ein eigener
Tenant-Apply-Blocker. Diese Repository-Änderung erteilt keine Rechte und setzt
keine Indizes im Tenant. Sie bestätigt auch nicht, dass nach späterer
Schema-Korrektur die Teams-403-Meldung verschwunden ist; dafür ist ein neuer,
separat autorisierter Funktionstest nötig. Keine Änderung an #739, #632,
Teams-App, BFF oder bestehenden Listeneinträgen.
