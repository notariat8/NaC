# Windows-native Current-State-Diagnose für Teams- und BFF-Zugriff – Implementierungsplan

Status: Repository- und synthetische Umsetzung abgeschlossen; Abnahme, Merge, SPFx-Bereitstellung und realer Providerlauf bleiben jeweils separat freigabepflichtig

Datum: 20. September 2026

Spec: [Windows-native Current-State-Diagnose für Teams- und BFF-Zugriff](../specs/2026-09-20-m365-current-state-access-diagnostic-design.md)

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Draft-PR: [#749](https://github.com/notariat8/NaC/pull/749)

Delivery Mode: Protected PR

Risk Gate: Human Approval

Post-Merge-Hotfix: [Issue #750](https://github.com/notariat8/NaC/issues/750)

## Hotfix-Plan für den Validator-Lebenszyklus

Der Hotfix ändert ausschließlich Validator, Verification Contract, den
bestehenden Test und diese synchronen DE/EN-Spec-/Planabschnitte. Test-first
werden ein gültiger gelieferter Merge, der exakte Hotfix-Scope sowie falscher
Tree, falsche Eltern und fehlende Ancestry geprüft. Danach ersetzt eine
zweistufige Prüfung die pauschale Annahme, dass `origin/main...HEAD` dauerhaft
den Issue-#748-Lieferscope enthält:

1. `pre_merge_scope` bindet Änderungen der Validator-/Contract-Kontrollfläche
   exakt an Basis `13ee6695296d45ce4f3d101ed33e46f9ca6ebb4a` und den sieben Dateien
   umfassenden Hotfix-Scope.
2. `delivered_merge_binding` prüft PR #749, PR-Head, Merge-Commit, Merge-Tree,
   beide geordneten Eltern, ursprünglichen Dateiscope und Ancestry aus dem
   lokalen Git-Objektgraphen.
3. Jede zusätzliche Hotfix-Datei und jede Abweichung von Commit, Tree, Parent,
   Head, Scope oder Ancestry blockiert fail-closed.
4. Der Fix verändert keine Diagnose-, Provider-, Credential-, Teams-, SPFx-
   oder Deploymentfunktion.

## Ergebnis und Grenze

Die Umsetzung liefert einen unabhängigen, Windows-nativen und ausschließlich
lesenden Diagnosepfad für `notary_team_01` und die Teams-App „NaC
Vorgangsansicht“. Er klassifiziert genau eine der vier Ursachen:

- `SPFX_SUBJECT_MISSING`;
- `BFF_REQUEST_NOT_OBSERVED`;
- `BFF_AUTHENTICATION_REJECTED_401`;
- `BFF_AUTHORIZATION_REJECTED_403`.

Der Pfad beginnt auf dem gemergten Stand von PR #747, ersetzt den terminalen
Issue-#739-Lauf nicht und erzeugt keine Issue-#632-Live-Freigabe. Die
Implementierungsphase verwendet ausschließlich synthetische Ports und lokale
Fixtures. Sie autorisiert keine Anmeldung, keinen Credential-, Netzwerk-,
Microsoft-, Tenant- oder Providerzugriff, keinen Retry, kein Deployment, keine
#739-Freigabe, keinen #632-Live-Lauf und keinen Merge.

Nach grüner lokaler und Remote-Validierung wird vor dem einzigen realen
Read-only-Lauf gestoppt. Dieser spätere Lauf benötigt eine neue, exakt an den
finalen Commit, Tree, PR, Checks, Contract, Toolchain, Resolver, Account,
Principal, Datenschutzbeleg und Scope gebundene Owner-Freigabe.

## Verbindliche Architekturentscheidungen

1. **Unabhängiger Pfad:** Neue Module importieren oder lesen keine #739- oder
   #632-Artefakte, Journale, Freigaben, Gates oder Laufzustände.
2. **Pure Klassifikation:** Eine seiteneffektfreie Kernfunktion erhält nur die
   geschlossene, redigierte Snapshotprojektion und gibt genau eine Klasse oder
   einen stabilen Blockiercode zurück.
3. **Autorisierung vor I/O:** Das finale Gate läuft vor der Port-Factory. Die
   unveränderliche Run-Autorisierung wird vor jedem einzelnen Providerread
   erneut geprüft.
4. **Geschlossene Ports:** Nur die sieben in der Spec genannten Ports dürfen
   entstehen. Es gibt keine allgemeine Graph-, Azure-, SharePoint- oder
   Suchschnittstelle.
5. **Windows-Sicherheitsbindung:** Resolver, Datenschutzbeleg,
   Clientbeobachtung, Target-Binding, Approval und Run-Gate werden über das
   vorhandene Windows-Sicherheitsbackend an kanonischen Pfad, SID, DACL,
   Datei-/Volume-ID, Reparse-/Hardlinkzustand, Größe und Hash gebunden.
6. **Einmalverbrauch:** Das geschützte Run-Gate wechselt atomar vor Erzeugung
   der Port-Factory von `unused` auf `consumed`. Replay, Parallelstart und ein
   Crash nach Consume bleiben blockiert.
7. **Zwei echte Erhebungen:** Snapshot 1 und 2 besitzen getrennte
   Acquisition-Envelopes, Sequenzen und Provider-Read-Receipts. Nur ihre
   nach RFC 8785 kanonisierten Entscheidungsprojektionen dürfen byte-identisch
   sein; ein wiederverwendeter Receipt ist kein zweiter Read.
8. **Keine Credential-Inhalte:** Token, Secret-, Header-, Cache- oder
   Credential-Store-Inhalte und deren Hashes werden niemals gelesen. Erlaubt
   sind nur allowlistete, nicht-inhaltliche OS-Metadaten unter aktivem
   Credential-Write-Guard.
9. **Keine KI-Laufzeit:** Der Diagnosepfad ruft kein Modell auf und erzeugt
   keine neue AI-SBOM-Komponente. Die bestehende AI-SBOM dokumentiert synchron
   die negative Entscheidung für diesen deterministischen lokalen Datenfluss.
10. **Expliziter lokaler Client-Receipt:** Das Webpart erzeugt erst nach einem
    terminalen neutralen Fehlerzustand und nur auf Operatoraktion kanonisches
    JSON. Es persistiert weder Subject noch Rohkorrelations-ID. Ein separater
    offline CLI-Schritt validiert und materialisiert den Download exklusiv im
    SID-/DACL-geschützten repository-externen Issue-#748-Inputverzeichnis.

## Festgelegte CLI-Bedienkante

Die Produktoberfläche bleibt in der vorhandenen Hierarchie
`nac m365 teams-sharepoint` und erhält genau drei neue Unterbefehle:

```text
nac m365 teams-sharepoint current-state-access-diagnostic-preflight
nac m365 teams-sharepoint current-state-access-diagnostic-run-read-only
nac m365 teams-sharepoint current-state-access-client-receipt-stage
```

`current-state-access-diagnostic-preflight` führt ausschließlich lokale
Bindungs- und Sicherheitsprüfungen aus und darf keine Provider-Ports erzeugen.
`current-state-access-diagnostic-run-read-only` ist zwar implementier- und
synthetisch testbar, bleibt produktiv bis zur späteren exakt gebundenen
Freigabe gesperrt. `current-state-access-client-receipt-stage` ist rein lokal,
akzeptiert den explizit heruntergeladenen Receipt sowie das geschützte
Inputverzeichnis, validiert eine geschlossene Struktur und erstellt die
autoritative Datei exklusiv ohne Überschreiben. Alle drei Befehle nehmen nur
Pfade zu lokalen Vertragsartefakten entgegen. Reale Tenant-, Account-,
Principal-, Team-,
Kanal-, Tab-, Site-, App-, Function- oder Korrelationswerte sind keine
CLI-Argumente. Es gibt keine Flags für Login, Device Code, Browserauth,
Refresh, Retry, Force, Redirect, Deployment, Recovery oder Write.

## Änderungsflächen

| Fläche | Geplante Artefakte | Zweck |
| --- | --- | --- |
| Verification Contract | `workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml` | geschlossene Bindungen, Phasen, Zähler, Fehlercodes, Port- und AC-Matrix |
| Validator und Quality Gate | `scripts/validate_m365_current_state_access_diagnostic.py`, `scripts/quality_gate.py` | Contract, Dateien, CLI, Tests und Windows-Matrix verpflichtend prüfen |
| Kern und Gate | `src/nac_bff/current_state_access_diagnostic.py`, `src/nac_bff/current_state_access_gate.py` | pure Klassifikation, Post-Merge-/GitHub-/Governance-/Datenschutz-Autorisierung |
| Ports, Adapter und Komposition | `src/nac_bff/current_state_access_ports.py`, `src/nac_bff/current_state_access_adapters.py`, `src/nac_bff/current_state_access_composition.py` | geschlossene Ports, produktive schmale Read-Adapter, Port-Factory hinter Gate, zwei getrennte Erhebungen |
| CLI | `src/nac_cli/cli.py` | lokaler Preflight und separat gesperrter Read-only-Lauf |
| SPFx-Client-Receipt | `NacWorkbenchHost.tsx`, `NacWorkbenchHost.styles.ts`, `NacBpmnViewerWebPart.ts`, `NacBffClient.ts`, neue `ClientObservationReceipt.ts`, VIS-725-05-Harness und zugehörige Tests | flüchtige Korrelationsbindung, geschlossenes Fenster, expliziter lokaler Download ohne PII, kein automatischer Download und visuelle Negativ-Evidence |
| Offline-Materialisierung | `src/nac_bff/current_state_access_client_receipt.py`, `src/nac_cli/cli.py` | strikte Sechs-Feld-Validierung und exklusive Materialisierung im geschützten externen Verzeichnis |
| Tests | `tests/test_m365_current_state_access_client_receipt.py`, `tests/test_m365_current_state_access_diagnostic.py`, `tests/test_m365_current_state_access_gate.py`, `tests/test_nac_cli.py`, `tests/test_windows_offline_cli_portability.py` | Positiv-, Negativ-, Sicherheits-, Replay-, Paritäts- und Windows-Tests |
| Dokumentation und AI-SBOM | `docs/de/cli.md`, `docs/en/cli.md`, `docs/de/m365-current-state-access-diagnostic.md`, `docs/en/m365-current-state-access-diagnostic.md`, `docs/de/sbom-for-ai.md`, `docs/en/sbom-for-ai.md` | Bedienung, Grenzen, Fehlerklassen, spätere Freigabekette und negative AI-Datenflussentscheidung |
| Kontext und CI | `agent-context/index.json`, `.github/workflows/windows-portability.yml` | on-demand Vertrag und verpflichtende Windows-Testmatrix |
| Traceability | DE/EN-Spec und -Plan, `workflows/contracts/spec-traceability.contract.json`, `scripts/validate_spec_traceability.py`, `tests/test_spec_traceability.py` | Issue, Planlinks, ACs, Dateien und Nachweise verbinden |

Andere Dateien werden nur aufgenommen, wenn ein zunächst roter Test eine
unmittelbare, in-scope Abhängigkeit beweist und der Plan vor dem Commit
synchronisiert wird. Eine Gantt-Änderung ist nicht vorgesehen, weil der Pfad
keinen Roadmap-, Scope- oder Meilensteinwechsel auslöst.

Der vollständige PR-Scope enthält außerdem den separat beauftragten und bereits
im freigegebenen Basisstand enthaltenen Commit `ecb1f96fc5cceaf2473661a0ff0cf0dd8d80e6f9`.
Er bindet Funktion8-/Microsoft-Anmeldeanforderungen an die explizite Nennung
von `ofunk@funktion8` oder `funktion8@funktion8`. Diese Governance-Klarstellung
erteilt keine Login-Freigabe und bleibt als eigener Vorwärtscommit prüfbar.

## Test-first-Implementierungsfolge

### 0. Datenschutzarmer SPFx-Client-Receipt

**Zuerst rot:** Zusätzliche oder unbekannte Receipt-Felder, Object-/Subject-ID,
Name, E-Mail, Tenantdaten, Token, Header, Request-Inhalt, Rohkorrelations-ID,
unsicherer Zufall, offenes oder rückwärts laufendes Zeitfenster, automatischer
Download, Telemetrie, bestehende Zieldatei, Reparse-/Hardlink-Ziel, fremde SID
oder breite DACL. Außerdem beweisen UI-Tests getrennt den Pfad ohne Subject und
den Pfad mit genau einmal verwendetem BFF-Korrelationswert.

**Dann grün:** Eine pure TypeScript-Hilfe erzeugt mit Web Crypto die flüchtige
Korrelations-ID, schließt das UTC-Fenster beim terminalen `no_access`-Zustand,
berechnet ausschließlich SHA-256-Bindings und serialisiert kanonisches JSON mit
exakter Feldmenge. Das Webpart bietet danach einen expliziten Download mit
festem personenfreiem Dateinamen an. Der BFF-Client akzeptiert für genau einen
Request die vorab erzeugte Korrelations-ID; er gibt weder Rohwert noch Header
an den Receipt zurück. Die offline CLI prüft maximal erlaubte Größe, UTF-8,
Duplikatschlüssel, Feldmenge, Datentypen, Fenster, Hashformate und verbotene
Schlüssel/Werte und materialisiert mit dem Windows-Sicherheitsbackend exklusiv
`client-observation-receipt.json`. POSIX-, Login-, Netzwerk-, Provider- und
Deploymentpfade bleiben unberührt.

### 1. Verification Contract und Validator

**Zuerst rot:** Contract fehlt, erlaubt unbekannte Felder, bildet nicht alle
AC-748-01 bis AC-748-08 ab, lässt Providerreads ohne Gate zu oder registriert
keinen echten Windows-Test im Quality Gate. Der allgemeine
Spec-Traceability-Validator erhält zusätzlich rote Fälle für fehlenden oder
nicht existierenden Planpfad, falschen Sprachpfad, ungepaarte DE/EN-Pläne,
abweichende Issue-/Spec-/AC-Bindung und einen Plan ohne konkrete
Validierungsbefehle oder vollständige AC-Nachweismatrix.

**Dann grün:** Geschlossenes YAML-Schema mit exakten Basis-, Ziel-, Toolchain-,
Resolver-, Account-/Principal-, DPA-/AVV-, Approval-, Snapshot-, Zähler- und
Check-Bindungen erstellen. Validator in `scripts/quality_gate.py` registrieren
und leere oder übersprungene Testsuiten als Fehler behandeln.

### 2. Pure Klassifikation

**Zuerst rot:** Je ein Fixture für die vier Zielklassen sowie Negativfälle für
fehlenden Clientbeleg, 2xx, anderen HTTP-Status, widersprüchliche Daten,
mehrere mögliche Klassen und unbekannte Felder.

**Dann grün:** Unveränderliche typisierte Snapshotprojektion und reine
Klassifikationsfunktion implementieren. Unvollständige oder mehrdeutige
Eingaben liefern einen stabilen Blockiercode, niemals eine Schätzung.

### 3. Post-Merge-, GitHub- und Governance-Gate

**Zuerst rot:** Falscher PR, nicht gemergter PR #747, falscher Merge-Commit
oder Tree, nicht abstammender Diagnose-HEAD, fehlender verpflichtender Check,
abweichender Resolver/Account/Principal, Same-Principal-Alias als zweite
Person, unzitierte externe Zwei-Personen-Pflicht, falsches
`OWNER_SOLO_APPROVAL`, `four_eyes_satisfied=true` oder ungültiger
Datenschutzbeleg.

**Dann grün:** Attestiertes, umgebungsbereinigtes Git für lokale Ancestry- und
Tree-Prüfung verwenden. Alle GitHub-Reads laufen unter Credential-Write-Guard
über den bereits etablierten Lesekanal. Fehlende externe Zwei-Personen-Pflicht
erlaubt `OWNER_SOLO_APPROVAL`; eine anwendbare konkret zitierte Pflicht mit nur
einem Principal blockiert `BLOCKED_SINGLE_PRINCIPAL`.

### 4. Windows-geschützte lokale Evidence und Run-Gate

**Zuerst rot:** Falscher Owner/SID, breite schreibende DACL, Reparse Point,
Hardlink, Pfad-/Datei-/Volume-ID- oder Hashwechsel, nicht attestierte Git-,
Python-, Node- oder Provider-Binärdatei, nicht bereinigte Umgebung,
schreibbarer Credential- oder Config-Store, fehlender oder driftender
DPA-/AVV-Beleg, paralleler Start, Approval-Replay, Crash nach Consume sowie
jeder nicht erlaubte `port_factory`-, `network_read`- oder
`run_gate_consume_write`- oder `result_evidence_write`-Zählerwert.

**Dann grün:** Bestehendes Windows-Sicherheitsbackend verwenden; keine
vereinfachte Pfadprüfung ergänzen. Das One-Shot-Gate vor Port-Factory atomar
konsumieren. Bei jeder Abweichung bleiben Port-, Netzwerk-, Login-,
Credential- und Mutationszähler null.

### 5. Geschlossene Ports und synthetische Adapter

**Zuerst rot:** Zusätzlicher Port, allgemeine Suche, ungebundene Resource,
abweichendes Fenster, Credential-Inhalt, Rohantwort, personenbezogenes Feld,
Redirect oder Mutation.

**Dann grün:** Protokolle für `ClientObservationReceiptPort`,
`TeamsTabMetadataReadPort`, `SharePointAppCatalogReadPort`,
`EntraApiPermissionReadPort`, `AzureFunctionMetadataReadPort`,
`AzureFunctionRequestLogReadPort` und `SharePointAccessDecisionReadPort`
definieren. Fake-Adapter geben nur die allowlisteten Booleans, geschlossenen
Enums, opaken Digests und Receipts zurück. In
`src/nac_bff/current_state_access_adapters.py` werden außerdem die sieben
produktiven schmalen Adapter implementiert: Graph-/SharePoint-/Entra-Reads
verwenden einen injizierten, attestierten No-Redirect-/No-Retry-Transport;
ARM- und Application-Insights-/Log-Analytics-Reads verwenden eine injizierte,
attestierte und read-only beschränkte Azure-CLI-Transportfähigkeit; die
SharePoint-Zugriffsentscheidung verwendet den vorhandenen gebundenen
synthetischen Listenleser. Kein Adapter erwirbt, erneuert, exportiert oder
persistiert Credentials. Die produktiven Adapter werden in dieser Phase nur
mit Fake-Transports getestet und nicht ausgeführt. Produktionskomposition und
jeder Adapter bleiben hinter derselben unveränderlichen Run-Autorisierung und
dem Credential-Write-Guard.

### 6. Doppelte Snapshot-Erhebung

**Zuerst rot:** Nur ein Snapshot, vertauschte oder wiederverwendete Sequenz,
gleicher Provider-Read-Receipt, andere Ziel-/Fenster-/Korrelationsbindung,
Provenienzdrift, unbekanntes Feld, PII, unterschiedliche kanonische Projektion
oder Drift der Autorisierung vor dem zweiten Read.

**Dann grün:** Zwei vollständige Erhebungen nacheinander durchführen, vor
jedem Portread neu autorisieren und getrennte Envelopes persistieren. Nur die
allowlistete Entscheidungsprojektion nach RFC 8785 kanonisieren und vergleichen.
Ergebnis nur bei identischem SHA-256 und genau einer Diagnoseklasse freigeben.

### 7. CLI und Komposition

**Zuerst rot:** Preflight erzeugt eine Port-Factory, produktiver Lauf startet
ohne finale Freigabe, CLI akzeptiert reale Tenantwerte oder eine verbotene
Login-/Retry-/Write-Option, beziehungsweise ein Adapter ist direkt erreichbar.

**Dann grün:** Beide festgelegten Unterbefehle registrieren, stabile
Exitcodes und redigierte JSON-Ausgaben liefern und Factory-Erzeugung nur nach
erfolgreichem Gate zulassen. Kein Import startet I/O.

### 8. Dokumentation, Traceability und Windows-CI

DE/EN-CLI und -Runbook synchron aktualisieren. `agent-context/index.json`
verweist auf Spec, Plan und Verification Contract. Der verpflichtende Workflow
führt die echte neue Testsuite auf Windows aus und beweist die geschlossene
Null-Seiteneffektmatrix. AI-SBOM, Lizenz-, Datenschutz-, Link-, Sprach- und
Spec-Traceability-Validatoren müssen unverändert grün bleiben.

### 9. `implement -> review -> fix`

Nach der Implementierung wird der vollständige `main...HEAD`-Diff geprüft.
Unabhängige Reviews decken mindestens Scope/Schichten, Governance/Privacy,
Validation/Windows und DE/EN-Parität ab. Befunde werden mit Vorwärtscommits
behoben; Historie wird nicht umgeschrieben. Erst danach folgen Vollsuite,
Graft, Strict Doctor, Push und Remote-CI.

## AC-zu-Nachweis-Matrix

| AC | Primäre Umsetzung | Pflichtnachweis |
| --- | --- | --- |
| AC-748-01 | synchrone DE/EN-Spec, Plan, CLI und Runbooks | Sprachparität, Links und unabhängiger Docs-Review |
| AC-748-02 | finaler Gate-Validator für PR #747, Merge-Commit/Tree und Git-Ancestry | positive Basisfixture plus falscher PR/Merge/Tree/Ancestry |
| AC-748-03 | eigene Module, Contracts, Gates und Artefakte | Import-/Pfad-Negativtests gegen jeden #739/#632-Zugriff |
| AC-748-04 | Resolver-, Principal-, DPA-, Approval- und per-Read Autorisierung | vollständige Governance-Negativmatrix und Drift vor Read 2 |
| AC-748-05 | pure geschlossene Klassifikation | vier positive Klassen plus Ambiguitäts-/Unvollständigkeitsmatrix |
| AC-748-06 | datenschutzarmer SPFx-Beleg, geschützte Offline-Materialisierung, zwei Envelopes, unabhängige Receipts und RFC-8785-Projektion | SPFx-/CLI-Allowlist-, Fenster-, Korrelations-, SID-/DACL-, Sequenz-, Receipt-, PII- und Drifttests |
| AC-748-07 | Windows-Backend, Credential-Write-Guard und One-Shot-Gate | Null-Seiteneffektzähler, Parallel-, Replay- und Crashtests auf Windows |
| AC-748-08 | Validator, Quality Gate, Traceability, Docs und CI | Vollsuite, Graft, Strict Doctor, vollständiger Diff und Remote-Checks |

## Lokale Validierungsreihenfolge nach Implementierung

```text
python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
python -m unittest discover -s tests -p test_nac_cli.py
python -m unittest discover -s tests -p test_windows_offline_cli_portability.py
python -m unittest discover -s tests -p test_spec_traceability.py
cd spfx/nac-bpmn-viewer && npm run build
powershell -NoProfile -Command "$genericRoot = Join-Path $env:TEMP 'nac-generic-workbench'; Push-Location spfx/nac-bpmn-viewer; try { npm run workbench:capture -- $genericRoot } finally { Pop-Location }"
powershell -NoProfile -Command "$liveRoot = Join-Path $env:TEMP 'nac-workbench-live-read'; Push-Location spfx/nac-bpmn-viewer; try { npm run workbench:live:capture -- $liveRoot } finally { Pop-Location }"
powershell -NoProfile -Command "python scripts/validate_generic_workbench_foundation.py --generated-evidence-root (Join-Path $env:TEMP 'nac-generic-workbench')"
powershell -NoProfile -Command "python scripts/validate_workbench_live_read_binding.py --generated-evidence-root (Join-Path $env:TEMP 'nac-workbench-live-read')"
python scripts/validate_m365_current_state_access_diagnostic.py
python -m unittest discover -s tests -p test_m365_current_state_access_client_receipt.py
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python -m unittest discover -s tests
graft build
graft check
python scripts/nac.py doctor --profile strict
git status --short
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

Die reale Read-only-Komposition wird in dieser Sequenz nur mit Fakes geprüft.
Ein lokaler grüner Lauf ist keine Providerfreigabe.

## Geplante Commitfolge

1. `test(issue-748): define diagnostic contract and negative matrix`
2. `feat(issue-748): add gated current-state diagnostic core`
3. `docs(issue-748): document Windows read-only diagnostic`
4. `fix(issue-748): address implementation review findings`

Die tatsächliche Zahl darf kleiner sein, wenn eine atomare Änderung dadurch
verständlicher bleibt. Jeder Commit bleibt im genehmigten Issue-#748-Scope;
kein Force-Push.

## Definition of Done für die Implementierungsphase

- alle AC-748-01 bis AC-748-08 besitzen ausführbare Nachweise;
- genau die vier Zielklassen sind deterministisch unterscheidbar;
- #739 bleibt terminal und #632 bleibt unberührt;
- Gate und per-Read-Autorisierung laufen vor jedem externen Zugriff;
- zwei unabhängige, redigierte Snapshots sind erforderlich;
- der autoritative Clientbeleg entsteht ausschließlich aus dem expliziten
  lokalen Download und der erfolgreichen geschützten Offline-Materialisierung;
- der Receipt enthält nur neutralen UI-Zustand, Subject-Boolean, geschlossenes
  Fenster sowie Fenster- und Korrelationsbindings;
- Login-, Credential-, Retry-, Redirect-, Mutation- und Deploymentzähler sind
  geschlossen enumeriert und null;
- die vollständige lokale Windows-Suite, Graft und Strict Doctor sind grün;
- SPFx-Build, Komponententests und visueller Nachweis des expliziten
  Receipt-Downloads sind grün;
- `main...HEAD` ist vollständig reviewed, der Workspace ist sauber und PR #749
  bleibt bis zur separaten finalen Merge-Freigabe geschützt;
- alle verpflichtenden Remote-Checks sind grün;
- die erwarteten Checks sind `Privacy and Secrets Guard / secret-scan`,
  `Privacy and Secrets Guard / privacy-lint`, `NaC Quality Gate / quality-gate`
  und `NaC Windows Portability / windows-offline-cli`;
- vor dem realen Read-only-Lauf liegt eine neue exakte Owner-Freigabe vor.

## Review-Gate

Der Basisplan und die Client-Receipt-Erweiterung wurden geprüft, freigegeben und
repository-lokal umgesetzt. Abnahme, Merge, SPFx-Bereitstellung und externer
Providerzugriff bleiben getrennte Gates.
