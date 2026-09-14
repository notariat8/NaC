# Windows-Offline-CLI-Portabilität – Implementierungsplan

Status: Plan vom Owner freigegeben, interne Reviews bestanden, Implementierung läuft

Datum: 14. September 2026
Spec: [Windows-Offline-CLI-Portabilität](../specs/2026-09-14-windows-offline-cli-portability-design.md)
Führendes Issue: [#744](https://github.com/notariat8/NaC/issues/744)
Delivery Mode: Protected PR
Risk Gate: Human Approval

## Ziel

Die zentrale `nac`-CLI und die festgelegten lokalen M365-/SPFx-Prüfungen werden
unter nativem Windows mit Python 3.11 importierbar und ausführbar. Das
bestehende Linux-Sicherheitsbackend bleibt der einzige Ausführungspfad für
Live-Aktivierung, Recovery und Reconciliation. Windows blockiert diese Kanten
mit `PLATFORM_SECURITY_BACKEND_UNAVAILABLE` und `writes_started: false`, bevor
Credentials, State, Locks, Subprozesse, Netzwerk, Tenant oder Provider erreicht
werden.

## Änderungsflächen

| Fläche | Geplante Artefakte | Zweck |
| --- | --- | --- |
| Portable Verträge und Aufrufe | `src/nac_bff/azure_activation_contract.py`, `src/nac_bff/azure_activation_facade.py` | Plattformneutrale Typen, Fehlercode, vertrauenswürdige Capability-Prüfung und öffentliche Lazy-Load-Wrapper ohne Nebenwirkungen |
| Linux-Live-Backend | `src/nac_bff/azure_activation_runner.py`, `src/nac_bff/azure_activation_composition.py` | Typen aus dem Contract beziehen; Backend nur über die portable Fassade erreichen; bestehende Linux-Sicherheitslogik erhalten |
| Bestehende Windows-Live-Abzweige | `src/nac_bff/azure_live_commands.py`, `src/nac_bff/azure_live_commands_win.py`, `src/nac_bff/azure_activation_attestations.py` | Windows-Subprozess-, Mutex- und Live-Attestationspfade deaktivieren oder unerreichbar machen; Offline-Import erhalten |
| Zentrale CLI | `src/nac_cli/cli.py` | Windows-Sperre vor allen Live-/Recovery-/Reconciliation-Imports und Seitenkanten; Offline-Routen bleiben erreichbar |
| Produktionsadapter | `src/nac_m365_graph/business_case_type_production_adapters.py` | Import portabel machen; versiegelte GitHub-Ausführung ohne POSIX-Fähigkeit vollständig blockieren |
| Verträge und Validatoren | Live-Aktivierungsvertrag/-Verification/-Validator sowie S4f-Produktionsadaptervertrag/-Verification/-Validator | Faktischen Linux-Live-/Windows-Offline-Vertrag und den blockierten S4f-Ausführungspfad erzwingen |
| Tests | `tests/test_windows_offline_cli_portability.py`, `tests/test_spfx_bff_catalog_readback_regression.py` und die exakten Aktivierungs-/Reconciliation-/S4f-Suites | AC-744-01 bis AC-744-06 mit Windows-Negativ- und Linux-Regressionsnachweisen abdecken |
| CI | `.github/workflows/windows-portability.yml` | Nicht optionaler Windows-Job mit Python 3.11 und stabilem Check-Kontext |
| Dokumentation und Kontext | DE/EN-CLI-Doku, DE/EN-Mindestvoraussetzungen, alte Windows-Light-Spec und `agent-context/index.json` | Supportgrenze eindeutig als Windows-Offline/Linux-Live darstellen und auffindbar machen |

Die genaue Dateiliste darf sich während der testgetriebenen Umsetzung nur
innerhalb dieser Flächen ändern. Jede zusätzliche Policy-, Roadmap-, Plugin-,
Provider- oder Live-Ausführungsfläche stoppt die Umsetzung und benötigt eine
neue Scope-Prüfung.

## Reihenfolge: Test → Implementierung → Review → Fix

### 1. Reproduzierbare rote Windows-Verträge festhalten

- `tests/test_windows_offline_cli_portability.py` zunächst mit der vollständigen
  Offline- und Negativmatrix aus der Spec anlegen.
- Die echten Windows-Smokes verwenden Python 3.11 und die eingecheckten
  Standardartefakte; `fcntl` und `pwd` werden nicht als Fake-Module injiziert.
- Sämtliche neuen und verwendeten Fixtures sind ausschließlich synthetisch und
  enthalten keine realen Tenant-, Kunden-, Mandats-, Personen- oder
  Credentialdaten. Die Tests prüfen diese Herkunfts- und Inhaltsgrenze.
- Seitenkanten für Credential-, State-, Lock-, Subprozess-, Netzwerk-, Tenant-
  und Providerzugriff erhalten fehlschlagende Wächter. Erfolgreiche Offline-
  Fälle müssen für diese Wächter exakt null Aufrufe nachweisen.
- Vor der Änderung werden die bekannten Importfehler sowie die vorhandenen
  grünen Linux-Verträge protokolliert. Nur der erwartete Plattformbruch darf
  rot sein.

Der reproduzierbare native Windows-Rotlauf lautet:

```powershell
python -m unittest tests.test_windows_offline_cli_portability
```

Vor der Implementierung werden ausschließlich die dokumentierten POSIX-
Importgrenzen als Fehler akzeptiert. Kein Test darf dabei eine der sieben
Seitenkanten erreichen; jeder weitere Fehler stoppt die Umsetzung.

Die unveränderte POSIX-Baseline wird auf Linux mit folgendem schnellen
Regressionsteil und dem autoritativen vollständigen Strict Gate erfasst:

```bash
python -m unittest tests.test_nac_bff_azure_activation_cli tests.test_nac_bff_azure_live_commands tests.test_business_case_type_production_adapters
graft build
python scripts/nac.py doctor --profile strict
```

Der gezielte Unit-Test-Aufruf ist nur der schnelle Regressionsteil;
`doctor --profile strict` mit vollständiger Test-Discovery ist der maßgebliche
Linux-Gesamtnachweis.

### 2. Portable Aktivierungsfassade implementieren

- `ActivationStepError`, `ActivationContext` und `LiveActivationRequest` aus
  dem Runner in `azure_activation_contract.py` verschieben.
- Bestehende öffentliche Importpfade bei Bedarf durch reine Re-Exports
  kompatibel halten; kein Consumer darf dadurch POSIX-Primitiven vorzeitig
  laden.
- Eine deny-by-default Capability-Funktion implementieren, die ausschließlich
  vertrauenswürdige Runtime-Eigenschaften auswertet. CLI-, Request-, Env- und
  Konfigurationswerte sind keine Plattformautorität.
- Den stabilen redigierten Plattformfehler zentral erzeugen und sicherstellen,
  dass unbekannte Plattformen und unvollständige Capabilities blockieren.
- `azure_activation_facade.py` stellt die öffentlichen Callables
  `run_azure_bff_live_activation`, `reconcile_azure_bff_live_activation_lock`,
  `build_live_activation_execution_port`,
  `build_interruption_reconciliation_ports` und
  `build_function_deployment_reconciliation_ports` bereit. Jeder Wrapper
  prüft zuerst die Runtime-Capabilities und importiert Runner oder Composition
  auf Linux erst danach dynamisch.
- CLI und portable Consumer wechseln auf Contract beziehungsweise Fassade.
  Der Linux-Runner bleibt intern für bestehende Sicherheitstests importierbar;
  unter Windows wird er nie als portable API geladen.

### 3. Linux-Backend ohne Sicherheitsdelta abtrennen

- `azure_activation_runner.py` bleibt Eigentümer der bestehenden POSIX-
  Ausführung und lädt `pwd`, `fcntl`, `memfd`-, Eigentümer-, Lock- und
  No-follow-Primitiven nur als Backendvoraussetzungen.
- `azure_activation_composition.py` importiert portable Typen aus dem Contract;
  die Fassade lädt Composition und Runner erst nach bestandenem Gate.
- Eigentümerprüfung, hostglobales Locking, versiegelte `memfd`-Ausführung,
  Binary-/Toolchain-Binding, Ledger, Evidence, Recovery und Pre-write-Gates
  werden nicht neu implementiert oder abgeschwächt.
- Backend-Import- oder Capabilityfehler bleiben terminal; es gibt keinen
  Windows-Fallback und keinen No-op-Lock.
- Live-Zulassung verlangt Linux und alle vorhandenen `memfd`-, `/proc`,
  Eigentümer-, Lock-, Namespace- und No-follow-Fähigkeiten. macOS, sonstige
  POSIX-Systeme und unbekannte Plattformen bleiben ohne vollständigen Nachweis
  für Live, Recovery und Reconciliation gesperrt.

### 4. Alle öffentlichen CLI- und Python-Kanten früh sperren

- In `src/nac_cli/cli.py` die vier Spec-Kanten Live-Aktivierung,
  Finalization-Recovery, Interruption-Reconciliation und Function-Deployment-
  Reconciliation vor Owner-State-Auflösung, Repo-State, Backendimport und allen
  weiteren Seitenkanten prüfen.
- Für jeden erkannten Windows-Befehl hat der Plattformfehler Vorrang vor
  fehlenden Owner-Argumenten, Parser-Detailvalidierung und Approval-Prüfung.
- Die entsprechenden Python-Funktionen und Composition-Factorys verwenden
  dieselbe Capability-Grenze.
- POSIX behält sämtliche bestehenden Owner-Gates. Die neue Plattformprüfung
  darf weder Freigaben erzeugen noch bestehende Freigabefehler in zulässige
  Ausführung umwandeln.
- Der Plattformfehler-Payload enthält exakt `schema_version`, `status`,
  `error` und `writes_started`; `status` ist `BLOCKED`, `error` enthält nur den
  stabilen Code und `writes_started` ist `false`. Absolute Benutzerpfade, SID,
  Login, Token, Environment oder Providerantworten bleiben ausgeschlossen.

### 5. Produktionsadapter portabel importierbar machen

- Den Module-Level-Import von `fcntl` aus der portablen Importkante entfernen
  oder eindeutig als nicht verfügbare Backendfähigkeit kapseln.
- Die versiegelte GitHub-CLI-Ausführung bleibt an Linux-`memfd`, `/proc/self/fd`,
  Eigentümerprüfung, Seals, `pass_fds` und Binary-Binding gebunden.
- Ohne vollständige POSIX-Fähigkeit vor Secret-, State-, Lock-, Subprozess-,
  Netzwerk-, Tenant- und Providerzugriff mit dem gemeinsamen Plattformcode
  blockieren.
- Wächter prüfen null Aufrufe von `gh`, `gh.exe`, Azure CLI und Microsoft 365
  CLI; es wird kein ausführbares Programm über `PATH` als Ersatz akzeptiert.
- S4f-Produktionsadaptervertrag, Verification Contract, Validator, Contract-
  und CLI-Tests werden auf den portablen Offline-Status und den gemeinsamen
  blockierten Plattformcode synchronisiert. `VERIFIED_OFFLINE` darf keine
  live-fähige Adapterinstanz auf Windows behaupten.

### 6. Bestehende Windows-Live-Abzweige schließen

- In `azure_live_commands.py` jeden Windows-Dispatch zu direkter
  Subprozessausführung vor dem Start blockieren.
- `azure_live_commands_win.py` bleibt höchstens als deaktivierte historische
  Implementierung ohne erreichbare Produktkante bestehen oder wird entfernt,
  wenn keine Vertrags- oder Testreferenz sie benötigt.
- `azure_activation_attestations.py` bleibt für portable Offline-Information
  importierbar, darf auf Windows aber keine Live-Ausführbarkeit attestieren.
- `src/nac_m365_graph/sealed_toolchain.py` und der Windows-Zweig in
  `src/nac_m365_graph/mvp_test_environment_deploy.py` werden explizit auf
  weitere Live-Reichweite auditiert. Eine Codeänderung erfolgt dort nur, wenn
  eine erreichbare Windows-Live-Kante nachgewiesen wird.
- Validator und Negativtests müssen jede aktive Windows-Subprozess-, Mutex- oder
  Live-Attestationskante zurückweisen.

### 7. Vertrag, Validator und Dokumentation korrigieren

- Den Live-Aktivierungsvertrag so ändern, dass Linux mit vollständigen
  Sicherheitsfähigkeiten das einzige Live-Backend
  ist und Windows nur die portable Offline-Fassade besitzt. Die derzeitige
  nicht implementierte Behauptung eines aktivierten Windows-Light-Runners mit
  Global Mutex und handlebasierter Live-Ausführung wird entfernt oder explizit
  als deaktivierter Zukunftsscope markiert.
- Verification Contract und Validator müssen den gemeinsamen Fehlercode,
  `writes_started: false`, vertrauenswürdige Plattformerkennung, Null-
  Seitenkanten und die unveränderten Linux-Invarianten erzwingen.
- Der Live-Validator registriert `azure_activation_contract.py`,
  `azure_activation_facade.py`, `test_windows_offline_cli_portability.py` und
  `windows-portability.yml` als Pflichtquellen. Der S4f-Validator registriert
  den portablen Adapterimport und seinen Plattformblock. Beide Validatoren
  erhalten negative Validator-Tests gegen Vertrags- oder Workflowdrift.
- Der Validator prüft strukturell: Windows ist exakt offline-only; Live,
  Recovery und Reconciliation sind dort blockiert; Linux mit vollständigen
  Sicherheitsfähigkeiten bleibt einziges
  Live-Backend; der alte Windows-Light-Runner ist deaktiviert; kein aktives
  Vertragsfeld wirbt mit handlebasierter Windows-Ausführung oder Windows-
  Mutex; Fehlercode und `writes_started: false` sind exakt.
- Der Validator prüft außerdem Workflowname `NaC Windows Portability`, Job
  `windows-offline-cli`, `windows-latest`, Python 3.11, den exakten Testbefehl,
  das Fehlen von `continue-on-error`, Secrets, Login- und Live-Kommandos sowie
  Coverage-Marker für alle öffentlichen Kanten und alle sieben verbotenen
  Seitenkategorien. Ein Validator-Test muss bei Abschwächung dieser Marker rot
  werden.
- Die DE/EN-CLI-Dokumentation und Mindestvoraussetzungen erhalten eine kurze,
  identische Supportmatrix: Windows `offline`; Linux mit allen erforderlichen
  Sicherheitsfähigkeiten `offline + live`; Windows, andere POSIX-Systeme ohne
  vollständige Fähigkeiten und unbekannte Plattformen für Live/Recovery/
  Reconciliation `blocked`.
- Die alte DE/EN-Windows-Light-Spec wird als durch #744 für den aktuellen
  Lieferumfang abgelöst markiert; sie darf keine aktuelle Windows-Live-
  Unterstützung mehr suggerieren.
- `agent-context/index.json` verweist auf Spec, Plan, Code, Vertrag, Validator,
  Tests und CI. Es werden keine Policy-, SBOM- oder Gantt-Inhalte künstlich
  geändert; die vorhandenen Windows-/Python-SBOM-Einträge werden nur geprüft
  und in der PR-Evidence festgehalten.

### 8. Native Windows-CI hinzufügen

- `.github/workflows/windows-portability.yml` mit Workflowname
  `NaC Windows Portability`, PR-/Push-Triggern ohne Path-Filter und Jobname
  `windows-offline-cli` anlegen.
- Job läuft auf `windows-latest`, richtet Python 3.11 ein, installiert das Repo
  ohne neue Abhängigkeit und führt mindestens
  `python -m unittest tests.test_windows_offline_cli_portability
  tests.test_spfx_bff_catalog_readback_regression` aus.
- Kein `continue-on-error`, kein Secret, keine Anmeldung und kein Live-Smoke.
- Der resultierende Check-Kontext
  `NaC Windows Portability / windows-offline-cli` muss auf dem PR erfolgreich
  sein. Nachdem der Kontext erstmals erschienen ist, benötigt seine Aufnahme
  in die Branch Protection oder das Repository-Ruleset ein separates exaktes
  Owner/Admin-Gate. Erst nach dieser Freigabe wird die Konfiguration geändert
  und anschließend read-only verifiziert, dass der Kontext tatsächlich
  verpflichtend ist.
- Echte Child-Process-Smokes laufen mit vergiftetem Sentinel-`PATH`, isolierten
  temporären Home-/Credential-/Config-Pfaden, Import-Trace aus dem Child und im
  Child installierten Netzwerk-/Subprozesswächtern. In-Process-Call-Counts
  ergänzen diese Nachweise, ersetzen sie aber nicht.

### 9. Implementierungsreview und Fix-Schleife

- Vollständige Arbeitsdiff durch isolierte Read-only-Reviews prüfen lassen:
  Plattform/Policy für Fail-closed-Grenze, Validation für AC-/CI-Abdeckung und
  Dokumentation für DE/EN-Parität.
- Jeder Befund erhält Schweregrad, betroffene Kante und konkrete Evidence.
- Blockierende und mittlere Befunde vor Abnahme beheben; danach dieselben
  Reviewer gezielt nachprüfen lassen.
- Keine Tenant-, Provider-, Credential-, Live-, Recovery- oder
  Reconciliation-Aktion als Teil des Reviews ausführen.

### 10. Lokale und Remote-Abnahme

- Windows: `python -m unittest tests.test_windows_offline_cli_portability
  tests.test_spfx_bff_catalog_readback_regression`.
- Linux Aktivierung: `python -m unittest
  tests.test_nac_bff_azure_activation_cli tests.test_nac_bff_azure_live_commands
  tests.test_nac_bff_azure_activation_composition
  tests.test_nac_bff_azure_activation_runner
  tests.test_nac_bff_azure_interruption_reconciliation
  tests.test_nac_bff_azure_function_deployment_reconciliation
  tests.test_m365_azure_bff_live_activation_contract
  tests.test_spfx_bff_catalog_readback_regression`.
- Linux S4f: `python -m unittest
  tests.test_business_case_type_production_adapters
  tests.test_business_case_type_production_adapters_contract
  tests.test_business_case_type_production_adapters_cli
  tests.test_sqlite_evidence_staging_outbox`.
- Anschließend `python scripts/validate_m365_azure_bff_live_activation.py`,
  `python scripts/validate_business_case_type_production_adapters.py`, die
  beiden Agent-Context-Validatoren, `graft build`, `graft check` und
  `python scripts/nac.py doctor --profile strict`.
- Spec-Traceability, Sprachparität, Linkprüfung und alle registrierten
  Vertragsvalidatoren müssen bestehen.
- Vor Push und PR-Abschluss Datei- und Commitliste sowie die vollständige Diff
  `origin/main...HEAD` inhaltlich prüfen; unfreigegebenen Scope entfernen.
- Commit und – als sichtbare YELLOW-/Batch-Freigabe – Push auf
  `codex/744-windows-offline-cli`; anschließend mit derselben klar begrenzten
  Freigabe einen geschützten PR mit `Closes #744` erstellen, kein Auto-Merge.
- Nach dem ersten erfolgreichen Auftreten des Windows-Kontexts die exakte
  Branch-Protection-/Ruleset-Änderung als eigenes Owner/Admin-Gate vorlegen.
  Ohne Freigabe keine Governance-Mutation und kein Abschluss von AC-744-07.
- Nach Freigabe den Kontext als Required Check eintragen und die Konfiguration
  read-only nachweisen; erst danach `gh pr checks --required --watch` verwenden.
- Remote auf die vier exakten Checkkontexte warten: Windows Portability,
  Secret Scan, Privacy Lint und NaC Quality Gate. Erst bei vollständigem Erfolg
  ist der PR reviewbereit; Merge bleibt separat owner-/rollen-gated.
- Vor Merge beziehungsweise Abschluss des Protected-PR-Delivery-Modes muss die
  Human-Approval-Evidence eine nach dem Rollenmodell zulässige Rolle,
  insbesondere `prozessverantwortung` oder `freigabeverantwortung`,
  nachvollziehbar ausweisen. Fehlt dieser Nachweis, wird gestoppt und nicht
  gemerged.

## AC-zu-Evidence-Matrix

| AC | Primärer Nachweis | Ergänzender Nachweis |
| --- | --- | --- |
| AC-744-01 | Windows-Test: echter Import plus drei Hilfeaufrufe auf Python 3.11 | `NaC Windows Portability / windows-offline-cli` |
| AC-744-02 | Parametrisierte Windows-Smokes für `validate`, `plan`, `bpmn-viewer-plan` mit Exit-/Status-/Guard-Assertions | Ausschließlich synthetische Standardartefakte und kein geladenes POSIX-Backend |
| AC-744-03 | Parametrisierte Live-Kanten mit Plattformcode, `writes_started is False` und Nullaufrufen für Credentials, State, Locks, Subprozesse, Netzwerk, Tenant und Provider | Redaktionsassertions und Backend nicht in `sys.modules` |
| AC-744-04 | Parametrisierte Recovery-/Reconciliation-Kanten und manipulierte Plattformhinweise | Identische Null-Seitenkanten wie AC-744-03 |
| AC-744-05 | Import der Produktionsadapter und versiegelter Ausführungsblock auf Windows | Nullaufrufe für `gh`, `gh.exe`, Azure CLI und M365 CLI |
| AC-744-06 | Exakt aufgelistete Linux-Aktivierungs-, Runner-, Composition-, Reconciliation-, SPFx- und S4f-Suites | Beide Verträge und Validatoren sowie Strict Doctor |
| AC-744-07 | Traceability-/Sprach-/Linkvalidatoren, Graft und Strict Doctor | Vollständige `origin/main...HEAD`-Prüfung und vier erfolgreiche Remote-Checks |

## Abbruchkriterien

Die Umsetzung stoppt und fordert neuen Owner-Input, wenn:

- eine sichere Windows-Offline-Fassade nur durch Abschwächung eines POSIX-
  Live-Sicherheitsvertrags erreichbar wäre;
- ein neues Paket, ein externer Provider, ein Tenant-Zugriff oder eine
  Credential-/Secret-Aktion erforderlich wird;
- der Scope Windows-Live-Aktivierung oder Windows-Recovery erfordert;
- die vollständige PR-Diff fremden oder nicht freigegebenen Scope enthält;
- verpflichtende Remote-Checks nicht erfolgreich werden und eine Behebung
  außerhalb der freigegebenen #744-Flächen läge.
- der neue Windows-Kontext nach seinem ersten Lauf als Required Check
  eingetragen werden muss, aber die exakte Owner/Admin-Freigabe für diese
  Branch-Protection-/Ruleset-Änderung fehlt.

## Nicht Teil dieses Plans

Kein App-Catalog-Upload, kein SharePoint-Deploy, kein Graph-/Azure-/M365-Read
oder -Write, kein Login, kein Credential-Read, keine Recovery-Ausführung, kein
Windows-Live-Backend, kein Merge und keine automatische Freigabe.
