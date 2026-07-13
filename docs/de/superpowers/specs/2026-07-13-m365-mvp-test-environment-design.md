# M365-MVP-Testumgebung Design

Status: SPFx-/Deployment-Pfad package-ready; BFF-Livepfad DEFERRED
Datum: 13. Juli 2026
Scope: site-spezifische, ausschließlich synthetische Testumgebung im Workspace `notary_team_01`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-mvp-test-environment
leading_issue: https://github.com/notariat8/NaC/issues/620
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-13-m365-mvp-test-environment.md
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-620-01
  - AC-620-02
  - AC-620-03
  - AC-620-04
  - AC-620-05
  - AC-620-06
  - AC-620-07
validation_commands:
  - python3 -m unittest tests.test_m365_mvp_test_environment_verification_contract
  - python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton tests.test_m365_bpmn_viewer_runtime_readiness tests.test_m365_sharepoint_bpmn_viewer_adapter tests.test_m365_spfx_site_deployment tests.test_m365_mvp_test_environment_smoke tests.test_m365_mvp_test_environment_deploy tests.test_m365_test_environment_bff tests.test_m365_runtime_env_bootstrap
  - python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Ziel

Issue #620 liefert die erste sichtbare M365-Testumgebung für den NaC-MVP. Sie
zeigt im bestehenden Team- und SharePoint-Workspace `notary_team_01` einen
vollständig synthetischen Immobilienkaufvorgang mit BPMN-Diagramm, Aufgaben,
Frist und Rollenentscheidungen. Der Slice beweist die Paketierung, die
site-spezifische Installation, die kontrollierte Graph-Datenkante sowie
Readback, Cleanup und redigierte Evidence. Er verarbeitet keine produktiven
Akten-, Personen-, Dokument- oder Kommunikationsdaten.

## Verbindliche Schichtentrennung

### SharePoint- und Teams-Oberfläche

Die Oberfläche ist ein site-spezifisch installiertes SPFx-`1.23.2`-Paket mit
Teams-Hosts. `skipFeatureDeployment` bleibt `false`; tenant-weite Bereitstellung
ist verboten. Das Paket zeigt zunächst ausschließlich paketgebundene,
synthetische Daten. Es fordert exakt null Microsoft-Graph-Berechtigungen an und
enthält keinen direkten Graph-Client, kein Graph-Token und keinen alten
SharePoint-API- oder SDK-Datenpfad.

### Getrennte Deployment-Control-Plane und Data Plane

Für die site-spezifische Paketbereitstellung ist die Microsoft-365-CLI die
bewusste Control-Plane-Ausnahme. Sie darf ausschließlich das SPFx-Paket im App
Catalog bereitstellen, die App auf der exakten Site installieren oder
aktualisieren, die dedizierte Seite samt Webpart veröffentlichen und das
abgeleitete Teams-Paket im exakten Team bereitstellen. Sie darf keine
SharePoint-Listen- oder Item-Daten lesen, schreiben oder löschen und keine
Rechte, Scopes oder Credentials verändern.

Synthetisches Seeding, gezielter Readback und Cleanup bilden dagegen den
owner-gated Data-Plane-Smoke. Für sämtliche SharePoint-Listen- und
Item-Datenoperationen ist ausschließlich rohe Microsoft Graph REST `v1.0`
zulässig; alte SharePoint-Daten-APIs und SDK-Datenpfade sind verboten. Der
Runner ist hart an `notary_team_01`, den zugehörigen Site-/Team-Binding-Stand
und die synthetische Akten-ID `NAC-SYN-MATTER-001` gebunden. Er führt keine
Rechte- oder Credential-Änderung aus und stoppt fail-closed bei Workspace-,
Paket-, Hash-, Rollen- oder Readback-Abweichungen.

### Spätere BFF-Aktivierung

Direkter Microsoft-Graph-Zugriff aus SPFx bleibt dauerhaft verboten. Der
spätere dynamische Lesepfad lautet `SPFx/Teams -> NaC BFF -> Graph REST v1.0`.
Der BFF erzwingt serverseitig Workspace-, Akten-, Zweck-, Rollen- und
Vertretungsgrenzen und gibt nur redigierte DTOs zurück. Seine Aktivierung ist
in Issue #620 bewusst zurückgestellt, bis ein bereits vorhandener öffentlicher
HTTPS-Endpunkt und ein bereits vorhandener delegierter Entra-Scope genutzt
werden können. Dieser Slice darf keine Entra-Berechtigung, kein Credential und
keinen Scope neu anlegen oder verändern.

## Synthetischer Testvorgang

Der sichtbare Testdatensatz ist als synthetisch und nicht produktiv markiert.
Er enthält ausschließlich:

- Akten-ID `NAC-SYN-MATTER-001` und Vorgangsart Immobilienkaufvertrag,
- ein paketgebundenes BPMN-2.0-Modell mit kanonischem Hash,
- zwei synthetische Aufgaben mit BPMN-Schrittbezug,
- mindestens eine explizite Frist als ISO-8601-UTC-Wert,
- die Rollenfälle zuständig, protokolliert vertreten und unberechtigt.

Die Oberfläche muss sichtbar „Synthetische Testdaten“ und „Keine Mandatsdaten“
kennzeichnen. Personen, reale Aktenzeichen, Dokumentinhalte, Freitext aus einem
Notariat, Tokens und rohe Graph-Antworten sind nicht zulässig.

