# Sicherer Windows-Abschluss der partiellen M365-BFF-Aktivierung

Status: Spec und Plan vom Owner freigegeben; lokale Windows-Implementierung in Arbeit; operative Ausführung blockiert

Datum: 17. September 2026

Führendes Issue: [#746](https://github.com/notariat8/NaC/issues/746)

Zu überarbeitender Implementierungsplan: [Sicherer Abschluss der partiellen M365-BFF-Aktivierung](../plans/2026-09-15-m365-bff-failed-partial-safe-completion.md)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-failed-partial-safe-completion
leading_issue: https://github.com/notariat8/NaC/issues/746
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Platform
  - Security
affected_artifacts:
  - .github/workflows/governance-policy-sync.yml
  - .github/workflows/windows-portability.yml
  - AGENTS.md
  - agent-context/index.json
  - assets/docs/generic-workbench/VIS-721-manifest.json
  - docs/de/cli.md
  - docs/de/minimum-requirements.md
  - docs/de/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
  - docs/de/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
  - docs/de/role-model.md
  - docs/en/cli.md
  - docs/en/minimum-requirements.md
  - docs/en/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
  - docs/en/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
  - docs/en/role-model.md
  - policies/access-control-policy.yaml
  - policies/github-identity-registry.json
  - policies/github-identity-registry.schema.json
  - policies/process-policy.yaml
  - policies/role-model-policy.yaml
  - sbom/ai/nac-ai-sbom-draft.json
  - sbom/ai/nac-ai-sbom-export-mapping.json
  - scripts/onboarding_wizard.py
  - scripts/quality_gate.py
  - scripts/validate_agent_authentication_boundary.py
  - scripts/validate_identity_registry.py
  - scripts/validate_m365_azure_bff_live_activation.py
  - scripts/validate_m365_bff_failed_partial_safe_completion.py
  - src/nac_bff/activation_security_backend.py
  - src/nac_ai_sbom/export_mapping.py
  - src/nac_bff/activation_security_linux.py
  - src/nac_bff/activation_security_windows.py
  - src/nac_bff/azure_activation_attestations.py
  - src/nac_bff/azure_activation_composition.py
  - src/nac_bff/azure_activation_contract.py
  - src/nac_bff/azure_activation_runner.py
  - src/nac_bff/azure_live_commands.py
  - src/nac_bff/azure_live_commands_win.py
  - src/nac_m365_graph/mvp_test_environment_deploy.py
  - src/nac_m365_graph/node_runtime_integrity.py
  - src/nac_m365_graph/sealed_toolchain.py
  - tests/test_m365_azure_bff_live_activation_contract.py
  - tests/test_m365_bff_failed_partial_safe_completion.py
  - tests/test_activation_security_backend.py
  - tests/test_activation_security_windows.py
  - tests/test_agent_authentication_boundary.py
  - tests/test_identity_registry.py
  - tests/test_validate_windows_offline_cli_portability.py
  - tests/test_windows_offline_cli_portability.py
  - workflows/contracts/m365-azure-bff-live-activation.contract.json
  - workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml
  - workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml
acceptance_ids:
  - AC-746-01
  - AC-746-02
  - AC-746-03
  - AC-746-04
  - AC-746-05
  - AC-746-06
  - AC-746-07
  - AC-746-08
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/validate_ai_sbom.py
  - python scripts/validate_m365_bff_failed_partial_safe_completion.py
  - python scripts/validate_m365_azure_bff_live_activation.py
  - python -m unittest discover -s tests -p test_activation_security*.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git diff --check origin/main...HEAD
```

## Zweck und Abgrenzung

Diese Spec ersetzt die lokale POSIX-Voraussetzung des bisherigen Issue-#746-
Designs durch einen vollständigen nativen Windows-Pfad. Alle verpflichtenden
lokalen Entwicklungs-, Build-, Test-, Paketierungs-, Reconciliation-,
Freigabe- und Deployment-Steuerungsschritte müssen auf dem Windows-11-
Arbeitsplatz funktionieren. WSL, Docker, SBX, eine Linux-VM oder ein separater
Linux-Runner sind weder Voraussetzung noch Fallback.

Linux bleibt ausschließlich innerhalb der Azure-Zielumgebung zulässig. Die
Azure Function darf als `functionapp,linux` laufen, und Azure OneDeploy darf
Linux-native Abhängigkeiten im gebundenen Remote Build materialisieren. Daraus
entsteht keine lokale Linux-Abhängigkeit.

Die Spec beschreibt außerdem den sicheren Weg vom dokumentierten partiellen
Zustand zu einem möglichen neuen, separat freizugebenden Live-Lauf für den rein
synthetischen Workspace `notary_team_01`. Sie autorisiert selbst weder einen
Provider-Write noch die Issue-#739-Quarantänefreigabe, einen Live-Retry oder
einen Issue-#632-Live-Lauf.

Die sichtbare Teams-Meldung `Kein Zugriff auf diesen Arbeitsbereich` wird nicht
durch eine UI-Umgehung behoben. Der Abschluss muss die Kette
`Teams/SPFx -> AadHttpClient -> Entra-geschützter BFF -> serverseitiges
Zugriffsgate -> Microsoft Graph REST v1.0` nachweisen.

## Verbindliche Plattformgrenze

```yaml
local_development_platform: windows
local_build_platform: windows
local_test_platform: windows
local_packaging_platform: windows
local_reconciliation_platform: windows
local_deployment_control_platform: windows
local_live_activation_control_platform: windows
wsl_required: false
docker_required: false
linux_host_required: false
posix_runner_required: false
azure_function_runtime:
  linux_allowed: true
azure_remote_build:
  linux_allowed: true
linux_ci:
  allowed: true
  required_gate: false
  may_block_windows_delivery: false
```

Ein optionaler Linux-CI-Lauf darf nur die Kompatibilität mit der erlaubten
Azure-Linux-Runtime prüfen. Er ersetzt keinen Windows-Nachweis und darf die
Windows-Lieferung nicht allein blockieren.

Die [Microsoft-first, On-Prem-AI Zielarchitektur](../../architecture/microsoft-first-onprem-target-architecture.md)
bleibt unverändert: Microsoft 365 bildet die Benutzer-, Identitäts- und
Datenkante; lokale NaC-Arbeitsplätze und die Entwicklung laufen unter Windows;
Azure-Dienste dürfen ihre verwaltete Linux-Runtime verwenden.

## Provenienz und aktueller Ausgangszustand

GitHub-Flächen sind kein Produkt- oder Runtimezustand. Die folgenden Issues
haben getrennte Rollen:

- [#620](https://github.com/notariat8/NaC/issues/620) ist historische Provenienz
  der sichtbaren M365-MVP-Testumgebung.
- [#632](https://github.com/notariat8/NaC/issues/632) bleibt der maßgebliche
  Vertrag und die separate Freigabefläche für einen neuen Live-Lauf.
- [#739](https://github.com/notariat8/NaC/issues/739) enthält die aktuelle
  quarantänisierte Laufspur. Der dokumentierte Lauf
  `nac-bff-live-20260908-issue739-v4` endete an Schritt 7
  `deploy_function_package` mit
  `AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS`.
- [#743](https://github.com/notariat8/NaC/issues/743) ist eine andere historische
  Unterbrechung und darf nicht zur Rekonstruktion von #739 verwendet werden.
- [#744](https://github.com/notariat8/NaC/issues/744) führte die portable
  Windows-Offline-CLI und die derzeitige Linux-only-Live-Sperre ein. Die
  Sperre bleibt bis zur validierten Windows-Implementierung fail-closed aktiv,
  ist aber keine Zielarchitektur mehr.
- [#746](https://github.com/notariat8/NaC/issues/746) führt die sichere
  Windows-Migration und die spätere Abschlusskette.

Alte Evidence oder alte Kommentare sind keine aktuelle Freigabe. Der lokale
und providerseitige Zustand bleibt `UNVERIFIED` und damit `BLOCKED`, bis der
neue Windows-Preflight und die doppelte read-only Inspection frisch bestehen.

## Bewertete Lösungswege

### A. Windows-nativer Kontrollpfad mit Azure-Linux-Ziel – gewählt

Der vollständige lokale Ablauf wird unter Windows abgesichert. Der Controller
erzeugt gebundene Eingabepakete und steuert Azure, Entra, Graph, SharePoint und
M365 von Windows aus. Die Azure Function und ihr Remote Build dürfen Linux
verwenden. Dieser Weg entspricht der real verfügbaren Entwicklungsumgebung und
vermeidet eine zusätzliche Betriebsplattform.

### B. Separater POSIX-Runner – verworfen

Ein Linux-Rechner, WSL, eine VM oder SBX würde lediglich die bisherige
Implementierungsbeschränkung konservieren. Credentials, Arbeitszustand und
Evidence müssten über eine zusätzliche Hostgrenze transportiert werden. Das ist
für NaC fachlich nicht erforderlich und widerspricht der verbindlichen lokalen
Windows-Plattform.

### C. Manueller Cleanup oder unmittelbarer Rerun – verworfen

Manuelles Unlock, Löschen, Berechtigungsänderungen oder ein Voll-Rerun vor der
Reconciliation würden die #739-Provenienz und ihre Quarantäne umgehen. Dieser
Weg bleibt gesperrt.

## Windows-Sicherheitsbackend

### Einheitlicher Plattformvertrag

`PlatformSecurityBackend` kapselt sicherheitsrelevante Plattformoperationen.
Das Windows-Backend ist für lokale NaC-Entwicklung und -Steuerung verbindlich.
Ein Linux-Backend darf als optionale Kompatibilitätsreferenz bestehen, aber kein
lokaler Produktpfad darf davon abhängen.

Die bestehende Windows-Light-Runner-Implementierung wird nicht unverändert
reaktiviert. Ihre Grundideen werden nur übernommen, wenn sie die folgenden
Garantien erfüllen.

### Dateien, Pfade, SID und ACL

Sicherheitsrelevante Dateien werden über Windows-Handles geöffnet. Der
Controller prüft vor ihrer Verwendung:

- absoluten und kanonischen Pfad;
- die relevante Pfadkette auf unerwartete Reparse Points;
- den finalen Pfad über das geöffnete Handle;
- lokale Volume-, Datei- und Größenbindung;
- Eigentümer-SID und DACL;
- fehlende Schreibrechte für nicht zugelassene Principals;
- verweigertes Write- und Delete-Sharing während Messung und Verwendung;
- SHA-256 aus dem bereits geöffneten Handle.

Der repository-externe Identity Resolver wird nicht mehr an POSIX-Modus `0600`,
sondern an die aktuelle Benutzer-SID, eine restriktive Windows-DACL, seinen
kanonischen Pfad und seinen SHA-256 gebunden. Reale Account-Principal-
Zuordnungen gelangen weder in Git noch in öffentliche Logs oder Kommentare.

State, Ledger, Evidence und Journale werden in demselben geschützten Verzeichnis
geschrieben, geflusht und atomar ersetzt beziehungsweise append-only ergänzt.

### Vollständige Toolchain-Attestation

Nicht nur ein `.cmd`-Wrapper wird gemessen. Gebunden wird die gesamte
ausführbare Kette:

```text
Launcher/Wrapper -> Interpreter -> CLI-Einstiegspunkt -> Paket/Modul
```

Dies gilt für Azure CLI, M365 CLI, Python, Node, npm/pnpm, Heft und Bicep.
Fest verdrahtete Linux-Pfade werden aus dem lokalen Vertrag entfernt. Jeder
unerwartete Wrapper, Interpreter, Einstiegspunkt oder Paket-Hash blockiert vor
Netzwerkzugriff.

### Prozessgrenze

Sicherheitskritische Programme starten ohne Shell-Interpolation, mit expliziter
Argumentliste, festem Arbeitsverzeichnis, minimaler Environment-Allowlist und
begrenzter Ausgabe. Der Prozess wird suspendiert erzeugt, mit einem echten
Prozesshandle einem Windows Job Object zugeordnet und erst danach fortgesetzt.
Das Job Object verwendet mindestens `KILL_ON_JOB_CLOSE`. Zulässige
Kindprozesse folgen der attestierten CLI-Kette; unbekannte Prozesse blockieren.

Wo möglich startet der Controller den gebundenen Python- oder Node-Interpreter
direkt mit dem attestierten Einstiegspunkt, statt `.cmd` über eine allgemeine
Shell auszuführen. Tokens und Credentials erscheinen weder in Argumenten noch
in Logs oder Evidence.

Provider-nahe Python-Prozesse laufen unter Windows vor dem ersten Thread-Resume
mit einem Low-Integrity-Token; dadurch kann der vorhandene Auth-Kontext gelesen,
aber ein normal geschützter Credential- oder Konfigurationsspeicher nicht
geschrieben werden. Node-basierte M365-Prozesse verwenden den attestierten
Node-Permission-Modus ohne Dateischreibrecht; Runtime-Dateien bleiben zugleich
über Windows-Handles gebunden. Windows-Loaderfehler werden als redigierte
Fehlercodes zurückgegeben und dürfen keinen modalen Systemdialog öffnen.

### Locking und Crash-Erkennung

Jeder Lauf besitzt:

1. einen per DACL auf die aktuelle Benutzer-SID begrenzten Windows Named Mutex;
2. ein exklusiv geöffnetes, hashgebundenes Lock-/State-Journal.

Das Mutex-Handle bleibt bis zum Laufende erhalten. `WAIT_ABANDONED` ist kein
erfolgreicher normaler Lock-Erwerb, sondern führt zu `RECOVERY_REQUIRED`.
Automatisches Resume oder ein zweiter Live-Lauf ist ausgeschlossen.

### Credential-Grenze

Der Controller nutzt ausschließlich einen bereits vorhandenen
Authentifizierungskontext. Er kopiert, exportiert, hasht oder persistiert keine
Credentials. Login, Device Code, Browserauthentifizierung, Token-Refresh,
Cache-Neuanlage oder Konfigurationsrewrite blockieren die Reconciliation mit
`BLOCKED_AUTHENTICATION_REQUIRED`. Providerzugriff beginnt erst nach dem
vollständigen lokalen Preflight.

### Command-Allowlist

Die Sicherheitsgrenze entsteht aus exakten Command-Schemata, gebundenen
Zielressourcen, Argumenten, Artefakten, Toolchain-Hashes, Windows-ACLs und
Readbacks. Unbekannte Flags, andere Tenants, Subscriptions, Sites oder
Ressourcen werden vor Prozessstart abgewiesen. Eine lokale Linux-Sandbox ist
nicht Bestandteil des Designs.

## Phasenweise Abschlusskette

```text
WINDOWS_IMPLEMENTATION_READY
  -> ISSUE_746_OWNER_SOLO_APPROVAL
  -> WINDOWS_PREFLIGHT_READY
  -> READ_ONLY_RECONCILIATION
  -> TWO_IDENTICAL_NOT_APPLIED_SNAPSHOTS
  -> ISSUE_739_QUARANTINE_RELEASE
  -> ISSUE_632_OFFLINE_PACKAGE
  -> ISSUE_632_LIVE_APPROVAL
  -> ONE_WINDOWS_CONTROLLED_LIVE_RUN
  -> READ_ONLY_POST_VERIFY
```

Jede Phase autorisiert nur die nächste. Ein blockierter Lauf autorisiert keinen
Retry.

### Phase 0: Windows-Implementierung

Zunächst werden ausschließlich Repository-Artefakte geändert, lokal unter
Windows validiert, committed, zu PR #747 gepusht und durch verpflichtende
Windows-CI geprüft. Es gibt keinen Provider-, Tenant-, Credential- oder
Live-Zugriff. Nach erfolgreicher CI werden Commit, Tree, Verification Contract,
Windows-Backend, Toolchain, Resolver und Operator-Principal gebunden.

### Phase 1: neue Issue-#746-Freigabe

Eine neue `OWNER_SOLO_APPROVAL` bindet den finalen Implementierungsstand, weil
frühere Freigaben auf andere Commits zeigen. Die Freigabe erlaubt nur den
Windows-Preflight und die eng allowlistete read-only Reconciliation. Sie ist
weder die #739-Quarantänefreigabe noch die #632-Live-Freigabe.

### Phase 2: lokaler Windows-Preflight

Vor Credential-, Netzwerk- oder Providerzugriff prüft der Preflight Commit,
Tree, #739-State, Evidence, Ledger, drei Journale, Prepared Manifest,
Function- und SPFx-Pakete, Toolchain, SID, ACL, Reparse Points, Ziel- und
Approval-Bindung sowie konkurrierende Läufe. Bei Drift bleiben Netzwerk-,
Provider-, Tenant- und Credentialzähler null.

### Phase 3: read-only Provider-Reconciliation

Mit dem bereits vorhandenen Authentifizierungskontext wird ausschließlich die
eng gebundene Schritt-7-Frage geprüft. Exakt zwei allowlistete, redigierte und
kanonische Provider-Snapshots werden erzeugt. Nur zwei identische Snapshots mit
`FUNCTION_DEPLOYMENT_NOT_APPLIED` und Null-Schreibzählern öffnen das #739-Gate.
Redirect, Authentifizierungsbedarf, unbekannte Felder, Drift, ein beobachtetes
Deployment oder nicht redigierbare Ausgabe blockieren.

### Phase 4: getrennte #739-Quarantänefreigabe

Ein neuer, exakt gebundener Issue-#739-Kommentar autorisiert ausschließlich das
deterministische append-only Anhängen eines `RELEASED`-Datensatzes an die drei
lokalen Journale. Der historische Lauf bleibt `FAILED_PARTIAL`; State, Evidence
und Ledger werden nicht umgeschrieben. Ein partieller Append darf nur mit
derselben unveränderten Freigabe idempotent abgeschlossen werden.

### Phase 5: neues #632-Offline-Paket

Nach der Journalfreigabe wird unter Windows ein neues Aktivierungspaket für
alle zwölf bestehenden Schritte erzeugt. Es bindet Commit, Tree, Windows-
Backend, Toolchain, Function-, SPFx- und Bicep-Artefakte, Zielressourcen und
Readbacks. Die Paketerzeugung ist offline.

### Phase 6: eigenständige #632-Live-Freigabe

Ein neuer Issue-#632-Kommentar bindet das vollständige Paket und autorisiert
genau einen Live-Lauf. #746- und #739-Kommentare sind nicht wiederverwendbar.
Jede Änderung an Code, Vertrag, Toolchain oder Paket macht die Freigabe
ungültig.

### Phase 7: genau ein Windows-gesteuerter Live-Lauf

Der Lauf startet auf dem Windows-Arbeitsplatz. Azure darf das Function-Paket
intern als Linux-Runtime materialisieren. Der Controller wiederholt den
Prewrite-Check, führt ausschließlich die zwölf gebundenen Schritte aus, prüft
jeden Readback und stoppt beim ersten Fehler. Es gibt keinen automatischen
Retry.

### Phase 8: read-only Abschlussverifikation

Nach dem Lauf werden Function, Entra-API, `Matter.Read`, Managed Identity,
`Sites.Selected`, SharePoint-Site-Recht, SPFx-/App-Catalog-Zustand, Teams-BFF-
Verbindung sowie erlaubte und verweigerte synthetische Zugriffe read-only
geprüft. Erst danach darf redigierte Abschluss-Evidence dokumentiert werden.

## Governance und Identität

Provider-Accounts werden über den geschützten externen Resolver auf stabile
Principals abgebildet. Verschiedene Accounts desselben Principals sind eine
Person und erfüllen keine Vier-Augen-Trennung.

Ohne konkret zitierte anwendbare gesetzliche, regulatorische, vertragliche oder
verbindliche Security-Pflicht zu zwei verschiedenen natürlichen Personen gilt
`OWNER_SOLO_APPROVAL`. Ist eine solche Pflicht mit Quelle, Version, Digest und
Scope gebunden und nur ein Principal verfügbar, gilt
`BLOCKED_SINGLE_PRINCIPAL`. Eine Rollenbezeichnung oder `four_eyes` allein ist
kein Quellenbeleg.

## Akzeptanzkriterien

- **AC-746-01 – DE/EN-Parität:** Deutsche und englische Spec beschreiben
  identisch Plattformgrenze, Ausgangszustand, Security Backend, Phasen, Stop
  Conditions und getrennte Gates.
- **AC-746-02 – Provenienztrennung:** #620, #632, #739, #743, #744 und #746
  bleiben getrennt; alte Evidence und Kommentare sind weder aktueller State
  noch neue Freigabe.
- **AC-746-03 – Windows-Preflight:** Alle lokalen Bindungen, SID-/ACL- und
  Reparse-Point-Prüfungen laufen auf Windows vor jedem Netzwerkzugriff. Jede
  absichtliche Drift liefert `BLOCKED` bei Null-Seiteneffektzählern.
- **AC-746-04 – Doppelte read-only Reconciliation:** Genau zwei gebundene,
  redigierte Snapshots und ausschließlich
  `FUNCTION_DEPLOYMENT_NOT_APPLIED` öffnen das separate #739-Gate; Provider-,
  Tenant- und Credential-Schreibzähler bleiben null.
- **AC-746-05 – Vollständiges Windows-Sicherheitsbackend:** Live, Recovery und
  Reconciliation sind auf Windows nur bei nachgewiesener Handle-, ACL-,
  Reparse-, Toolchain-, Job-Object-, Mutex- und Journal-Sicherheit verfügbar.
  Das bloße Entfernen der bisherigen Plattform-Sperre ist unzulässig.
- **AC-746-06 – Replay- und Crash-Sicherheit:** Die drei Freigaben sind nicht
  austauschbar; falsche Issue-, Principal-, Commit-, Tree-, Contract-, Body-
  oder Artefaktbindung blockiert. Abandoned Mutex und Teil-Appends führen nie
  zu einem automatischen Live-Retry.
- **AC-746-07 – Windows-Validierung und Traceability:** Issue, DE/EN-Spec,
  DE/EN-Plan, AC-IDs, Dateien, positive und negative Tests sowie lokale und
  Remote-Evidence sind verbunden. Verpflichtende CI läuft auf Windows; Linux-
  CI bleibt optional und nicht blockierend.
- **AC-746-08 – Keine vorgezogene Live-Aktion:** Design, Plan und
  Implementierungs-PR führen keine Quarantänefreigabe, Anmeldung, Provider-,
  Tenant-, Credential- oder Live-Aktion aus. #739 und #632 bleiben separate,
  hashgebundene Owner-Gates.

## Validierungsmodell

Der nach Spec-Freigabe zu erstellende Plan führt für jedes AC eine Matrix:

`AC-ID -> Artefakte -> Windows-Positivtest -> Windows-Negativtest -> erwarteter
Status/Fehlercode -> lokaler Befehl -> Remote-Check/Evidence`.

Pflichtnachweise umfassen mindestens:

- Dateihandle-, Datei-ID-, Volume-ID- und Hashbindung;
- SID-, DACL- und Reparse-Point-Negativtests;
- vollständige Launcher-/Interpreter-/Paket-Attestation;
- suspendierten Prozessstart und Job-Object-Zuordnung;
- Mutex-, Abandoned-Mutex- und drei Journal-Crashfenster;
- Replay-Matrix für #746, #739 und #632;
- Credential-, Redaktions- und unbekannte-Felder-Sentinels;
- zwei identische read-only Snapshots bei Null-Schreibzählern;
- Windows-SPFx-Build und Windows-Function-Eingabepaket;
- Windows-native CLI-, Graft- und Strict-Doctor-Prüfung;
- Spec-Traceability, DE/EN-Parität, Governance-Sync, Privacy und Secret Scan.

Vor einem späteren Merge werden vollständige Datei-, Commit- und
`base...head`-Diff geprüft. Mindestens `Privacy and Secrets Guard / secret-scan`,
`Privacy and Secrets Guard / privacy-lint`, `NaC Quality Gate / quality-gate`
und das verpflichtende Windows-Gate müssen erfolgreich sein. PR #747 bleibt
bis zu einer gesonderten Merge-Freigabe Draft.

## Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
| --- | --- |
| Austausch zwischen Hashprüfung und Prozessstart | Handle offen halten, Write/Delete Sharing verweigern, Datei-/Volume-ID binden und Prozessimage nachprüfen |
| Manipulierter Wrapper oder Interpreter | vollständige Launcher-/Interpreter-/Paket-Attestation |
| Reparse-Point- oder Junction-Umleitung | relevante Pfadkette und finalen Handle-Pfad prüfen |
| Zu breite ACL | vor Credential-, Netzwerk- und Providerzugriff blockieren |
| Unerwartete CLI-Kindprozesse | attestierte Prozessstruktur und Windows Job Object |
| Credential-Cache-Mutation | Adaptergrenze und Vorher-/Nachher-Prüfung; bei nicht beweisbarer Schreibfreiheit blockieren |
| Crash mit verwaistem Mutex | `RECOVERY_REQUIRED`, kein automatischer Lauf |
| Windows-/Azure-Linux-Paketdrift | deterministisches Windows-Eingabepaket und gebundener Azure Remote Build |
| Linux-CI wird versehentlich Pflicht | maschinenlesbar `required_gate: false` und `may_block_windows_delivery: false` |

## Stop Conditions

Die Sequenz stoppt fail-closed bei unsauberem Arbeitsbaum, fehlender oder
abweichender Bindung, State-/Ledger-/Journalfehler, unzulässiger SID oder ACL,
Reparse Point, Toolchain-Drift, konkurrierendem oder verlassenem Lock,
Netzwerksperre, Authentifizierungsanforderung, Credentialmutation, unbekannter
Providerantwort, Snapshot-Drift, beobachtetem oder nicht sicher ausgeschlossenem
Deployment, nicht redigierbarer Ausgabe oder fehlgeschlagenem Pflicht-Gate.

Ein blockierter Lauf autorisiert keinen Retry.

## Nicht-Ziele

- keine Migration der Azure Function von Linux auf Windows;
- keine Abschaffung des Azure OneDeploy Remote Build;
- kein WSL, Docker, SBX, lokale Linux-VM oder separater POSIX-Runner;
- kein allgemeines lokales Sandboxprodukt;
- keine allgemeine Tenant-Administration;
- keine neue oder breitere Azure-, Entra-, Graph-, SharePoint-, Teams- oder
  App-Catalog-Berechtigung;
- keine Änderung der zwölf fachlichen Aktivierungsschritte;
- keine UI-Umgehung einer legitimen Zugriffsverweigerung;
- kein Umschreiben historischer Evidence;
- kein automatisches Resume, Rollback, Delete, Unlock oder Retry;
- kein Merge oder Force-Push von PR #747;
- keine Speicherung realer Identitätszuordnungen, Tokens, Credentials,
  personenbezogener Tenantdaten oder Mandatsdaten im Repository oder in
  öffentlichen Logs.

## Review Gate

Die vier Designabschnitte Plattformgrenze, Windows-Sicherheitsbackend,
Abschlusskette sowie Scope und Akzeptanzkriterien wurden im führenden Task vom
Owner freigegeben. Diese schriftliche DE/EN-Spec muss dennoch separat geprüft
und freigegeben werden, bevor der Implementierungsplan überarbeitet oder Code
geändert wird.

Die Spec-Freigabe ersetzt weder die später final-head-gebundene
Issue-#746-`OWNER_SOLO_APPROVAL` noch die Issue-#739-Quarantänefreigabe oder die
Issue-#632-Live-Freigabe. Bis zur Implementierung des vollständigen Windows-
Backends bleibt die bestehende Laufzeitsperre fail-closed aktiv.
