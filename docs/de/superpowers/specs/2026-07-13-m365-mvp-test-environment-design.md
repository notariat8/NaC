# M365-MVP-Testumgebung Design

Status: historische Live-Abnahme am 14. Juli 2026 verifiziert; aktuelle Read-only-Abnahme-Reconciliation `INCOMPLETE`
Datum: 13. Juli 2026
Lokale Vertragskorrektur: 1. Oktober 2026
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
  - python -m unittest tests.test_m365_mvp_test_environment_verification_contract
  - python -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton tests.test_m365_bpmn_viewer_runtime_readiness tests.test_m365_sharepoint_bpmn_viewer_adapter tests.test_m365_spfx_site_deployment tests.test_m365_mvp_test_environment_smoke tests.test_m365_mvp_test_environment_deploy tests.test_m365_test_environment_bff tests.test_m365_runtime_env_bootstrap
  - python scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/nac.py contracts verify
  - python scripts/nac.py doctor --profile strict
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

Die heutige Abnahme unter #620 gleicht ausschließlich vorhandene redigierte
Nachweise des aktuellen Zustands gegen die bestehenden Akzeptanzkriterien ab.
Der [Verification Contract](../../../../workflows/contracts/m365-mvp-test-environment.verification.contract.json)
führt dafür `final_bff_live_verification` als begrenzte Read-only-
Reconciliation mit Status `INCOMPLETE` und die
[versionierte Current-state-Evidence](../../../../workflows/verification-contracts/evidence/m365-mvp-current-state-acceptance.redacted.json).
Diese lokale Korrektur startet weder Providerzugriffe noch Anmeldung,
Token-Refresh, Deployment, Seeding, neue Writes oder Deletes. Fehlende Nachweise
bleiben offen; ein Offline-Kandidat oder Testreport ist kein Live-Receipt.

## Verbindliche Schichtentrennung

### SharePoint- und Teams-Oberfläche

Die Oberfläche ist ein site-spezifisch installiertes SPFx-`1.23.2`-Paket mit
Teams-Hosts. `skipFeatureDeployment` bleibt `false`; tenant-weite Bereitstellung
ist verboten. Das ursprüngliche Paket zeigte zunächst ausschließlich paketgebundene,
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

Historisches synthetisches Seeding, gezielter Readback und Cleanup bilden den
owner-gated Data-Plane-Smoke. Diese Beschreibung erteilt keine heutige
Write- oder Delete-Freigabe. Für sämtliche SharePoint-Listen- und
Item-Datenoperationen ist ausschließlich rohe Microsoft Graph REST `v1.0`
zulässig; alte SharePoint-Daten-APIs und SDK-Datenpfade sind verboten. Der
Runner ist hart an `notary_team_01`, den zugehörigen Site-/Team-Binding-Stand
und die synthetische Akten-ID `NAC-SYN-MATTER-001` gebunden. Er führt keine
Rechte- oder Credential-Änderung aus und stoppt fail-closed bei Workspace-,
Paket-, Hash-, Rollen- oder Readback-Abweichungen.

### Aktuelle BFF-Abnahme-Reconciliation

