# Windows-Offline-CLI-Portabilität

Status: Design freigegeben, interne Reviews bestanden, Owner-Spec-Freigabe ausstehend

Datum: 14. September 2026
Führendes Issue: [#744](https://github.com/notariat8/NaC/issues/744)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: windows-offline-cli-portability
leading_issue: https://github.com/notariat8/NaC/issues/744
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Security
  - Platform
  - Validation
  - Human Approval
acceptance_ids:
  - AC-744-01
  - AC-744-02
  - AC-744-03
  - AC-744-04
  - AC-744-05
  - AC-744-06
  - AC-744-07
validation_commands:
  - python -m unittest tests.test_windows_offline_cli_portability
  - python -m unittest tests.test_nac_bff_azure_activation_cli tests.test_nac_bff_azure_live_commands tests.test_business_case_type_production_adapters
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git diff --name-status origin/main...HEAD
  - git log --oneline origin/main..HEAD
  - git diff origin/main...HEAD
  - git diff --check origin/main...HEAD
  - gh pr checks --required --watch
```

## Ausgangslage

Die zentrale `nac`-CLI kann unter Windows derzeit nicht einmal für reine
Offline-Prüfungen importiert werden. POSIX-exklusive Importe wie `fcntl` und
`pwd` werden beim Modulimport geladen, obwohl ihre abgesicherten
Live-Funktionen gar nicht aufgerufen werden. Dadurch scheitern insbesondere
lokale M365-/SPFx-Prüfungen vor der eigentlichen Befehlsauswahl.

Der bestehende Live-Aktivierungspfad ist dagegen bewusst an POSIX-Sicherheits-
mechanismen wie versiegelte In-Memory-Binaries, Eigentümerprüfung und
prozessweite Locks gebunden. Diese Garantien dürfen nicht durch einen
scheinbar kompatiblen Windows-Ersatz abgeschwächt werden.

## Entscheidung

NaC erhält eine portable Offline-Fassade und ein davon dynamisch getrenntes
POSIX-Live-Backend. Die Fassade enthält nur plattformneutrale Verträge,
Datentypen, Fehlercodes und Capability-Entscheidungen. Das POSIX-Backend wird
erst geladen, nachdem die Fassade die angeforderte Operation als auf der
aktuellen Plattform zulässig bewertet hat.

Windows unterstützt damit die zentrale CLI und lokale M365-/SPFx-Prüfungen.
Live-Aktivierung und Recovery bleiben unter Windows ausdrücklich gesperrt und
brechen mit dem stabilen, redigierten Fehlercode
`PLATFORM_SECURITY_BACKEND_UNAVAILABLE` ab. Dieser Abbruch muss erfolgen,
bevor Credentials gelesen, Zustands- oder Lock-Dateien berührt, Subprozesse
gestartet oder Netzwerk- beziehungsweise Providerzugriffe ausgeführt werden.

## Scope

- Portable, nebenwirkungsfreie Aktivierungsverträge und Capability-Prüfung in
  einem plattformneutral importierbaren Modul unter
  [`src/nac_bff/`](../../../../src/nac_bff/).
- Dynamisches Laden des bestehenden POSIX-Live-Backends ausschließlich hinter
  einer erfolgreich bestandenen Plattform- und Capability-Prüfung.
- Importierbarkeit der zentralen [`nac`-CLI](../../../../src/nac_cli/cli.py)
  sowie die unten festgelegten lokalen M365-/SPFx-Offline-Smokes unter nativem
  Windows und Python 3.11.
- Importierbarkeit der M365-Produktionsadapter unter Windows; deren
  POSIX-gebundene versiegelte Ausführung bleibt fail-closed.
- Windows-CI für Import, Hilfe, Offline-Prüfungen und negative Live-/Recovery-
  Tests sowie unveränderte Linux-Prüfung des POSIX-Backends.
- Nachvollziehbare Verknüpfung von Issue, Spec, Plan, AC-IDs und
  Validierungsnachweisen.

## Nicht-Ziele

- Keine Windows-Live-Aktivierung und kein Windows-Recovery.
- Kein Ersatz von `memfd`, `fcntl`, `pwd`, POSIX-Eigentümerprüfung,
  Mount-Namespaces oder Binary-Binding durch schwächere Windows-Mechanismen.
- Kein `gh.exe`-, Azure-CLI-, Microsoft-365-CLI- oder anderer Subprozess-
  Fallback für gesperrte Windows-Live-Pfade.
- Keine Credential-Abfrage oder Anmeldung.
- Keine Tenant-Aktion, weder lesend noch schreibend, und keine Provideraktion.
- Keine App-Catalog-Installation oder SharePoint-Bereitstellung.
- Keine Änderung von Owner-Gates, Locking-Semantik, Hash-/Binary-Bindings,
  Ledger, Evidence oder Freigabeverträgen.
- Keine Reaktivierung des archivierten OCI-Releasepfads.

## Architektur

### Portable Offline-Fassade

Ein neues plattformneutrales Vertragsmodul, vorgesehen als
`src/nac_bff/azure_activation_contract.py`, besitzt mindestens:

- die stabilen Datentypen `ActivationStepError`, `ActivationContext` und
  `LiveActivationRequest`, soweit sie von CLI, Tests und Komposition geteilt
  werden;
- den stabilen Fehlercode `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`;
- eine reine Capability-Entscheidung ohne Datei-, Prozess-, Credential-,
  Netzwerk- oder Providerzugriff;
- eine eindeutige Klassifikation von Offline-, Live- und Recovery-Operationen.

Der Import der Fassade darf kein POSIX-exklusives Modul transitiv laden.
Die Plattformentscheidung stammt ausschließlich aus vertrauenswürdiger
Runtime-Erkennung. Request-, CLI-, Konfigurations- und Umgebungswerte dürfen
sie weder überschreiben noch eine POSIX-Fähigkeit vortäuschen.

### POSIX-Live-Backend

Der bestehende gehärtete Live-Runner bleibt das einzige Backend für
Live-Aktivierung und Recovery. Seine Sicherheitsgarantien bleiben unverändert.
Die Kompositionsschicht lädt ihn dynamisch und nur dann, wenn die portable
Capability-Prüfung die aktuelle Plattform zugelassen hat. Ein Fehler beim
Laden oder Validieren des Backends ist terminal und fail-closed.

### Produktionsadapter

[`business_case_type_production_adapters.py`](../../../../src/nac_m365_graph/business_case_type_production_adapters.py)
darf `fcntl` nicht mehr als Voraussetzung für den bloßen Modulimport behandeln.
Die tatsächlich versiegelte GitHub-Ausführung bleibt jedoch an den vorhandenen
Linux-`memfd`-Pfad gebunden. Fehlt diese Plattformfähigkeit, wird vor Secret-
oder Subprozesszugriff derselbe stabile Plattformfehler geliefert. Ein
schwächerer Windows-Ausführungspfad wird nicht eingeführt.

## Ausführungsflüsse

### Windows-Offline

1. Python lädt die zentrale CLI und die portable Fassade.
2. Der Parser wählt einen Offline-Befehl, beispielsweise eine lokale
   M365-/SPFx-Vertragsprüfung.
3. Nur lokale, nicht geheime Eingaben und Repo-Artefakte werden verarbeitet.
4. Der Befehl liefert sein normales Ergebnis; das POSIX-Live-Backend wurde zu
   keinem Zeitpunkt importiert oder geladen.

Die verbindliche Windows-Offline-Matrix nutzt die eingecheckten Standard-
artefakte
[`nac-mvp.teams-sharepoint.json`](../../../../deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json)
und
[`nac-bpmn-viewer.provisioning.json`](../../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json):

| Aufruf | Erwartung |
| --- | --- |
| `python -c "import nac_cli.cli"` | Exit `0`; kein Import von `fcntl`, `pwd` oder dem POSIX-Live-Backend |
| `python scripts/nac.py --help` | Exit `0` |
| `python scripts/nac.py m365 --help` | Exit `0` |
| `python scripts/nac.py m365 teams-sharepoint --help` | Exit `0` |
| `python scripts/nac.py m365 teams-sharepoint validate --format json` | Exit `0`; `status: PASSED` |
| `python scripts/nac.py m365 teams-sharepoint plan --format json` | Exit `0`; `status: PASSED` |
| `python scripts/nac.py m365 teams-sharepoint bpmn-viewer-plan --format json` | Exit `0`; `status: PASSED`; `mutates_tenant_now: false` und `live_apply_implemented: false` |

Jeder Matrixfall muss zusätzlich Nullaufrufe für Credentials, Netzwerk und
Provider sowie das Nichtladen des POSIX-Live-Backends nachweisen.

### Windows-Live oder Windows-Recovery

1. Python lädt die zentrale CLI und die portable Fassade.
2. Die Capability-Prüfung erkennt eine Live- oder Recovery-Operation auf
   Windows.
3. Die Ausführung endet mit `PLATFORM_SECURITY_BACKEND_UNAVAILABLE` und
   `writes_started: false`.
4. Es gab davor keinen Credential-, State-, Lock-, Subprozess-, Netzwerk- oder
   Providerzugriff; das POSIX-Live-Backend wurde nicht geladen.

Die endliche Negativtestmatrix umfasst diese öffentlichen Kanten:

| Klasse | Öffentliche Kante |
| --- | --- |
| CLI Live | `m365 teams-sharepoint bff-azure-activate-live` |
| CLI Recovery | `m365 teams-sharepoint bff-azure-activation-recovery` |
| CLI Reconciliation | `m365 teams-sharepoint bff-azure-activation-interruption-reconcile` |
| CLI Reconciliation | `m365 teams-sharepoint bff-azure-function-deployment-reconcile` |
| Python Live | `run_azure_bff_live_activation` und `build_live_activation_execution_port` |
| Python Recovery | `reconcile_azure_bff_live_activation_lock` |
| Python Reconciliation | `build_interruption_reconciliation_ports` und `build_function_deployment_reconciliation_ports` |

Jeder Fall erwartet denselben Fehlercode, `writes_started is False`, exakt
null Aufrufe aller verbotenen Seitenkanten und ein nicht in `sys.modules`
geladenes POSIX-Backend. Ein manipulierter Plattform- oder Capability-Hinweis
aus Request, CLI, Konfiguration oder Umgebung ist als zusätzlicher Negativfall
enthalten.

### POSIX-Live

1. Die portable Fassade klassifiziert die Operation und lässt das vorhandene
   POSIX-Sicherheitsbackend zu.
2. Die Kompositionsschicht lädt das Backend dynamisch.
3. Alle bestehenden Owner-, Attestierungs-, Locking-, Eigentümer-, Binary-
   Binding-, Ledger- und Evidence-Prüfungen bleiben wirksam.
4. Bereits bestehende Live-Validatoren und Negativtests müssen unverändert
   bestehen.

## Fehler- und Sicherheitsvertrag

- Der öffentliche Plattformfehler ist stabil, strukturiert und redigiert.
- Der Fehler enthält keine Pfade zu Credentials, Tokens, Umgebungswerte oder
  Providerantworten.
- `writes_started` ist für den Windows-Plattformabbruch immer `false`.
- Unbekannte Plattformen, fehlende Backend-Fähigkeiten oder Importfehler des
  Sicherheitsbackends werden nicht als Offline-Freigabe interpretiert.
- Tests instrumentieren alle verbotenen Seitenkanten und schlagen fehl, sobald
  Windows-Live oder Windows-Recovery eine davon erreicht.

## CI- und Validierungsdesign

Eine native Windows-CI-Lane prüft mindestens:

- Import der zentralen CLI und ihrer M365-/SPFx-Abhängigkeiten;
- Hilfe-/Parserpfade ohne POSIX-Importfehler;
- ausgewählte Offline-M365-/SPFx-Validatoren;
- Live- und Recovery-Negativtests mit Wächter-Doubles für Credentials, State,
  Locks, Subprozesse, Netzwerk und Provider;
- den stabilen Fehlercode und `writes_started: false`;
- die Importierbarkeit der Produktionsadapter ohne Aktivierung ihrer
  versiegelten Ausführung.

Sie läuft als GitHub-Actions-Job `windows-offline-cli` im Workflow
`NaC Windows Portability` auf `windows-latest` mit Python 3.11. Der stabile
Check-Kontext lautet `NaC Windows Portability / windows-offline-cli` und muss
im geschützten PR erfolgreich sein. Die Lane führt
`python -m unittest tests.test_windows_offline_cli_portability` aus; dieses
Testmodul bildet AC-744-01 bis AC-744-05 vollständig und parametrisiert ab.
Alle Fixtures sind ausschließlich synthetisch und enthalten keine Tenant-,
Kunden-, Mandats- oder Credentialdaten.

Die bestehende Linux-Lane prüft weiterhin das reale POSIX-Live-Backend und
seine vollständigen Sicherheitsverträge. Windows-Erfolg darf Linux-Gates weder
ersetzen noch überspringen. Beide Lanes werden im geschützten PR als
verpflichtende Quality-Gates behandelt.

## Akzeptanzkriterien

- **AC-744-01:** Die zentrale `nac`-CLI besteht unter `windows-latest` mit
  Python 3.11 den in der Windows-Offline-Matrix festgelegten Import und alle
  drei Hilfeaufrufe ohne `fcntl`-, `pwd`- oder sonstigen POSIX-Importfehler.
- **AC-744-02:** `validate`, `plan` und `bpmn-viewer-plan` bestehen unter
  Windows mit den festgelegten Standardartefakten, erwarteten Exit-Codes und
  Statuswerten; sie laden das POSIX-Live-Backend nicht und erreichen keine
  Credential-, Netzwerk-, Tenant- oder Providerkante.
- **AC-744-03:** Jede in der Negativtestmatrix benannte Windows-Live-Kante endet stabil mit
  `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`, `writes_started: false` und ohne
  Credential-, State-, Lock-, Subprozess-, Netzwerk- oder Providerzugriff.
- **AC-744-04:** Jede in der Negativtestmatrix benannte Windows-Recovery- und
  Reconciliation-Kante erfüllt dieselbe fail-closed Grenze wie AC-744-03;
  Plattformhinweise aus nicht vertrauenswürdigen Eingaben können die Sperre
  nicht umgehen.
- **AC-744-05:** Die Produktionsadapter sind unter Windows importierbar; ihre
  POSIX-gebundene versiegelte Ausführung bleibt vor jeder in AC-744-03
  genannten Seitenkante gesperrt. Wächter bestätigen null Aufrufe von `gh`,
  `gh.exe`, Azure CLI und Microsoft 365 CLI.
- **AC-744-06:** Die POSIX-Live- und Recovery-Verträge, einschließlich
  Eigentümerprüfung, `fcntl`-Locking, versiegelter `memfd`-Ausführung,
  Binary-/Toolchain-Binding, Recovery und Pre-write-Guards, bestehen in der
  Linux-Lane mit den vorhandenen vollständigen Aktivierungs- und
  Produktionsadapter-Suites. Diese Sicherheitstests werden weder gelöscht,
  umbenannt noch abgeschwächt.
- **AC-744-07:** Spec-Traceability, deutsche/englische Parität, Windows-CI,
  Linux-CI und das strikte NaC-Quality-Gate bestehen. Datei- und Commitliste
  werden geprüft; die vollständige Ausgabe von `git diff origin/main...HEAD`
  wird inhaltlich geprüft und `git diff --check origin/main...HEAD` besteht.
  `gh pr checks --required --watch` bestätigt mindestens
  `NaC Windows Portability / windows-offline-cli`,
  `Privacy and Secrets Guard / secret-scan`,
  `Privacy and Secrets Guard / privacy-lint` und
  `NaC Quality Gate / quality-gate` als erfolgreich.

## Risiken und Maßnahmen

| Risiko | Maßnahme |
| --- | --- |
| Ein transitiver Import lädt das POSIX-Backend weiterhin unter Windows. | Import-Isolationstest und Wächter gegen `fcntl`, `pwd` und das Backendmodul. |
| Ein früher CLI-Helfer greift vor der Capability-Prüfung auf State oder Credentials zu. | Seitenkanten als fehlschlagende Test-Doubles instrumentieren und Reihenfolge ausdrücklich testen. |
| Die Trennung verändert unbemerkt Linux-Live-Verhalten. | Bestehende Linux-Vertragstests unverändert ausführen und Backend-Logik nicht neu implementieren. |
| Ein optionaler Import wird fälschlich als Sicherheitsfreigabe behandelt. | Capability-Prüfung ist explizit deny-by-default; Backendfehler sind terminal. |
| Dokumentation suggeriert Windows-Live-Fähigkeit. | CLI- und Betriebsdokumentation benennt Windows ausschließlich als Offline-Fassade. |

## Auslieferung und Betrieb

Die Umsetzung erfolgt ausschließlich per geschütztem Pull Request gegen den
Zielbranch. Vor Review werden vollständige Datei- und Commitliste sowie die
Diff `base...head` geprüft. Es gibt keinen automatischen Merge und keine
Live-Aktivierung im Rahmen dieses Issues.

Der Implementierungsplan wird nach Freigabe dieser Spec in beiden Sprachen
erstellt, im Traceability-Block verlinkt und ordnet jedes AC einem konkreten
Test, Validator oder Remote-Check zu. Die Human-Approval-Evidence muss eine
nach dem Rollenmodell zulässige Freigaberolle nachvollziehbar ausweisen.

Die Änderung führt keine neue Laufzeitabhängigkeit und keinen neuen externen
Provider ein; eine SBOM-/AI-SBOM-Erweiterung ist daher nicht vorgesehen. Sie
ändert weder Roadmap, Produktumfang noch Meilenstein und benötigt deshalb kein
künstliches Gantt-Update.
Vor PR-Abschluss wird zusätzlich dokumentiert, dass die bestehenden Windows-
und Python-Einträge der SBOM/AI-SBOM geprüft wurden und kein Komponenten- oder
Boundary-Delta vorliegt.

## Verwandte Artefakte

- [Windows Light Runner – Design-Spec](2026-08-09-windows-light-runner-design.md)
- [`m365-azure-bff-live-activation.contract.json`](../../../../workflows/contracts/m365-azure-bff-live-activation.contract.json)
- [CLI-Dokumentation](../../cli.md)
- [Mindestvoraussetzungen](../../minimum-requirements.md)
- [`technology-policy.yaml`](../../../../policies/technology-policy.yaml)
- [`data-protection-policy.yaml`](../../../../policies/data-protection-policy.yaml)
