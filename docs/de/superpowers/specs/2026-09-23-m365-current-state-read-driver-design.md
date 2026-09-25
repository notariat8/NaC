# Versionierter Read-only-Treiber für die Teams-Current-State-Diagnose

Status: Spec und Plan freigegeben; Offline-Builder-Reparatur in Draft-PR, Paketkandidat, Treiber-Release und realer Providerlauf nicht freigegeben

Datum: 23. September 2026

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Ausgangsbasis: `main`-Commit `1b65259b9b4953a3b048be850c7953897b8eab83`, Tree `1723094af6a398077be25f7897888faf0159069c`; gelieferte [PR #749](https://github.com/notariat8/NaC/pull/749) und [PR #751](https://github.com/notariat8/NaC/pull/751). Diese Spec ist eine neue Vorwärtsänderung und schreibt deren historische Bindungen nicht um.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-current-state-read-driver-release
plan: docs/de/superpowers/plans/2026-09-23-m365-current-state-read-driver.md
leading_issue: https://github.com/notariat8/NaC/issues/748
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Secrets
  - Platform
  - Policy
affected_artifacts:
  - AGENTS.md
  - .codex/agents/nac-policy-reviewer.toml
  - .pi/agents/nac-policy-reviewer.md
  - docs/de/superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md
  - docs/en/superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md
  - docs/de/superpowers/plans/2026-09-23-m365-current-state-read-driver.md
  - docs/en/superpowers/plans/2026-09-23-m365-current-state-read-driver.md
  - workflows/contracts/m365-current-state-read-driver-resources.contract.json
  - workflows/contracts/m365-current-state-read-driver-license-catalog.json
  - workflows/verification-contracts/m365-current-state-read-driver.verification.json
  - src/nac_bff/current_state_read_driver.py
  - src/nac_bff/current_state_read_driver_release.py
  - src/nac_bff/current_state_read_driver_sbom.py
  - src/nac_bff/current_state_access_adapters.py
  - src/nac_bff/current_state_access_composition.py
  - src/nac_bff/activation_security_windows.py
  - scripts/build_m365_current_state_read_driver.py
  - scripts/validate_m365_current_state_read_driver.py
  - scripts/quality_gate.py
  - scripts/validate_m365_current_state_access_diagnostic.py
  - scripts/validate_spec_traceability.py
  - tests/test_m365_current_state_read_driver.py
  - tests/test_build_m365_current_state_read_driver.py
  - tests/test_m365_current_state_read_driver_sbom.py
  - tests/test_m365_current_state_access_diagnostic.py
  - tests/test_m365_current_state_access_gate.py
  - tests/test_activation_security_windows.py
  - tests/test_spec_traceability.py
  - docs/de/m365-current-state-access-diagnostic.md
  - docs/en/m365-current-state-access-diagnostic.md
  - docs/de/sbom-for-ai.md
  - docs/en/sbom-for-ai.md
  - docs/de/sbom-products.md
  - docs/en/sbom-products.md
  - policies/sbom-policy.yaml
  - .github/workflows/windows-portability.yml
  - assets/docs/generic-workbench/VIS-721-manifest.json
acceptance_ids:
  - AC-748-RD-01
  - AC-748-RD-02
  - AC-748-RD-03
  - AC-748-RD-04
  - AC-748-RD-05
  - AC-748-RD-06
  - AC-748-RD-07
  - AC-748-RD-08
validation_commands:
  - python scripts/validate_m365_current_state_read_driver.py
  - python scripts/validate_m365_current_state_read_driver.py --candidate <geschützter-externer-Kandidatenpfad>
  - python -m unittest discover -s tests -p test_m365_current_state_read_driver.py
  - python -m unittest discover -s tests -p test_build_m365_current_state_read_driver.py
  - python -m unittest discover -s tests -p test_m365_current_state_read_driver_sbom.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/validate_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
  - python -m unittest discover -s tests -p test_spec_traceability.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Zweck und Grenze

Der bestehende [#748-Diagnosevertrag](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) verlangt vor einem realen Read einen reviewbaren Treiber. Die derzeitige Komposition attestiert nur den externen ausführbaren Pfad und prüft Source-, klassisches SBOM- und Ressourcen-Digests lediglich auf Hex-Format. Die hier entworfene Release-Grenze macht diese Behauptungen anhand echter Artefakte prüfbar. Sie dient weiterhin ausschließlich dem synthetischen Workspace `notary_team_01` und der Teams-App „NaC Vorgangsansicht“.

Dieses Design autorisiert weder einen Microsoft-Read noch das Konsumieren des einmaligen Diagnose-Gates. Der terminale Issue-#739-Lauf und Issue #632 bleiben unberührt.
Der `--candidate`-Befehl in der Traceability ist ein **späteres** Paket-Gate und
wird unter der aktuellen Reparaturfreigabe nicht ausgeführt; ohne reales,
separat genehmigtes Paket bleibt AC-748-RD-01 auf Artefaktebene offen.

## Scope und Designentscheidungen

1. Eine eigene, versionierte Python-Quelle implementiert ausschließlich die neun bereits geschlossenen Operationen des [#748-Vertrags](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml). `local_git_gate`, `github_gate` und `client_observation_receipt` benutzen ihre bestehenden lokalen beziehungsweise gesondert credential-write-geschützten Kanten; keine dieser Operationen erhält Microsoft-Netzwerkfähigkeit.
2. Für Windows entsteht ein eigenständiges, attestiertes ausführbares Release aus einem gepinnten Build-Werkzeug. Ein Ein-Datei-Bundle mit ungebundener Entpackung in temporäre Pfade genügt nicht. Bei einem Verzeichnis-Bundle müssen ausführbarer Einstiegspunkt **und jede** geladene Runtime-/Bibliotheksdatei anhand eines geschlossenen Manifests, Eigentümer, Current-User-only-DACL, Datei-ID, Hardlink- und Reparse-Grenze geprüft werden. Tool, Version, Build-Befehl, Source-Commit/Tree, Eingabe-Digests und Binary-Digests werden im Release-Beleg gebunden; fehlende reproduzierbare Bytegleichheit darf nicht als Reproduzierbarkeit behauptet werden.
3. Die Release-Bindung umfasst tatsächlich erzeugte CycloneDX-JSON- und SPDX-JSON-SBOMs, die AGPL-3.0-or-later-Lizenz der NaC-Quelle, deren korrespondierenden Quellcode und die Lizenzen aller eingebundenen Laufzeitkomponenten. Syft 1.52.0 meldet Windows-Binary-Pakete über `syft:location:*:path`, SPDX-Paket-/Dateibeziehungen und nicht alle gebündelten Dateien als Paket: Der Validator gleicht die beiden Formate für entdeckte Pakete ab, attestiert **jede** Bundle-Datei separat und verlangt für nicht entdeckte Dateien eine ausdrückliche Zuordnung. Er erfindet keine SBOM-Pakete oder -Dateikanten. Bei Verteilung sind [NOTICE](../../../../NOTICE), Drittanbieter-Attribution und Lizenztexte mitzuliefern. Ein operatorseitiges Inventar samt Hash reicht allein nicht: Jede Lizenz-, Quell- und Dateizuordnung muss zusätzlich einem separat versionierten, reviewten [Lizenzkatalog](../../../../workflows/contracts/m365-current-state-read-driver-license-catalog.json) entsprechen. Solange dessen Status `PENDING` ist, blockiert die Finalisierung.
4. Ein kanonisches Ressourcenmanifest bindet pro Port die exakte Kombination aus HTTPS-Origin, API-Version, Pfadschablone, erlaubten Platzhaltern, festgelegter Query-Struktur, Ausgabefeldern und maximal einem GET pro Erhebung. Platzhalterwerte stammen ausschließlich aus geschützten, bereits gebundenen Target-Inputs, nie aus CLI-Argumenten, Redirects, Antwort-URLs oder freier Suche. Paginierung, `$batch`, allgemeine Tenant-/Ressourcenlisten und beliebige KQL-Strings sind ausgeschlossen.
5. Ein eigener HTTP-Transport akzeptiert nur `GET`, keinen Body, keinen Redirect und keinen Retry. Unerwartete HTTP-Statuswerte, `Location`, Pagination-Links, Authentifizierungs-Challenges, größenüberschreitende oder nicht redigierbare Antworten blockieren vor einem weiteren Request. Rohantworten, Header, Tokens, Request-URLs und -Querys, Ziel-IDs und personenbezogene Daten werden weder ausgegeben noch persistiert – auch nicht in Fehlermeldungen oder Prozesslogs. Die vorhandenen reduzierten Port-Schemas bleiben exakt.
6. Die Microsoft-Authentifizierung ist eine gesonderte Fähigkeit. Die bestehende Azure-/M365-CLI darf nicht als No-Refresh-Beleg gelten, weil sie vor einem GET intern Token erneuern kann. Solange kein bestehender Kanal die Nicht-Erneuerung technisch und testbar garantiert, ist die Microsoft-Transport-Factory deaktiviert und endet **vor** Credential-, Authentifizierungs- und Providerzugriff mit `BLOCKED_NO_REFRESH_CAPABILITY`. Weder Tokenexport/-import noch Browser-, Broker- oder Gerätecode-Login ist ein Fallback.
7. Der neue Release-Vertrag referenziert den historischen #748-Vertrag mit dessen Dateidigest vorwärtsgerichtet; die historische Vertragsdatei und PR-#749-/PR-#751-Commit-, Tree-, Parent- und Scope-Evidence bleiben unverändert. Der Spec-Traceability-Validator muss die AC- und Plan-Parität auch für diesen neuen `spec_id` prüfen; eine leere Befehlsliste oder bloße Platzhalter zählen nicht als Nachweis. Vor dem einmaligen Gate-Consume prüft die #748-Komposition den realen Release-Beleg, das Ressourcenmanifest und die attestierte Runtime erneut. `LIVE_CAPABLE` ist nur konjunktiv mit allen bestehenden #748-Gates möglich: geschützte AVV-/DPA-Vertrags- und Receipt-Bindung, Provider-/Tenant-/Zielscope, kontospezifische Leseberechtigung, `principal_id`, exakt gebundene Owner-Entscheidung, Remote-Checks, One-Shot-Marker und Autorisierung vor Port-Factory sowie vor jedem Read. Treiber-Release-Freigabe und Freigabe genau eines realen Reads sind zwei getrennte Entscheidungen.

## Geschlossene Ressourcenfamilien

Die folgende Liste definiert die einzigen zulässigen API-Familien. Das Release-Manifest muss vor einer produktiven Freigabe deren **konkrete** Pfad- und Query-Schablonen festlegen; falls die erforderliche Projektion mit genau einem GET je Provider-Port nicht beweisbar ist, bleibt dieser Port und damit der reale Lauf gesperrt. Der bereits vereinbarte Zähler von sechs Microsoft-Reads je vollständiger Erhebung wird nicht stillschweigend erhöht.

| Port | Zulässige GET-Familie | Grenze |
| --- | --- | --- |
| Teams-Tab | Graph v1.0 `/teams/{team}/channels/{channel}/tabs/{tab}` | Nur vorab gebundener Tab, keine Kanalsuche. |
| SharePoint-App-Catalog | SharePoint `/_api/web/tenantappcatalog/AvailableApps/GetById('{product}')` auf gebundener Catalog-Site | Nur gebundenes SPFx-Produkt. |
| Entra-API-Permission | Graph v1.0 auf exakt gebundene Service-Principal-/Grant-Ressource | Keine Directory-Suche; unvollständige Permission-Projektion blockiert. |
| Azure-Function-Metadaten | ARM `Microsoft.Web/sites/{function}` mit fixierter API-Version | Keine App-Settings-, Secret- oder Content-Abfrage. |
| Azure-Function-Request-Log | Application-Insights-v1-GET `/apps/{app}/query` | Feste, parametrisierte Query ausschließlich für geschlossenes Fenster und Korrelationsbindung; keine freie KQL-Eingabe. |
| SharePoint-Zugriffsentscheidung | Graph v1.0 auf exakt gebundene synthetische Site-/List-Item-Ressource | Keine realen Akten oder Listen-/Site-Suche; fehlende vollständige Evidenz blockiert. |

Microsoft dokumentiert die [Teams-Tab-GET-API](https://learn.microsoft.com/en-us/graph/api/channel-get-tabs?view=graph-rest-1.0), die [SharePoint-ALM-GET-API](https://learn.microsoft.com/en-us/sharepoint/dev/apis/alm-api-for-spfx-add-ins), [Service-Principal-Grants](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list-oauth2permissiongrants?view=graph-rest-1.0), den [ARM-Site-GET](https://learn.microsoft.com/en-us/rest/api/appservice/web-apps/get?view=rest-appservice-2024-04-01), den [Application-Insights-Query-GET](https://learn.microsoft.com/en-us/rest/api/application-insights/query/get?view=rest-application-insights-v1) und den [Graph-List-Item-GET](https://learn.microsoft.com/en-us/graph/api/listitem-get?view=graph-rest-1.0). Diese API-Dokumentation ist kein Beleg für vorhandene Berechtigungen, einen aktiven BFF oder einen erfolgreichen Diagnose-Read.

## Risiken und Fail-closed-Entscheidungen

- Ein GET kann im aufgerufenen CLI-Client einen Refresh auslösen. Deshalb werden `az rest` und M365-CLI nicht ungeprüft als produktiver Transport eingehängt; ein Offline-Mock beweist dies ebenfalls nicht.
- Ein einzelner GET kann für einen Port nicht alle benötigten Fakten liefern. Dann lautet das Ergebnis `BLOCKED_RESOURCE_PROJECTION_INCOMPLETE`; eine zusätzliche Abfrage, ein POST-Batch oder eine verallgemeinerte Suche wird nicht improvisiert.
- Ein Build-Bundle kann Bibliotheken außerhalb des attestierten Einstiegs enthalten. Ohne vollständigen Bundle- und Lizenz-/SBOM-Nachweis lautet das Ergebnis `BLOCKED_DRIVER_RELEASE_BINDING`.
- Die Vorbereitung erzeugt nur ein Current-User-only-Bundle mit `preparation.json` und dem Status `AWAITING_INDEPENDENT_LICENSE_EVIDENCE`, aber keinen Release-Beleg. Die erste Vorbereitung ist Review-Evidence; nach Freigabe des Katalogs auf einem neuen Commit muss eine frische Vorbereitung mit **identischen** Datei-, Tool-, SBOM-, Treiberquell- und Ressourcen-Hashes erfolgen. Die Finalisierung braucht den im Git-Tree gebundenen, ausdrücklich reviewten Lizenzkatalog und geschützte externe Lizenztexte. Ein Katalogeintrag ist ein nachvollziehbarer Review-Nachweis, keine automatische Authentizitätsprüfung eines fremden Download-Servers. Ohne unabhängige Prüfung seiner Quell-Hashes und Lizenztexte bleibt `BLOCKED_LICENSE_PROVENANCE`; in diesem Auftrag wird kein neuer Paketkandidat gebaut.
- Ein aktiver Clientbeleg beweist weder einen Request im BFF noch vorhandene Request-Telemetrie. Fehlende, nicht korrelationsgebundene oder nicht redigierbare Log-Evidence blockiert; sie wird nicht zu `BFF_REQUEST_NOT_OBSERVED` geraten.
- Die Konto-/Principal-Regeln des #748-Gates gelten unverändert. Ohne konkret zitierte anwendbare externe Zwei-Personen-Pflicht ist `OWNER_SOLO_APPROVAL` zulässig und dokumentiert `four_eyes_satisfied=false`. Eine konkret zitierte anwendbare Pflicht mit nur einem Principal blockiert `BLOCKED_SINGLE_PRINCIPAL`. Verschiedene Accounts desselben Principals sind keine Vier-Augen-Trennung und erweitern keine Providerberechtigung.

## Akzeptanzkriterien

- **AC-748-RD-01:** Release-Manifest und Validator binden tatsächliche Source-, Build-, Binary-, klassische SBOM-, Lizenz-, korrespondierende Quellcode- und Ressourcenartefakte mit Hash, Version und Scope; Dummy-Digests, fehlende Drittanbieterhinweise und unvollständiges Lizenzinventar scheitern.
- **AC-748-RD-02:** Jede Runtime-Datei des Windows-Bundles wird vor Start mit dem Windows-Sicherheitsbackend an Eigentümer, DACL, Datei-ID, Hash, Hardlink und Reparse-Grenze gebunden; Austausch, Zusatzdatei und Pfaddrift blockieren.
- **AC-748-RD-03:** Das Ressourcenmanifest erlaubt nur die sechs gebundenen Microsoft-GET-Familien und höchstens einen GET je Port und Erhebung; andere Methoden, Hosts, Pfade, Querys, Pagination und Redirects scheitern ohne zweiten Request.
- **AC-748-RD-04:** Login, Token-Refresh, Credential-Export/-Import und Credential-/Provider-Write sind technisch ausgeschlossen oder der Produktionsport blockiert vor Zugriff mit `BLOCKED_NO_REFRESH_CAPABILITY`. Die Governance-Negativmatrix belegt Same-Principal-Account-Aliase ohne Vier-Augen- oder Berechtigungserweiterung, unzitierte Zwei-Personen-Behauptungen, `OWNER_SOLO_APPROVAL` mit `four_eyes_satisfied=false` und `BLOCKED_SINGLE_PRINCIPAL` bei zitierter anwendbarer Pflicht.
- **AC-748-RD-05:** Providerantworten werden in-memory auf die bestehenden Port-Felder reduziert; unbekannte oder personenbezogene Felder, Header, Rohantworten, Request-URLs/-Querys, Ziel-IDs und übergroße Daten scheitern ohne öffentliche Ausgabe oder Log-Leck.
- **AC-748-RD-06:** Synthetische Positiv- und Negativtests beweisen getrennt Source-/SBOM-/Bundle-Bindung, HTTP-Grenzen, vier Microsoft-GETs insgesamt für `SPFX_SUBJECT_MISSING` beziehungsweise zwölf für jede andere vollständige Zweifacherhebung, null weiteren Request nach blockierter Projektion, Authentifizierungsblockade, One-Shot-Gate und die vier Diagnoseklassen; sie benutzen keinen realen Provider.
- **AC-748-RD-07:** DE/EN-Spec, Plan, Verification Contract, Spec-Traceability, klassische SBOM- und AI-SBOM-Entscheidung sowie Bedien- und Sicherheitsdokumentation sind synchron. Gepinnte Build-/Runtime-Abhängigkeiten stehen im klassischen SBOM und, soweit Mindestanforderungen betroffen sind, in der AI-SBOM-Inventur oder begründet als ausstehend. Kein neues AI-Modell oder externer AI-Datenfluss wird behauptet.
- **AC-748-RD-08:** Der vollständige `main...HEAD`-Scope, lokale Pflichtgates und Remote-CI sind geprüft. Der PR bleibt Draft; Treiber-Release und genau ein realer Read verlangen danach eigene exakt gebundene Freigaben.

## Nicht-Ziele

Keine Anmeldung, kein Token-Refresh, kein Credential-Write, kein realer Microsoft-/Tenant-/Providerzugriff, kein App-/BFF-Deployment, keine Rollen- oder Berechtigungsänderung, keine #739-Freigabe, kein #632-Live-Lauf und kein Merge in dieser Design- und Planphase. Die Spec beseitigt nicht die noch fehlende No-Refresh-Authentifizierungsfähigkeit.
