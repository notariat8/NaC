# M365-MVP-Testumgebung Implementierungsplan

**Datum:** 13. Juli 2026
**Issue:** [#620](https://github.com/notariat8/NaC/issues/620)
**Spec:** [M365-MVP-Testumgebung Design](../specs/2026-07-13-m365-mvp-test-environment-design.md)
**Delivery Mode:** Protected PR

## Zielzustand

Im bestehenden Workspace notary_team_01 ist ein site-spezifisches,
installierbares SPFx-1.23.2-Paket als SharePoint-Seite und optional als
Teams-App sichtbar. Der paketgebundene, synthetische Immobilienkaufvorgang
zeigt Aktenstatus, BPMN, zwei Aufgaben und eine UTC-Frist. Der owner-gated
Data-Plane-Smoke verwendet für Listen-/Item-Daten rohe Graph REST v1.0,
liest die erzeugten Einträge gezielt zurück, schreibt redigierte Evidence und
entfernt nur seine eigenen Testeinträge. SPFx besitzt keine Graph-Berechtigung
und ruft Graph nie direkt auf.

Der BFF-Core, die serverseitige Allowlist und die Fail-closed-Verträge werden
offline implementiert. Delegierter BFF-Scope, öffentliche Bereitstellung und
Live-Entra-Tokenvalidierung bleiben DEFERRED, solange kein bereits vorhandener
Scope und öffentlicher HTTPS-Endpunkt verfügbar sind.

## Umsetzungsschritte

1. **Site-spezifisches Paket reproduzierbar bauen (AC-620-01).**
   SPFx 1.23.2, Heft, React und bpmn-js pinnen; Lockfile binden;
   SharePointWebPart und TeamsTab deklarieren; skipFeatureDeployment=false und
   installierbares site-scoped Paket prüfen.
2. **Browser-/API-Grenze erzwingen (AC-620-02).**
   Graph-Permission-Requests und direkte Graph-Aufrufe aus SPFx blockieren.
   Als einzigen späteren dynamischen API-Zielpfad den delegierten NaC-BFF-
   Scope vorsehen, dessen Aktivierung ohne bestehenden Scope und HTTPS-
   Endpunkt DEFERRED bleibt.
3. **BFF-Identität, Projektion und Fail-closed-Verhalten prüfen
   (AC-620-03, AC-620-04, AC-620-05).**
   Identität nur aus validierten Entra-Token-Claims ableiten; Workspace-, Site-
   und Listen-IDs ausschließlich serverseitig allowlisten; für zugeordnete
   Benutzer nur redigierten Status, Aufgaben, Frist und BPMN liefern.
   Unzugeordnete Benutzer sowie manipulierte Workspace-, Akten-, Zweck- oder
   Filterwerte ohne Existenzleck ablehnen. Live-Tokenvalidierung und Live-BFF-
   Auslieferung bleiben DEFERRED; die paketgebundene Projektion ist
   package-ready.
4. **SharePoint-/Teams-Deployment und Graph-Smoke absichern (AC-620-06).**
   Paket-ID, SHA-256, SPFx-Version, Site-/Team-Binding und App-Catalog-
   Antworten prüfen. App, Seite, Webpart und optionales Teams-Paket idempotent
   bereitstellen. Ausschließlich synthetische Listeneinträge per Graph REST
   v1.0 schreiben, gezielt zurücklesen und laufgebunden löschen. Deployment,
   Readback, Cleanup und Evidence müssen reproduzierbar und redigiert sein.
5. **Unveränderliche Sicherheitsgrenze prüfen (AC-620-07).**
   Keine Credentials, Berechtigungen oder Entra-Scopes anlegen oder ändern,
   keine Produktivdaten lesen oder schreiben und keine Aktion außerhalb
   notary_team_01 zulassen. Falscher Workspace, fehlende Owner-Freigabe,
   Hash-Drift und Sicherheitsfehler stoppen vor dem ersten Write.
6. **One-Shot-Bedienkante und Abnahme integrieren (AC-620-01, AC-620-02, AC-620-03, AC-620-04, AC-620-05, AC-620-06, AC-620-07).**
   Die zentrale nac-CLI verbindet Paketprüfung, site-spezifisches Deployment,
   synthetischen Smoke, Readback, Cleanup und redigierte Evidence. Fokussierte
   Tests einschließlich Deployment- und Runtime-Env-Bootstrap, Contract-
   Verifikation, Sprachparität, Linkprüfung, visueller Nachweis, Strict-Gate
   und grüne Protected-PR-Checks bilden den Nachweis.

## Reihenfolge der Live-Aktionen

1. aktuelles Paket und SHA-256 an das Deployment-Gate binden,
2. App-Catalog-Paket site-spezifisch bereitstellen,
3. App auf der Zielsite installieren oder aktualisieren,
4. Testseite und Webpart idempotent veröffentlichen,
5. optional Teams-Paket veröffentlichen und im exakten Team installieren,
6. synthetischen Graph-Smoke mit Readback und Cleanup ausführen,
7. Installation und Seite read-only prüfen,
8. redigierte Abschluss-Evidence und visuellen Nachweis erzeugen.

## Stop-Bedingungen

Der Lauf stoppt fail-closed bei fehlender Berechtigung, Sicherheitsfehler,
Workspace-/Site-/Team-Abweichung, falschem Paket-Hash, tenant-weiter
Bereitstellung, Graph-Permission im SPFx-Paket, produktionsähnlichen Daten,
unvollständigem Readback oder fehlgeschlagenem zielgenauem Cleanup. Er ändert
keine Rechte, Credentials, Zertifikate oder Entra-Scopes.

## BFF-Aktivierung nach Issue #620

Die Implementierung des BFF-Cores gehört zum Slice, seine öffentliche
Aktivierung nicht. Diese erfolgt erst in einem getrennten owner-gated Scope,
wenn ein vorhandener öffentlicher HTTPS-Endpunkt und ein vorhandener
delegierter Entra-Scope nachgewiesen sind. Dann ersetzt der BFF die
paketgebundene UI-Datenquelle, ohne die Regel „kein direkter Graph aus SPFx“
zu ändern.

## Abnahmenachweis

Der package-ready Slice ist abgenommen, wenn AC-620-01 bis AC-620-07 im
maschinenlesbaren Verification Contract mit ihrer exakten Semantik
abgedeckt sind, alle fokussierten Tests und Validatoren bestehen, das Paket
reproduzierbar gebaut wurde und Deployment-/Smoke-Evidence ausschließlich
synthetisch und redigiert ist. BFF-Scope, öffentliche Aktivierung und Live-
Tokenvalidierung bleiben als DEFERRED ausgewiesen und werden nicht als live
erfüllt dargestellt.
