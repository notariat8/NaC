# Windows-nativer Abschluss der partiellen M365-BFF-Aktivierung – Implementierungsplan

Status: Spec, Plan und P0-/P1-/P2-Reparatur vom Owner freigegeben; `plan -> review -> fix` und `implement -> review -> fix` abgeschlossen; Umsetzung im geschützten Draft-PR; operative Ausführung und Merge separat gesperrt

Datum: 19. September 2026

Spec: [Sicherer Windows-Abschluss der partiellen M365-BFF-Aktivierung](../specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md)

Führendes Issue: [#746](https://github.com/notariat8/NaC/issues/746)

Draft-PR: [#747](https://github.com/notariat8/NaC/pull/747)

Delivery Mode: Protected PR

Risk Gate: Human Approval

## Ergebnis und Grenze

Die Umsetzung liefert einen vollständig Windows-nativen lokalen Entwicklungs-,
Build-, Test-, Paketierungs-, Reconciliation-, Recovery- und
Aktivierungssteuerungspfad. Linux bleibt ausschließlich als verwaltete Azure-
Function-Runtime, Azure-Remote-Build-Umgebung und optionaler nicht blockierender
Kompatibilitätstest zulässig.

Dieser Plan autorisiert nur Repository-Änderungen, lokale Windows-Prüfungen,
synthetische Tests, einen separaten lokalen Commit und nach späterer
ausdrücklicher Freigabe einen Push zu PR #747. Er autorisiert jetzt nicht:

- Anmeldung oder Credentialänderung;
- Tenant- oder Providerzugriff;
- Issue-#739-Quarantänefreigabe;
- Erzeugung einer operativ gültigen Issue-#632-Live-Freigabe;
- Live-Aktivierung, Retry, Rollback, Delete oder Unlock;
- Merge oder Force-Push.

Windows-Live-Aktivierung und Windows-Recovery bleiben unabhängig von der
Verfügbarkeit des Windows-Sicherheitsbackends fail-closed gesperrt. Das Backend
dient in Issue #746 ausschließlich der separat autorisierten Read-only-
Reconciliation und den lokalen Sicherheitsprüfungen.

## Implementierungsprinzipien

1. **Test-first:** Jede neue Windows-Fähigkeit beginnt mit einem positiven und
   mindestens einem fail-closed Negativtest.
2. **Keine Abschwächung:** Linux-Primitiven werden nicht einfach entfernt,
   sondern durch überprüfbare Windows-Garantien ersetzt.
3. **Backend-Injektion:** Runner und Reconciler greifen nicht direkt auf
   `fcntl`, `/proc`, Unix-UIDs oder rohe Windows-APIs zu, sondern auf einen
   schmalen Plattformvertrag.
4. **Windows ist autoritativ:** Alle verpflichtenden lokalen und Remote-Gates
   müssen auf Windows funktionieren. Linux-CI ist optional.
5. **Keine Provideraktion während der Implementierung:** Echte Adapter werden
   nur mit synthetischen Ports, Fake-Prozessen und Sentinel-Daten geprüft.
6. **Bestehende Provenienz erhalten:** Historische #739-State-, Ledger- und
   Journal-Artefakte werden weder umgeschrieben noch rekonstruiert.
7. **Ein Gate pro Wirkung:** #746-Reconciliation, #739-Journalfreigabe und
   #632-Live-Lauf bleiben nicht austauschbar.
8. **Verlust ist terminal:** Sind die exakt gebundenen #739-Originalartefakte
   vollständig verloren, endet der lokale Pfad mit
   `FUNCTION_DEPLOYMENT_PROVENANCE_LOST`; kein Providerabgleich und keine
   Freigabephase darf folgen.

## Änderungsflächen

| Fläche | Geplante Artefakte | Zweck |
| --- | --- | --- |
| Plattformvertrag | `src/nac_bff/azure_activation_contract.py`, neu `src/nac_bff/activation_security_backend.py` | Backend-Protokoll, Fähigkeiten, stabile Fehlercodes und Auswahl definieren |
| Windows-Backend | neu `src/nac_bff/activation_security_windows.py` | Handle-, SID-/ACL-, Reparse-, Prozess-, Job-Object-, Mutex- und Flush-Semantik |
| Optionales Linux-Backend | neu `src/nac_bff/activation_security_linux.py` | vorhandene Linux-Semantik isolieren, ohne lokale Abhängigkeit zu erzeugen |
| Runner/Recovery | `src/nac_bff/azure_activation_runner.py`, `src/nac_bff/azure_activation_facade.py` | Datei-, Lock-, State-, Evidence- und Recovery-Operationen über Backend führen |
| Toolchain/Prozesse | `src/nac_bff/azure_activation_attestations.py`, `src/nac_bff/azure_live_commands.py`, `src/nac_bff/azure_live_commands_win.py`, `src/nac_m365_graph/sealed_toolchain.py` | vollständige Windows-Launcher-/Interpreter-/Paketbindung und sicherer Prozessstart |
| Reconciliation | bestehende Function-Deployment- und Interruption-Reconciliation-Module, neu `src/nac_bff/issue746_reconciliation_gate.py` | Windows-Preflight, produktives #746-Gate, doppelte read-only Snapshots und Null-Schreibgrenze |
| CLI/Komposition | `src/nac_cli/cli.py`, `src/nac_m365_graph/mvp_test_environment_deploy.py`, `src/nac_bff/azure_activation_composition.py` | #746-Autorisierung vor Factory und erneut vor jedem Provider-Read erzwingen; Live und Recovery gesperrt halten |
| Resolver/Governance | `src/nac_identity/governance_registry.py`, Issue-#746-Validator und Verification Contract | gemeinsame Principal-Logik, SID-/DACL- statt POSIX-`0600`-Bindung und keine Zweitkonto-Trennung |
| Verträge | `workflows/contracts/m365-azure-bff-live-activation.contract.json`, beide M365-Verification-Contracts | Windows-Ziel, optionale Azure-Linux-Runtime, Gate- und Evidence-Matrix |
| Tests | neue Backendtests sowie bestehende #632/#739/#744/#746-Tests | positive Windows-Pfade, Negativmatrix, Replay- und Crashfenster |
| Entwicklerwerkzeuge | `scripts/startup_check.py`, Mindestvoraussetzungen, SBOM | funktionierendes Windows-Python `>=3.11` und Windows-Graft als Pflicht nachweisen |
| Dokumentation | DE/EN CLI, Mindestvoraussetzungen, #632/#744/#746 Spec und Plan | Linux-only-Zielannahme entfernen und Migrationsstatus erklären |
| CI | `.github/workflows/windows-portability.yml`, Quality-Gate-Konfiguration | verpflichtendes Windows-Gate; Linux-Kompatibilität optional und nicht allein blockierend |
| Traceability | `agent-context/index.json`, Spec-Manifeste, AI-SBOM | Issue, ACs, Dateien, Tests und Remote-Evidence verbinden |

Neue Dateinamen sind Planvorgaben. Ergibt die Implementierung eine klarere
Aufteilung ohne Scopeänderung, muss der Plan vor dem Commit synchronisiert
werden; parallele Doppelimplementierungen sind nicht zulässig.

## Verbindliche Phasen- und Gate-Tabelle

| Phase | Eingabe | Zulässige Aktion | Erfolg | Blockiert bei | Mutation |
| --- | --- | --- | --- | --- | --- |
| 0 Implementierung | freigegebene Spec, Plan und Owner-Reparaturauftrag für den vollständigen `main...HEAD`-Diff | Code, Tests, Verträge, Docs, lokale Windows-Validierung | `WINDOWS_IMPLEMENTATION_READY` | rotem Pflicht-Gate | nur Repository |
| 1 PR-Evidence | sauberer Implementierungscommit | Push nach gesonderter Freigabe, Windows-CI, vollständige PR-Diff | `WINDOWS_REMOTE_CI_READY` | fehlendem/rotem Check oder Scope-Drift | GitHub-Branch/PR |
| 2 #746-Gate | finaler Commit/Tree, Contract-, Backend-, Toolchain-, Resolver- und Principal-Bindung | neue `OWNER_SOLO_APPROVAL` | `WINDOWS_RECONCILIATION_APPROVED` | Binding- oder Governancefehler | GitHub-Kommentar |
| 3a Windows-Preflight | unveränderte #739-Artefakte | ausschließlich lokale Bindungen lesen | `WINDOWS_PREFLIGHT_READY` | Drift, ACL/Reparse/Lock/Toolchainfehler | keine |
| 3b terminaler Provenienzverlust | DACL-/SID-geschützter lokaler Owner-Datensatz, geschützter Resolver, stabiler Principal, exakte Issue-/Aktions-/Run-/Hash-/Correlation-/Pfad-/Inventarbindung und vollständige Abwesenheit am Sollort | ausschließlich lokale Existenz- und Bindungsprüfung | `status=BLOCKED`, `reason_code=FUNCTION_DEPLOYMENT_PROVENANCE_LOST`, `terminal=true`, `retry_allowed=false`, `next_phase=null`, Exit `2` | jeder Abweichung, Teilbestand, unprüfbarer Ablage oder vorhandenen Artefakten an den gebundenen Sollorten | keine; geschlossen enumerierte operative Zähler `0` |
| 4 Provider-Inspection | erfolgreicher Preflight, bestehender nicht schreibender Auth-Kontext | genau zwei gebundene read-only Snapshots | `FUNCTION_DEPLOYMENT_NOT_APPLIED` | Authbedarf, Drift, unbekannter Ausgabe, Deployment | keine |
| 5 #739-Gate | identische Snapshot-Hashes und neue exakte Freigabe | drei deterministische Journal-Appends | `LOCK_JOURNALS_RELEASED` | Replay, Tail-, Hash- oder Reihenfolgenfehler | nur drei lokale Appends |
| 6 #632-Paket | sauberer gebundener Stand nach Phase 5 | Windows-native Offline-Paketierung | `ISSUE_632_PACKAGE_READY` | Build-/Bindingfehler | lokale Offline-Artefakte |
| 7 #632-Gate | vollständiges Paket und neue exakte Freigabe | genau einen Live-Lauf autorisieren | `LIVE_RUN_APPROVED` | jeder Drift | GitHub-Kommentar |
| 8 zukünftiger Live-Pfad | gültige #632-Freigabe und eigene freigegebene Spezifikation | unter Issue #746 keine Windows-Ausführung; Windows blockiert vor externem Zugriff | `BLOCKED_ON_WINDOWS` | immer im #746-Windows-Pfad | keine |
| 9 Post-Verify | terminaler Live-Status | read-only Zielzustand und Zugriffe prüfen | `PASSED` oder gebundener Fehler | unklarem Readback | redigierte Evidence |

Im aktuellen Implementierungsturn werden nur Phase 0 und lokale synthetische
Prüfungen ausgeführt. Jede spätere Phase besitzt ein eigenes Gate.
Phase 3b ist kein Ersatz-Gate für Phase 3a, sondern ein terminaler Endzustand;
sie kann keine Phase 4 bis 9 öffnen.

## Zielvertrag des Windows-Sicherheitsbackends

Das Backend-Protokoll stellt mindestens folgende Fähigkeiten bereit:

```text
capabilities()
current_operator_binding()
inspect_private_path(path, purpose)
open_bound_read(path, expected_binding)
atomic_write(path, bytes)
append_and_flush(path, bytes)
acquire_run_lock(target_binding)
launch_attested_process(spec)
inspect_process_image(process_handle)
```

Die konkreten Rückgaben sind typisierte, redigierbare Datensätze und enthalten
keine Credentials oder Klartextidentitäten. Benötigte Bindungen umfassen:

- kanonischen Pfad-Hash;
- Datei- und Volume-ID;
- Größe und SHA-256;
- Eigentümer-SID-Hash;
- Security-Descriptor-/DACL-Hash;
- Reparse-Point-Status;
- Launcher-, Interpreter-, Einstiegspunkt- und Paket-Hashes;
- bei Prozessen Job-Object- und Image-Bindung;
- bei Locks Mutexname-Hash, Journal-Hash und `normal`/`abandoned`-Status.

## Test-first-Implementierungsfolge

### 1. Verification Contract und zunächst rote Plan-/Contracttests

**Dateien:**

- `workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml`
- `workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml`
- `workflows/contracts/m365-azure-bff-live-activation.contract.json`
- `tests/test_m365_bff_failed_partial_safe_completion.py`
- `tests/test_m365_azure_bff_live_activation_contract.py`
- `scripts/validate_m365_bff_failed_partial_safe_completion.py`

**Zuerst rot:**

- Windows ist nicht autoritative lokale Plattform;
- `posix_local` oder `ubuntu_remote_ci` ist verpflichtendes Gate;
- Linux-Pfad ist für lokalen Build oder Live-Controller erforderlich;
- Windows-Reconciliation bleibt pauschal blockiert;
- Resolver verlangt POSIX-Modus `0600`;
- #746-, #739- oder #632-Gates sind austauschbar.

**Dann grün:**

- Schema-Version erhöhen;
- `windows_native` und `windows_remote_ci` als verpflichtende Plattformen
  materialisieren;
- `azure_linux_runtime_optional` als Zielkompatibilität, nicht als lokales Gate;
- alle acht ACs und Phasen 0 bis 9 maschinenlesbar verbinden;
- stabile Windows-Fehlercodes und Null-Seiteneffektzähler festlegen.

### 2. Backend-Protokoll und Linux-Isolation

**Dateien:**

- neu `src/nac_bff/activation_security_backend.py`
- neu `src/nac_bff/activation_security_linux.py`
- `src/nac_bff/azure_activation_contract.py`
- neue `tests/test_activation_security_backend.py`

**Zuerst rot:** Backendauswahl darf nicht durch CLI-Flag, Environment oder
Konfiguration vortäuschbar sein; unvollständige Fähigkeiten müssen mit
`PLATFORM_SECURITY_BACKEND_UNAVAILABLE` blockieren.

**Dann grün:** Bestehende Linux-Prüfungen in das optionale Linux-Backend
verschieben; vertrauenswürdige Laufzeiteigenschaften wählen das Backend;
Facade, Runner und Adapter erhalten es explizit oder über eine kleine Factory.

### 3. Windows-Datei-, Pfad-, SID- und ACL-Primitiven

**Dateien:**

- neu `src/nac_bff/activation_security_windows.py`
- neue `tests/test_activation_security_windows.py`

**Windows-APIs:** `CreateFileW`, `GetFinalPathNameByHandleW`,
`GetFileInformationByHandleEx`, `GetSecurityInfo`, `GetNamedSecurityInfoW`,
`FlushFileBuffers`, `ReplaceFileW` beziehungsweise `MoveFileExW`.

**Zuerst rot:** relative Pfade, Junctions/Reparse Points, unerwartete
Eigentümer, breite schreibende ACEs, Remote-/Nicht-NTFS-Volumes, File-ID-Wechsel,
Write/Delete-Sharing und Hashdrift.

**Dann grün:** Handle-basierte Messung und typisierte `BoundFileSnapshot`-
Evidence. Kein PowerShell-`Get-Acl`, kein `icacls`-Parsing und keine zusätzliche
`pywin32`-Abhängigkeit; Windows-APIs werden eng über `ctypes` gekapselt.

### 4. Windows-Locking, atomare Writes und Crashfenster

**Dateien:**

- Windows-Backend;
- `src/nac_bff/azure_activation_runner.py`;
- Runner-, Recovery- und Journaltests.

**Zuerst rot:** zweiter Prozess, verlorenes Mutex-Handle, `WAIT_ABANDONED`,
Crash vor erstem Append, nach erstem/zweitem Append und nach drittem Append vor
Rückgabe.

**Dann grün:** per DACL geschützter Named Mutex plus exklusives Journalhandle;
`WAIT_ABANDONED -> RECOVERY_REQUIRED`; `WriteFile`/`FlushFileBuffers`;
atomarer Replace; idempotente Journalfortsetzung nur mit identischer #739-
Freigabe. Der Runner enthält danach keine direkte `fcntl`-Annahme mehr.

### 5. Attestierter Windows-Prozessstart

**Dateien:**

- Windows-Backend;
- `src/nac_bff/azure_live_commands_win.py`;
- `src/nac_bff/azure_live_commands.py`;
- neue Prozess- und Toolchaintests.

**Zuerst rot:** Prozess startet vor Job-Zuordnung, PID wird als Handle benutzt,
unbekannter Kindprozess, Shell-Interpolation, Environment-Leak, Imagewechsel,
Timeout, übergroße Ausgabe oder nicht allowlisteter Exitcode.

**Dann grün:** `CreateProcessW` mit `CREATE_SUSPENDED`, echtes Prozess- und
Threadhandle, `AssignProcessToJobObject`, `KILL_ON_JOB_CLOSE`, anschließendes
`ResumeThread`, attestierte Kindprozessstruktur, feste Argumentliste, feste
Arbeitsdirectory, minimale Environment-Allowlist und redigierte bounded output.
Der Python-Providerpfad setzt vor `ResumeThread` Low Integrity; der
Node-/M365-Pfad startet mit attestiertem Node-Permission-Modus ohne
Dateischreibrecht. Vererbte Windows-Fehlerdialoge sind deaktiviert, damit jeder
Loaderfehler ausschließlich fail-closed als redigierter Code endet.

Der alte Windows-Light-Runner-Code wird nicht parallel behalten. Verwertbare
Teile werden übernommen, der fehlerhafte Stub anschließend entfernt oder zum
Kompatibilitätsexport auf das neue Backend reduziert.

### 6. Vollständige Windows-Toolchain-Attestation

**Dateien:**

- `src/nac_bff/azure_activation_attestations.py`;
- `src/nac_m365_graph/sealed_toolchain.py`;
- `src/nac_bff/azure_live_commands.py`;
- Attestations- und Negativtests.

Für Azure CLI, M365 CLI, Python, Node, npm/pnpm, Heft und Bicep werden Launcher,
Interpreter, Einstiegspunkt und Paketbasis gebunden. `.cmd` ist allein nie
ausreichend. Wo möglich startet der Controller Interpreter und Einstiegspunkt
direkt, ohne allgemeine Shell.

Fest verdrahtete `/usr/bin`-, `/tmp`- und `linux-x64`-Pfade verschwinden aus
dem verpflichtenden lokalen Vertrag. Linux-Artefakte dürfen nur zum Azure-
Zielpaket oder optionalen Kompatibilitätstest gehören.

### 7. Runner, Facade, CLI und zwölf Aktivierungsschritte integrieren

**Dateien:**

- `src/nac_bff/azure_activation_runner.py`;
- `src/nac_bff/azure_activation_facade.py`;
- `src/nac_bff/azure_activation_composition.py`;
- `src/nac_cli/cli.py`;
- `src/nac_m365_graph/mvp_test_environment_deploy.py`;
- vorhandene Runner-, CLI- und Kompositionstests.

Offline-Befehle bleiben unverändert importierbar. Ausschließlich die gebundene
read-only Interruption- und Function-Deployment-Reconciliation nutzt das
Windows-Backend für Provider-Lesezugriffe. Live und Recovery bleiben unter #746
auch bei vollständigen Backend-Fähigkeiten gesperrt. Alle zwölf Schritte, ihre
Reihenfolge, Zielressourcen und Readbacks bleiben unverändert.

### 8. Credential-schreibfreie Reconciliation und zwei Snapshots

**Dateien:** `src/nac_bff/issue746_reconciliation_gate.py`, bestehende
Reconciliation-Module, CLI/Komposition, Verification Contract, Adapter- und
Sentineltests.

Der echte Adapter erhält keinen impliziten Login- oder Refreshpfad. Vor dem
ersten Provider-Read müssen Resolver, Operator-Principal, finaler HEAD/Tree, PR
#747, alle Pflichtchecks und der unveränderte #746-`OWNER_SOLO_APPROVAL`-
Kommentar dieselbe Autorisierung bilden. CLI und beide Port-Factories verlangen
sie zwingend; der Runtime-Verifier prüft ihren kanonischen Digest vor jedem
Provider-Subprozess erneut. Kann der verwendete Kanal Credential- oder
Cache-Schreibfreiheit nicht technisch garantieren, blockiert er vor dem
Providerzugriff.

Synthetische Tests versuchen Login, Device Code, Refresh, Cache Create und
Config Rewrite und erwarten Blockierung ohne Credentialmutation. Zwei
Providerantworten werden sofort auf dieselbe allowlistete kanonische Projektion
reduziert. Nur identische Hashes mit
`FUNCTION_DEPLOYMENT_NOT_APPLIED` öffnen das separate #739-Gate.

**Terminaler Verlustpfad:** Vor dem produktiven #746-Gate und vor der Port-
Factory liest ein eigener lokaler CLI-Pfad einen repository-externen, per
Windows-SID/DACL und SHA-256 gebundenen Owner-Bestätigungsdatensatz sowie den
bereits geschützten Identitätsresolver. Der Resolver muss das bestätigende
Konto auf einen aktiven `OWNER_SOLO_APPROVAL`-Principal mit Prozessrolle und
Qualifikation abbilden. Der Datensatz bindet den verwendeten Resolver-Hash und
ist selbst der einzige Owner-Bestätigungsnachweis dieses terminalen Pfads; alte
#632-/#739- oder #746-Kommentare sind dafür weder erforderlich noch ausreichend.
Der Datensatz ist die vertrauenswürdige Sollquelle und
bindet Aktion `CONFIRM_FUNCTION_DEPLOYMENT_PROVENANCE_LOST`, Issue `739`, Run-ID
`nac-bff-live-20260908-issue739-v4`, Activation Hash, Correlation ID,
kanonischen Laufpfad, die ursprünglichen Target-/Legacy-Lock-Binding-Hashes,
vollständiges erwartetes Artefaktinventar, Resolver-, Operator-Account- und
Principal-Hash sowie den exakten Terminalvertrag. Die
normalen Laufargumente sind nur ein zweiter Vergleichskanal und dürfen Sollwerte
oder Sollpfad nicht bestimmen.

Der Pfad prüft ausschließlich lokal: alle Datensatz-/Resolver-/Principal- und
Laufbindungen; die Abwesenheit des kanonischen Hash-Verzeichnisses; sowie die
Abwesenheit der drei aus den im Bestätigungsdatensatz gebundenen ursprünglichen
Target-/Legacy-Lock-Hashes gebildeten Lock-Journale. Er baut weder einen
aktuellen Aktivierungsplan noch ein Function-Paket und startet keinen
Unterprozess. Nur der vollständige Sollbestand gilt als gebundenes Inventar;
Teilbestand, unprüfbare Ablage an den gebundenen Sollorten und jede Abweichung liefern
einen engen Binding-/State-Fehler. Positive und negative Tests beweisen das
exakte Ergebnis `BLOCKED` plus Reason, Terminal-/Retry-/Next-Phase-Felder und
Exit `2`. Sentinel-Tests verbieten jeden GitHub-, DNS-/HTTP-/Netzwerk-,
Subprozess-, Credential-, Provider-, Tenant-, Live-, Recovery-, Retry-,
Paketierungs-, #739-Release-, #632-Autorisierungs-, Datei- und Journalpfad.
Der Contract enumeriert diese Zähler geschlossen; jeder bleibt `0`.

### 9. Windows-Resolver und Approval-Bindings

**Dateien:** `src/nac_identity/governance_registry.py`, produktives #746-Gate,
Issue-#746-Validator, Verification Contract, Resolver-Fixtures und Tests.

Der geschützte externe Resolver wird an kanonischen Pfad, Datei-/Volume-ID,
SHA-256, Benutzer-SID und DACL gebunden. Öffentliche Evidence enthält nur
zweckgetrennte Hashes. Die drei bekannten Accounts müssen weiterhin demselben
Principal zugeordnet sein und können keine gegenseitige Freigabe bilden.
Der Resolver bindet außerdem absoluten Pfad und erwarteten SHA-256 des Git-
Executables. Das #746-Gate verwendet ausschließlich dieses Git mit bereinigter
Umgebung; eine Suche über den ambienten `PATH` ist unzulässig.

Replay-Tests decken falsches Issue, falsche Author-Association, anderen
Principal, veränderten Body/Hash, Commit, Tree, Contract, Toolchain, Resolver,
Snapshot und Paket ab.

### 10. Windows-Paketierung für Function und SPFx

**Dateien:** Paketierungs-/Buildadapter, SPFx-Konfiguration, Verträge und Tests.

- SPFx/Heft baut vollständig unter Windows aus dem exakten Lockfile.
- Das Function-Eingabepaket entsteht deterministisch unter Windows.
- Linux-native Function-Abhängigkeiten werden ausschließlich durch den
  gebundenen Azure OneDeploy Remote Build erzeugt.
- Lokaler Build und Hash dürfen nicht von WSL, Docker oder Linux abhängen.
- Wiederholte Builds mit denselben Eingaben müssen identische gebundene
  Eingabeartefakte erzeugen oder dokumentierte deterministische Normalisierung
  verwenden.

### 11. Windows-Entwicklerwerkzeuge und CI

**Dateien:**

- `scripts/startup_check.py`;
- DE/EN-Mindestvoraussetzungen und CLI-Doku;
- `.github/workflows/windows-portability.yml`;
- Quality-Gate- und SBOM-Artefakte.

Der Windows-Portability-Job und der lokale Aktivierungsvalidator weisen einen
nativen Python-Interpreter `>=3.11`, Node `>=24`,
die gepinnte Graft-CLI und die benötigten Buildwerkzeuge nach. Ein defekter
Launcher, der seine Standardbibliothek oder Paketabhängigkeiten nicht auflösen
kann, gilt als nicht verfügbar. Es gibt keinen Linux-Fallback.

Die frühere lokale Graft-0.18.0-Installation war wegen einer nicht auflösbaren
`dotenv`-Abhängigkeit nicht lauffähig. Die Windows-Installation wurde daraufhin
als ausdrücklich freigegebene Grundvoraussetzung repariert. `graft build` und
`graft check` werden nun lokal und im verpflichtenden Windows-Workflow nativ
ausgeführt; ein Linux-Fallback bleibt ausgeschlossen.

Remote verpflichtend:

- Windows-Backend-Unit- und Integrationstests;
- Windows-CLI- und Validatorläufe;
- Windows-SPFx-Build;
- Windows-Function-Eingabepaket;
- Privacy, Secret Scan, Governance-Sync und Quality Gate.

Linux-CI darf die Azure-Linux-Kompatibilität prüfen, ist aber kein Ersatz und
darf allein die Windows-Lieferung nicht blockieren.

### 11.1 Nachträgliche Strict-Doctor-Windows-Cluster

Der native Volltest hat zusätzliche POSIX-Annahmen in bereits vorhandenen
Sicherheits- und Persistenzpfaden sichtbar gemacht. Sie gehören zu
AC-746-05 und AC-746-07, weil der Windows-Abschluss nur belastbar ist, wenn
auch seine direkten Verbraucher nativ und fail-closed funktionieren:

- Git-Tree-, Reconciliation-, Activation-, Live- und Performance-Pfade;
- Business-Case-Komposition, Quarantäne, Migration und SQLite-Outbox;
- M365-Node-, Sealed-Toolchain-, SPFx- und MVP-Deployment-Pfade;
- repository-lokale Validatoren, kanonische Pfade und Windows-Testfixtures.

Die Portierung ersetzt POSIX-Dateideskriptor-, UID-, Modus-, Signal-,
pass_fds- und Symlink-Annahmen durch das gebundene Windows-Sicherheitsbackend.
SID-, DACL-, Datei-ID-, Hash-, Hardlink-, Reparse-, Locking-, Toolchain- und
Fail-closed-Prüfungen bleiben vollständig erhalten. Fokussierte Regressionen
werden vor Vollsuite, Graft und Strict Doctor ausgeführt; ein roter Shard darf
nicht durch einen isolierten grünen Test verdeckt werden.

### 12. Dokumentation, Traceability und AI-SBOM

DE/EN synchronisieren:

- #632-Windows-Light-Runner-Spec;
- #744-Windows-Offline-Spec und Plan;
- #746-Spec und Plan;
- CLI und Mindestvoraussetzungen;
- `agent-context/index.json`;
- AI-SBOM und Verification Contracts.

#744 bleibt als historische sichere Zwischenstufe dokumentiert. Die damalige
Windows-Sperre wird erst nach grüner Windows-Implementierung als abgelöst
markiert; historische Commit- oder Issue-Aussagen werden nicht umgeschrieben.

### 13. Implement -> Review -> Fix

Nach der Umsetzung wird die vollständige `origin/main...HEAD`-Diff geprüft,
nicht nur der letzte Commit. Der Review kontrolliert mindestens:

- Scope und Spec-Konformität;
- Windows-API- und Handle-Lebenszyklen;
- ACL-/Reparse-/TOCTOU-Grenzen;
- Credential-, Privacy- und Redaktionsgrenzen;
- zwölf Aktivierungsschritte und Zielbindung;
- Replay-, Crash- und Recoverypfade;
- DE/EN-Parität;
- Windows-CI als verpflichtendes Gate;
- keine realen Identitäts-, Tenant- oder Credentialdaten im Diff.

Jeder Befund wird vor Implementierungsabnahme korrigiert und erneut validiert.

## Maschinenlesbare Validierungszuordnung

```nac-validation-matrix
schema_version: nac.issue-746-validation-plan/v0.2
commands:
  - id: spec_traceability
    platform: windows_native
    command: python scripts/validate_spec_traceability.py
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: language_parity
    platform: windows_native
    command: python scripts/validate_language_parity.py
    acceptance_ids: [AC-746-01]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: issue746_validator
    platform: windows_native
    command: python scripts/validate_m365_bff_failed_partial_safe_completion.py
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: windows_security_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_activation_security*.py
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_bff_regression_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_nac_bff_azure_*.py
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: issue746_gate_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_issue746_reconciliation_gate.py
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_business_case_regression_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_business_case_type_*.py
    acceptance_ids: [AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_m365_regression_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_m365_*.py
    acceptance_ids: [AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_sqlite_outbox_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_sqlite_evidence_staging_outbox.py
    acceptance_ids: [AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: issue746_windows_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_m365_*.py
    acceptance_ids: [AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: activation_validator
    platform: windows_native
    command: python scripts/validate_m365_azure_bff_live_activation.py
    acceptance_ids: [AC-746-03, AC-746-04, AC-746-05, AC-746-06]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: spfx_windows_build
    platform: windows_native
    command: npm --prefix spfx/nac-bpmn-viewer run build
    acceptance_ids: [AC-746-05, AC-746-07]
    remote_evidence: [SPFx BPMN Viewer / spfx-bpmn-viewer]
  - id: graft_build
    platform: windows_native
    command: graft build
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: graft_check
    platform: windows_native
    command: graft check
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: strict_doctor
    platform: windows_native
    command: python scripts/nac.py doctor --profile strict
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: windows_ci_security_tests
    platform: windows_remote_ci
    command: python -m unittest discover -s tests -p test_activation_security*.py
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06, AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_activation_tests
    platform: windows_remote_ci
    command: python -m unittest discover -s tests -p test_m365_*.py
    acceptance_ids: [AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_spfx_build
    platform: windows_remote_ci
    command: npm --prefix spfx/nac-bpmn-viewer run build
    acceptance_ids: [AC-746-05, AC-746-07]
    remote_evidence: [SPFx BPMN Viewer / spfx-bpmn-viewer]
  - id: windows_ci_graft
    platform: windows_remote_ci
    command: graft build
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_graft_check
    platform: windows_remote_ci
    command: graft check
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_doctor
    platform: windows_remote_ci
    command: python scripts/nac.py doctor --profile strict
    acceptance_ids: [AC-746-01, AC-746-03, AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: remote_checks
    platform: post_pr_remote
    command: authenticated GitHub connector check listing for PR 747 at exact HEAD
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [Privacy and Secrets Guard / secret-scan, Privacy and Secrets Guard / privacy-lint, NaC Quality Gate / quality-gate, NaC Windows Portability / windows-offline-cli, SPFx BPMN Viewer / spfx-bpmn-viewer]
  - id: full_diff
    platform: windows_native
    command: git diff origin/main...HEAD
    acceptance_ids: [AC-746-01, AC-746-07, AC-746-08]
    remote_evidence: [complete base...head patch]
```

Der Verification Contract ergänzt jeden Eintrag um `scope` und
`side_effect_class`. `windows_native` ist `local_read_or_synthetic`,
`windows_remote_ci` ist `ci_read_or_synthetic`, `post_pr_remote` ist
`github_read_only`. Kein Validierungsbefehl besitzt Live-Autorität.

## AC-Evidenzmatrix

| AC | Hauptartefakte | Positivnachweis | Negativnachweis | Erwartung |
| --- | --- | --- | --- | --- |
| AC-746-01 | DE/EN-Spec und Plan, Contract | Paritätsvalidator und normalisierte Gate-Tabelle | fehlender/abweichender Abschnitt | `BLOCKED` |
| AC-746-02 | Provenienz- und Approval-Matrix, geschützter lokaler Bestätigungsdatensatz | exakter #739-Run, Principal und vollständiger Sollbestand fehlen an den gebundenen Sollorten | Teilbestand oder unprüfbare Ablage an den Sollorten, falscher Principal, Run, Issue, Aktion, Hash, Correlation ID oder Pfad | `BLOCKED` + `FUNCTION_DEPLOYMENT_PROVENANCE_LOST` nur im exakten bestätigten Verlustfall |
| AC-746-03 | Windows-Backend, Runner, Preflight | vollständige Bindung vor Netzwerk | Drift je Feld, ACL, Reparse, Lock | alle Seitenzähler `0` |
| AC-746-04 | Reconciler und Snapshotprojektion | zwei identische `NOT_APPLIED`-Snapshots | Drift, Redirect, Authbedarf, unbekanntes Feld | Null-Schreibzähler |
| AC-746-05 | Backend, Toolchain, Job Object | vollständige Windows-Capabilities | fehlende Einzelcapability | `PLATFORM_SECURITY_BACKEND_UNAVAILABLE` oder enger Windows-Code |
| AC-746-06 | Gate-, Mutex- und Journaltests | identische Freigabe setzt echten Präfix fort | anderer Hash, Tail, Reihenfolge, abandoned lock | kein Retry |
| AC-746-07 | Traceability, Tooling, CI | Windows-Gates und vollständige Matrix grün | fehlender Windows-Check oder Linux-only-Pflicht | `BLOCKED` |
| AC-746-08 | geschlossenes Zählerschema und PR-Diff | terminales Ergebnis mit `next_phase=null`, Exit `2` und allen Zählern `0` | Aufruf von GitHub, Netzwerk/DNS/HTTP, Subprozess, Credential, Provider, Tenant, Live, Recovery/Retry, Paketierung, #739-Release, #632-Autorisierung, Datei- oder Journal-Write | `BLOCKED`, terminal, keine Folgephase |

## Geplante Commitfolge

1. `test(m365): bind Windows activation security contract`
2. `feat(m365): add Windows activation security backend`
3. `feat(m365): run reconciliation and activation control on Windows`
4. `build(m365): make Windows packaging and CI authoritative`
5. `docs(m365): synchronize Windows issue 746 evidence`

Vor jedem Commit wird die Datei- und Testmenge geprüft. Ein Commit darf mehrere
Schritte zusammenfassen, wenn dadurch keine Reviewgrenze verloren geht; die
Historie wird nicht umgeschrieben oder force-gepusht.

## Plan-Review-Befunde und Fixes

Der lokale `plan -> review -> fix`-Durchlauf hat folgende Befunde korrigiert:

1. **POSIX blieb im alten Plan autoritativ.** Alle verpflichtenden lokalen und
   CI-Nachweise wurden auf Windows umgestellt; Linux ist nur Azure-Ziel oder
   optionaler Kompatibilitätstest.
2. **Der frühere Windows-Light-Runner war kein ausreichendes Sicherheitsbackend.**
   Der Plan verlangt echte Prozesshandles, suspendierten Start, korrekte
   Job-Zuordnung, persistentes Mutex-Handle, Reparse-/ACL-Prüfung und vollständige
   Toolchainbindung.
3. **Runner-Dateioperationen waren nicht als Plattformgrenze erfasst.** Datei-,
   Lock-, Journal-, Atomic-Write- und Recoveryoperationen wurden in den
   Backendvertrag aufgenommen.
4. **Credential-Schreibfreiheit war nur nachträglich messbar.** Der Plan verlangt
   einen Adapter, der Login/Refresh/Cachewrite technisch vor dem Providerzugriff
   blockiert; andernfalls bleibt Reconciliation gesperrt.
5. **Der Resolver war weiterhin an POSIX-`0600` gebunden.** SID-, DACL-,
   Datei-/Volume-ID- und Hashbindung ersetzen den POSIX-Modus.
6. **Windows-Build bedeutete noch nicht Windows-Tooling.** Python-, Graft-,
   SPFx- und Function-Paketierung wurden als Windows-Pflichtgates ergänzt.
7. **GitHub-CLI wurde als Pflichtkanal behandelt.** Remote-Checkauswertung nutzt
   den vorhandenen authentifizierten GitHub-Connector; `gh` bleibt optional und
   löst keine Anmeldung aus. Die produktive #746-Grenze akzeptiert nur zwei
   semantische, fest auf Repository, PR und Kommentar begrenzte Reads eines vom
   vertrauenswürdigen Host injizierten Kanals. Ohne Kanal blockiert sie vor der
   Azure-Factory; ein 401 führt weder zu Login noch zu Retry.
8. **Windows-CI war nur als Prosa, nicht als eigene Plattformzeile vorhanden.**
   Security-, Aktivierungs-, SPFx-, Graft- und Doctor-Läufe besitzen jetzt
   explizite `windows_remote_ci`-Einträge.
9. **Der #746-Validator war auf die alte POSIX-Artefaktliste und lokale
   `gh`-Befehle fest verdrahtet.** Validator, Verification Contract und Tests
   nutzen jetzt dieselbe semantische Kanalschnittstelle und die freigegebene
   Windows-Befehlsmatrix.

Nach diesen Fixes enthält der Plan keine bekannte verpflichtende lokale Linux-
Abhängigkeit und keine vorgezogene operative Autorisierung.

## Implementierungs-Definition-of-Done

Die Implementierung ist erst zur Owner-Abnahme bereit, wenn:

- alle acht ACs durch positive und negative Windows-Tests belegt sind;
- Windows-SPFx-Build und Function-Eingabepaket reproduzierbar bestehen;
- Graft und Strict Doctor nativ unter Windows bestehen;
- keine Linux-/POSIX-Pflicht im lokalen oder verpflichtenden CI-Pfad verbleibt;
- DE/EN-Dokumentation, Verträge, Traceability und AI-SBOM synchron sind;
- vollständige `origin/main...HEAD`-Diff und Commitliste geprüft sind;
- Worktree sauber und Branch ohne History-Rewrite pushbereit ist;
- noch kein Login, Provider-, Tenant-, Credential-, #739- oder #632-Live-
  Zugriff erfolgt ist.

Erst danach wird eine separate Push-Freigabe beziehungsweise die bereits
gültige Delivery-Autorisierung geprüft. Der spätere operative Ablauf benötigt
anschließend neue, final-head-gebundene Gates für #746, #739 und #632.