Direkter Microsoft-Graph-Zugriff aus SPFx bleibt dauerhaft verboten. Der
dynamische Lesepfad lautet `SPFx/Teams -> NaC BFF -> Graph REST v1.0`. Der BFF
erzwingt serverseitig Workspace-, Akten-, Zweck-, Rollen- und
Vertretungsgrenzen und gibt nur redigierte DTOs zurück. Issue #632 stellte den
öffentlichen Endpunkt, `Matter.Read`, Runtime-`Sites.Selected` und Site-Rolle
`read` owner-gated bereit. Der separate historische
[#632-Aktivierungsvertrag](../../../../workflows/contracts/m365-azure-bff-live-activation.contract.json)
bleibt unverändert; die heutige #620-Abnahme verlangt keinen neuen zwölfstufigen
Aktivierungslauf und übernimmt keine Create-/Reuse-/Approve-Berechtigung.
Exakte bestehende Scopes, Rollen und Site-Grants müssen nachvollziehbar
zurückgelesen sein. Fehlende, abweichende, doppelte oder breitere Bindungen
blockieren; die Reconciliation legt sie nicht an und repariert sie nicht.
Der #739-Zustand `FUNCTION_DEPLOYMENT_PROVENANCE_LOST` bleibt terminal:
keine Rekonstruktion, Wiederaufnahme oder Wiederholung dieses Laufs.

Für die aktuelle Release-/Host-/Versionsbindung genügt eine kausale Kette aus
hashgebundenem Source-Input, erfolgreichem Remote-Build-Deployment-Handoff und
getrennten aktuellen Host-/Versions-Readbacks. Ein Digest des erst in Azure
gebauten Binärartefakts ist keine zusätzliche Pflicht. Die getrennten
Readbacks dürfen weder den Handoff ersetzen noch #739-Provenienz rekonstruieren.

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
BFF aus validierten Entra-Claims und serverseitig gelesener Rollenbindung
treffen. Die aktuelle Abnahme benötigt weiterhin einen positiven Nachweis
für die zeitlich gültige, begründete und protokollierte Vertretung. Der
Negativfall benötigt unabhängig davon einen vor der Entscheidung belegten
Zustand ohne Zuordnung und ohne gültige Vertretung. Ein separates
authentifiziertes Kandidaten-`403` ersetzt diesen Vorzustand nicht.

## Historische Bereitstellung und Cleanup

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
Für die aktuelle Reconciliation wird ausschließlich das historische
laufgebundene Cleanup nachgewiesen; es werden keine neuen Einträge angelegt
oder gelöscht.

## Evidence und Datenschutz

Evidence enthält Status, Correlation-ID, Paket- und BPMN-Hashes, technische
Schritt- und Rollenentscheidungen sowie Cleanup-Ergebnisse. Sie enthält keine
Tokens, Zertifikate, privaten Schlüssel, Graph-Rohantworten, Personen,
Dokumente, reale Aktenzeichen oder auflösbare produktive Referenzen. Alle
historischen Live-Aktionen bleiben an ihre damalige Freigabe und den exakten
Workspace gebunden. Aktuelle Reconciliation-Evidence enthält vorhandene
Nachweise, ihre Bindungen und offene Lücken, kein erfundenes `PASSED`.

## Akzeptanzkriterien

- **AC-620-01:** Ein reproduzierbar gebautes, site-spezifisches und
  installierbares SPFx-Paket deklariert die Hosts SharePointWebPart und
  TeamsTab und setzt skipFeatureDeployment=false.
- **AC-620-02:** SPFx fordert niemals Microsoft-Graph-Berechtigungen an und
  ruft Graph nie direkt auf. Einziger zulässiger dynamischer API-Zielpfad ist
  der unter Issue #632 owner-gated bereitgestellte NaC-BFF-Scope `Matter.Read`;
  die aktuelle Versions- und Berechtigungsbindung bleibt nachweispflichtig.
- **AC-620-03:** Der BFF leitet die Benutzeridentität ausschließlich aus einem
  validierten Entra-Access-Token ab und löst Workspace-, Site- und Listen-IDs
  ausschließlich über eine serverseitige Allowlist auf. JWT/JWKS-Prüfung und
  Fail-closed-Grenzen sind offline implementiert; die aktuelle
  Live-Tokenvalidierung wird gegen vorhandene gebundene Nachweise geprüft.
- **AC-620-04:** Ein zugeordneter Benutzer erhält ausschließlich eine
  redigierte Projektion aus synthetischem Aktenstatus, Aufgaben, Frist und
  BPMN. Diese Projektion und der fixe Graph-REST-Adapter sind package-ready;
  aktuelle SharePoint- und Teams-Auslieferung sowie Versionsbindung müssen
  durch vorhandene Live-Nachweise belegt werden. Die zeitlich gültige,
  begründete Vertretung bleibt als separater positiver Rollenfall Pflicht.
- **AC-620-05:** Nicht zugeordnete Benutzer sowie manipulierte Workspace-,
  Akten-, Zweck- oder Filtereingaben scheitern fail-closed, ohne Existenz oder
  Metadaten der Akte preiszugeben. Der unzugeordnete Negativfall verlangt einen
  unabhängigen Vorzustandsnachweis ohne Zuordnung und ohne gültige Vertretung.
- **AC-620-06:** Site-spezifische SharePoint- und optionale Teams-
  Bereitstellung, Graph-REST-v1.0-Write/Readback, laufgebundenes Cleanup und
  die zugehörige Evidence sind reproduzierbar und redigiert. Die aktuelle
  Read-only-Reconciliation prüft bestehende Bereitstellung, Readbacks,
  historisches laufgebundenes Cleanup und wiederholte unveränderte Readbacks
  als Konvergenz; sie führt keine neuen Writes oder Deletes aus.
- **AC-620-07:** Die aktuelle Abnahme erzeugt oder ändert keine Credentials,
  Scopes, Rollen, Grants oder sonstigen Berechtigungen, berührt keine
  Produktivdaten und bleibt auf `notary_team_01` begrenzt. Exaktes
  `Matter.Read`, Runtime-`Sites.Selected` und Site-Rolle `read` sind durch
  bestehende Readbacks zu belegen; fehlende, abweichende, doppelte oder breitere
  Bindungen blockieren ohne Reparatur. Die historische #632-Supersession
  erteilt keine heutige Create-/Reuse-/Approve-Freigabe.

Die Härtung aus [#681](https://github.com/notariat8/NaC/issues/681) bleibt
unverändert verbindlich: **AC-681-01** bindet ausschließlich die kanonische
BPMN-Quelle mit Prozess, Profil und SHA-256 ohne eingebettetes BPMN;
**AC-681-02** bindet jede Aufgabe genau einmal an einen kanonischen BPMN-Task
mit passendem `nac:kgRef`, BusinessCaseType und usecase-lokalem Knowledge Graph;
**AC-681-03** bleibt offline ohne Tenant-, Rechte- oder Credential-Änderung.

## Lieferstatus

Der owner-approved Live-One-Shot wurde am 14. Juli 2026 in `notary_team_01`
erfolgreich ausgeführt. Verifiziert sind das site-spezifische SPFx-/Heft-Paket,
App-Catalog- und Teams-Gate, der gemeinsame SharePoint-/Teams-Paketpfad, der
synthetische Aktenstatus mit zwei Aufgaben und UTC-Frist, der read-only
`bpmn-js`-Viewer mit BPMN-Bindung, die Rollenentscheidungen, Graph REST `v1.0`-
Write/Readback und das laufgebundene Cleanup. Dokumentzeiger und Lazy Loading/
Code Splitting für `bpmn-js` sind nicht nachgewiesen und bleiben offen. Die
[historische `PASSED`-Attestation](../../../../workflows/verification-contracts/m365-mvp-test-environment-live.verification.json)
wird unverändert erhalten und belegt weder BFF-Aktivierung noch
Live-Entra-Tokenvalidierung.

Der Azure-Functions-BFF ist mit Entra-JWT/JWKS-Prüfung, fixer Graph-REST-
`v1.0`-Projektion, deterministischem Paket, Managed-Identity-IaC und zentralem
Offline-Readiness-Gate als **READY** prüfbar. Issue #632 hat den öffentlichen
Endpunkt, `Matter.Read`, Runtime-`Sites.Selected` und den exakten Site-Grant
`read` owner-gated und eng begrenzt eingeführt. Ein früherer Aktivierungsversuch
endete am SPFx-Deployment mit `FAILED_PARTIAL`; der zugehörige Fix wurde
gemergt. Diese Aktivierungs-/Fehlergeschichte bleibt separat; #739 endet
weiterhin terminal in `FUNCTION_DEPLOYMENT_PROVENANCE_LOST`.

Für die aktuelle Abnahme sind zugeordnete Workspace-/Workbench-/BPMN-`200`,
anonyme `401`, vier Workspace-/Akten-/Zweck-/Filter-`403` und ein separates
authentifiziertes Kandidaten-`403` auf beiden Routen in
[#620-Nachweis 5932777104](https://github.com/notariat8/NaC/issues/620#issuecomment-5932777104)
und [#620-Nachweis 5934493891](https://github.com/notariat8/NaC/issues/620#issuecomment-5934493891)
aufgezeichnet. Aktuelle Render-Beobachtungen sind über
[#620-Nachweis 5918874200](https://github.com/notariat8/NaC/issues/620#issuecomment-5918874200)
und [#762-Nachweis 5916031285](https://github.com/notariat8/NaC/issues/762#issuecomment-5916031285)
referenziert. Diese Beobachtungen begründen kein vollständiges `PASSED`.

Offen bleiben die aktuelle Release-Input-/Host-/Versionsbindung, der positive
gültige Vertretungsfall, der unabhängige unzugeordnete Vorzustand ohne gültige
Vertretung, SharePoint-Rendernachweis sowie exakte Berechtigungs- und
Read-only-Konvergenznachweise. Bis zur vollständigen Belegung bleibt die
Current-state-Abnahme `INCOMPLETE`.

## Nichtziele

- keine Produktivdaten und kein Zugriff auf andere Workspaces,
- keine heutigen Entra-, Rollen-, Scope-, Grant-, App-Credential- oder Zertifikatsänderungen,
- kein direkter Graph-Zugriff aus SPFx,
- keine produktive BFF-Aktivierung ohne vorhandenen Endpunkt und Scope,
- keine Workflow-Ausführung durch `bpmn-js`; das Paket rendert BPMN read-only,
- kein tenant-weites SPFx-Deployment und kein automatisches Löschen fremder
  App-, Seiten-, Teams- oder SharePoint-Artefakte,
- kein neuer #632-Aktivierungslauf und keine Rekonstruktion oder Wiederholung
  des terminalen #739-Laufs zur Erfüllung der heutigen Abnahme.