## Rollen- und Sichtbarkeitsprüfung

Die Testumgebung prüft drei getrennte Entscheidungen:

1. Die fest zugeordnete Rolle erhält Zugriff auf die synthetische Akte.
2. Eine zeitlich gültige, begründete Vertretung erhält Zugriff und erzeugt
   einen protokollierbaren Entscheidungsnachweis.
3. Eine nicht zugeordnete Rolle erhält keinen Zugriff; die Antwort verrät
   weder Existenz noch Metadaten der Akte.

Im paketgebundenen UI sind diese Fälle als synthetische Vertragsnachweise
darstellbar. Eine produktive Identitätsentscheidung darf ausschließlich der
spätere BFF aus validierten Entra-Claims und serverseitig gelesener
Rollenbindung treffen.

## Bereitstellung und Cleanup

Der App-Catalog- und Site-Runner validiert vor jeder Aktion Paket-ID,
Paket-Hash, SPFx-Version, site-spezifische Bereitstellung und Zielbindung. Er
installiert oder aktualisiert idempotent die App, erzeugt die dedizierte
Testseite, setzt den Webpart und kann das abgeleitete Teams-Paket im
Organisation-Katalog veröffentlichen und im exakten Team installieren.

Der synthetische Graph-Smoke erzeugt nur die deklarierte Testakte und ihre
Aufgaben, liest sie gezielt zurück und entfernt alle von diesem Lauf erzeugten
Listeneinträge in einem `finally`-Pfad. Vorhandene oder produktive Einträge
werden nie gelöscht. Ein Fehler führt zu `FAILED`, redigierter Evidence und
bestmöglichem zielgenauem Cleanup, nicht zu einem unkontrollierten Rollback.

## Evidence und Datenschutz

Evidence enthält Status, Correlation-ID, Paket- und BPMN-Hashes, technische
Schritt- und Rollenentscheidungen sowie Cleanup-Ergebnisse. Sie enthält keine
Tokens, Zertifikate, privaten Schlüssel, Graph-Rohantworten, Personen,
Dokumente, reale Aktenzeichen oder auflösbare produktive Referenzen. Alle
Live-Aktionen bleiben owner-gated und auf den freigegebenen Workspace begrenzt.

## Akzeptanzkriterien

- **AC-620-01:** Ein reproduzierbar gebautes, site-spezifisches und
  installierbares SPFx-Paket deklariert die Hosts SharePointWebPart und
  TeamsTab und setzt skipFeatureDeployment=false.
- **AC-620-02:** SPFx fordert niemals Microsoft-Graph-Berechtigungen an und
  ruft Graph nie direkt auf. Einziger zulässiger dynamischer API-Zielpfad ist
  ein delegierter NaC-BFF-Scope. Seine Aktivierung bleibt ohne bereits
  vorhandenen Scope und öffentlichen HTTPS-Endpunkt ausdrücklich DEFERRED.
- **AC-620-03:** Der BFF leitet die Benutzeridentität ausschließlich aus einem
  validierten Entra-Access-Token ab und löst Workspace-, Site- und Listen-IDs
  ausschließlich über eine serverseitige Allowlist auf. Die Live-
  Tokenvalidierung bleibt bis zu den vorhandenen Voraussetzungen DEFERRED.
- **AC-620-04:** Ein zugeordneter Benutzer erhält ausschließlich eine
  redigierte Projektion aus synthetischem Aktenstatus, Aufgaben, Frist und
  BPMN. Diese Projektion ist paketgebunden package-ready; die Auslieferung
  über den Live-BFF bleibt DEFERRED.
- **AC-620-05:** Nicht zugeordnete Benutzer sowie manipulierte Workspace-,
  Akten-, Zweck- oder Filtereingaben scheitern fail-closed, ohne Existenz oder
  Metadaten der Akte preiszugeben.
- **AC-620-06:** Site-spezifische SharePoint- und optionale Teams-
  Bereitstellung, Graph-REST-v1.0-Write/Readback, laufgebundenes Cleanup und
  die zugehörige Evidence sind reproduzierbar und redigiert.
- **AC-620-07:** Der Slice erzeugt keine Credentials oder Berechtigungen,
  berührt keine Produktivdaten und führt keine Aktion in einem anderen
  Workspace als notary_team_01 aus.

## Lieferstatus

Der site-spezifische SPFx-/Teams-Paket-, Deployment- und synthetische
Graph-Smoke-Pfad ist **package-ready**. Der BFF-Core und seine
Fail-closed-Verträge sind offline prüfbar. Die öffentliche BFF-Aktivierung,
delegierte Anmeldung und Live-Tokenvalidierung sind **DEFERRED**, weil dieser
Slice weder einen neuen delegierten Scope noch einen öffentlichen HTTPS-
Endpunkt oder Credentials anlegen darf.

## Nichtziele

- keine Produktivdaten und kein Zugriff auf andere Workspaces,
- keine Entra-Rechte-, Scope-, App-Credential- oder Zertifikatsänderung,
- kein direkter Graph-Zugriff aus SPFx,
- keine produktive BFF-Aktivierung ohne vorhandenen Endpunkt und Scope,
- keine Workflow-Ausführung durch `bpmn-js`; das Paket rendert BPMN read-only,
- kein tenant-weites SPFx-Deployment und kein automatisches Löschen fremder
  App-, Seiten-, Teams- oder SharePoint-Artefakte.
