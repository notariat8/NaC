# M365-MVP-Testumgebung Implementierungsplan

**Datum:** 13. Juli 2026
**Issue:** [#620](https://github.com/notariat8/NaC/issues/620)
**Spec:** [M365-MVP-Testumgebung Design](../specs/2026-07-13-m365-mvp-test-environment-design.md)
**Delivery Mode:** Protected PR
**Live-Status:** Owner-approved Live-One-Shot am 14. Juli 2026 in `notary_team_01` erfolgreich; Azure-BFF offline READY, Live-Aktivierung DEFERRED

## Zielzustand

Im bestehenden Workspace notary_team_01 ist ein site-spezifisches,
installierbares SPFx-1.23.2-Paket als SharePoint-Seite und optional als
Teams-App sichtbar. Der paketgebundene, synthetische Immobilienkaufvorgang
zeigt Aktenstatus, BPMN, zwei Aufgaben und eine UTC-Frist. Der owner-gated
Data-Plane-Smoke verwendet für Listen-/Item-Daten rohe Graph REST v1.0,
liest die erzeugten Einträge gezielt zurück, schreibt redigierte Evidence und
entfernt nur seine eigenen Testeinträge. SPFx besitzt keine Graph-Berechtigung
und ruft Graph nie direkt auf.

Der BFF-Core, die serverseitige Allowlist, Entra-JWT-Prüfung, rohe Graph-REST-
`v1.0`-Adapter, das deterministische Azure-Functions-Paket und die Bicep-
Baseline sind offline implementiert und über
`nac m365 teams-sharepoint bff-azure-readiness` als `READY` prüfbar.
Das neue SPFx-Paket lädt dynamische Vorgangsdaten nur noch per
`AadHttpClient` vom festen BFF-Endpunkt; im Paket verbleibt ausschließlich
das hashgebundene BPMN-XML ohne Mandatsdaten. Der vollständige Live-Ablauf ist
über `nac m365 teams-sharepoint bff-azure-activation-plan` hashgebunden.
Delegierter BFF-Scope, Azure-Bereitstellung, Site-Grant und Live-Entra-
Tokenvalidierung bleiben bis zum einzigen gebündelten Owner-Gate `DEFERRED`.

## Umsetzungsschritte

1. **Site-spezifisches Paket reproduzierbar bauen (AC-620-01).**
   SPFx 1.23.2, Heft, React und bpmn-js pinnen; Lockfile binden;
   SharePointWebPart und TeamsTab deklarieren; skipFeatureDeployment=false und
   installierbares site-scoped Paket prüfen.
2. **Browser-/API-Grenze erzwingen (AC-620-02).**
   Graph-Permission-Requests und direkte Graph-Aufrufe aus SPFx blockieren.
   Als einzigen dynamischen API-Zielpfad den delegierten NaC-BFF-Scope
   verwenden. Das neue Paket ist darauf umgestellt; sein Live-Deployment
   bleibt bis zur gebündelten Scope-/HTTPS-Aktivierung DEFERRED.
3. **BFF-Identität, Projektion und Fail-closed-Verhalten prüfen
   (AC-620-03, AC-620-04, AC-620-05).**
   Identität nur aus validierten Entra-Token-Claims ableiten; Workspace-, Site-
   und Listen-IDs ausschließlich serverseitig allowlisten; für zugeordnete
   Benutzer nur redigierten Status, Aufgaben, Frist und BPMN liefern.
   Unzugeordnete Benutzer sowie manipulierte Workspace-, Akten-, Zweck- oder
   Filterwerte ohne Existenzleck ablehnen. Live-Tokenvalidierung und Live-BFF-
   Auslieferung bleiben DEFERRED; BFF-Client, DTO-Validierung und
   fail-closed UI-Zustände sind package-ready.
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

Die Offline-Implementierung des BFF-Cores einschließlich Azure-Functions-Host,
Managed-Identity-IaC, Storage-Netzgrenze, Kostenlimits, JWT/JWKS-Härtung und
fixer `notary_team_01`-Graph-Projektion gehört zum Slice. Die öffentliche
Aktivierung erfolgt in einem gebündelten Owner-Gate: Azure-Ressourcen
bereitstellen, delegierten Entra-Scope und exakten Site-Grant konfigurieren,
Paket als Azure-Functions-Flex-OneDeploy mit `--build-remote true` bereitstellen und SPFx per `AadHttpClient` auf den BFF umschalten. Das ZIP ist bewusst ein reproduzierbares Quellpaket; ein Deployment ohne Remote-Build ist unzulässig. Bis zu
diesem Gate bleibt die bereits bereitgestellte Altversion sichtbar; das neue
Repository-Paket ist jedoch vollständig auf `AadHttpClient -> NaC BFF`
umgestellt. Die Regel „kein direkter Graph aus SPFx“ bleibt unverändert. Der
Befehl `bff-azure-activation-plan` bindet alle zwölf Aktivierungs-,
Zugriffs-, Idempotenz- und Evidence-Schritte mit einem gemeinsamen SHA-256.
Der Hash umfasst ein kanonisches Manifest aller relevanten SPFx-Quellen; vor
dem Deploy muss daraus das `.sppkg` gebaut und dessen SHA-256 als redigierte
Evidence festgehalten werden. Da Entra die API-Client-ID erst bei der
App-Erstellung vergibt, löst derselbe genehmigte Live-Lauf genau eine
Anwendung über `api://funktion8.de/nac-bff` auf, prüft die UUID und bindet
diese `appId` vor dem Bicep-Deploy als exakten `bffApiAudience`. Die Freigabe
gilt ausschließlich für die vertraglich gebundene Site-ID von
`notary_team_01`.

## Abnahmenachweis

Der owner-approved Live-One-Shot wurde am 14. Juli 2026 in `notary_team_01`
erfolgreich mit site-spezifischem SPFx-/Heft-Paket, SharePoint-/Teams-Gate,
synthetischem Vorgang, BPMN, Aufgaben/Frist, Rollenentscheidungen, Graph REST
`v1.0`-Readback und laufgebundenem Cleanup ausgeführt. Die Evidence bleibt
synthetisch und redigiert. Dokumentzeiger und `bpmn-js`-Lazy-Loading sind nicht
nachgewiesen und bleiben offen. BFF-Scope, öffentliche Aktivierung und Live-
Entra-Tokenvalidierung bleiben ausdrücklich DEFERRED und werden nicht als live
erfüllt dargestellt.
