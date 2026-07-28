# M365-MVP-Testumgebung Design

Status: Live-Deployment am 14. Juli 2026 verifiziert; finaler Azure-BFF-Live-Abschlusslauf auf aktuellem main offen
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

### BFF-Abschlusslauf

Direkter Microsoft-Graph-Zugriff aus SPFx bleibt dauerhaft verboten. Der
dynamische Lesepfad lautet `SPFx/Teams -> NaC BFF -> Graph REST v1.0`. Der BFF
erzwingt serverseitig Workspace-, Akten-, Zweck-, Rollen- und
Vertretungsgrenzen und gibt nur redigierte DTOs zurück. Issue #632 stellte den
öffentlichen Endpunkt, `Matter.Read`, Runtime-`Sites.Selected` und Site-Rolle
`read` owner-gated bereit. Der Abschlusslauf darf eine fehlende exakte Bindung anlegen oder eine exakt
passende vorhandene Bindung wiederverwenden. Abweichende, doppelte oder breitere
Bindungen stoppen fail-closed und werden nicht im Lauf repariert; Credentials
werden nicht erzeugt oder geändert.

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
  der unter Issue #632 owner-gated bereitgestellte NaC-BFF-Scope `Matter.Read`;
  der finale Live-Nachweis auf aktuellem `main` steht noch aus.
- **AC-620-03:** Der BFF leitet die Benutzeridentität ausschließlich aus einem
  validierten Entra-Access-Token ab und löst Workspace-, Site- und Listen-IDs
  ausschließlich über eine serverseitige Allowlist auf. JWT/JWKS-Prüfung und
  Fail-closed-Grenzen sind offline implementiert; die Live-Tokenvalidierung
  ist Pflicht des noch offenen zwölfstufigen Abschlusslaufs.
- **AC-620-04:** Ein zugeordneter Benutzer erhält ausschließlich eine
  redigierte Projektion aus synthetischem Aktenstatus, Aufgaben, Frist und
  BPMN. Diese Projektion und der fixe Graph-REST-Adapter sind package-ready;
  SharePoint- und Teams-Auslieferung müssen im Abschlusslauf auf aktuellem
  `main` live nachgewiesen werden.
- **AC-620-05:** Nicht zugeordnete Benutzer sowie manipulierte Workspace-,
  Akten-, Zweck- oder Filtereingaben scheitern fail-closed, ohne Existenz oder
  Metadaten der Akte preiszugeben.
- **AC-620-06:** Site-spezifische SharePoint- und optionale Teams-
  Bereitstellung, Graph-REST-v1.0-Write/Readback, laufgebundenes Cleanup und
  die zugehörige Evidence sind reproduzierbar und redigiert.
- **AC-620-07:** Der Abschlusslauf erzeugt keine Credentials oder ungebundenen
  Berechtigungen, berührt keine Produktivdaten und führt keine Aktion in einem
  anderen Workspace als `notary_team_01` aus. Unter der begrenzten Supersession
  aus Issue #632 darf er ausschließlich `Matter.Read` sowie Runtime-
  `Sites.Selected` mit Site-Rolle `read` bei Fehlen anlegen oder exakt
  wiederverwenden. Abweichungen werden nicht repariert, sondern blockieren.

## Lieferstatus

Der owner-approved Live-One-Shot wurde am 14. Juli 2026 in `notary_team_01`
erfolgreich ausgeführt. Verifiziert sind das site-spezifische SPFx-/Heft-Paket,
App-Catalog- und Teams-Gate, der gemeinsame SharePoint-/Teams-Paketpfad, der
synthetische Aktenstatus mit zwei Aufgaben und UTC-Frist, der read-only
`bpmn-js`-Viewer mit BPMN-Bindung, die Rollenentscheidungen, Graph REST `v1.0`-
Write/Readback und das laufgebundene Cleanup. Dokumentzeiger und Lazy Loading/
Code Splitting für `bpmn-js` sind nicht nachgewiesen und bleiben offen.

Der Azure-Functions-BFF ist mit Entra-JWT/JWKS-Prüfung, fixer Graph-REST-
`v1.0`-Projektion, deterministischem Paket, Managed-Identity-IaC und zentralem
Offline-Readiness-Gate als **READY** prüfbar. Issue #632 hat den öffentlichen
Endpunkt, `Matter.Read`, Runtime-`Sites.Selected` und den exakten Site-Grant
`read` owner-gated und eng begrenzt eingeführt. Der letzte Aktivierungsversuch
war `FAILED_PARTIAL` am SPFx-Deployment; der Fix ist gemergt. Es fehlt ein
aktueller vollständiger 12-Step-Lauf samt Idempotenz, vier Manipulationstests,
SharePoint-/Teams-Rendernachweis und redigierter Abschluss-Evidence.

## Nichtziele

- keine Produktivdaten und kein Zugriff auf andere Workspaces,
- keine anderen oder breiteren Entra-Rechte und keine App-Credential- oder Zertifikatsänderungen im Abschlusslauf,
- kein direkter Graph-Zugriff aus SPFx,
- keine produktive BFF-Aktivierung ohne vorhandenen Endpunkt und Scope,
- keine Workflow-Ausführung durch `bpmn-js`; das Paket rendert BPMN read-only,
- kein tenant-weites SPFx-Deployment und kein automatisches Löschen fremder
  App-, Seiten-, Teams- oder SharePoint-Artefakte.
