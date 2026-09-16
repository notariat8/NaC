# Sicherer Abschluss der partiellen M365-BFF-Aktivierung

Status: Ursprungsspec vom Owner freigegeben; erweiterter Governance-Scope benötigt erneute hashgebundene Freigabe; Abnahme blockiert

Datum: 15. September 2026
Führendes Issue: [#746](https://github.com/notariat8/NaC/issues/746)
Implementierungsplan: [Sicherer Abschluss der partiellen M365-BFF-Aktivierung](../plans/2026-09-15-m365-bff-failed-partial-safe-completion.md)

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
  - agent-context/index.json
  - AGENTS.md
  - assets/docs/generic-workbench/VIS-721-manifest.json
  - docs/de/role-model.md
  - docs/de/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
  - docs/de/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
  - docs/en/role-model.md
  - docs/en/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
  - docs/en/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
  - policies/access-control-policy.yaml
  - policies/github-identity-registry.json
  - policies/github-identity-registry.schema.json
  - policies/role-model-policy.yaml
  - sbom/ai/nac-ai-sbom-draft.json
  - sbom/ai/nac-ai-sbom-export-mapping.json
  - scripts/onboarding_wizard.py
  - scripts/quality_gate.py
  - scripts/validate_identity_registry.py
  - scripts/validate_m365_azure_bff_live_activation.py
  - scripts/validate_m365_bff_failed_partial_safe_completion.py
  - tests/test_identity_registry.py
  - tests/test_m365_azure_bff_live_activation_contract.py
  - tests/test_m365_bff_failed_partial_safe_completion.py
  - tests/test_validate_windows_offline_cli_portability.py
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
  - python scripts/validate_ai_sbom_export_mapping.py
  - python scripts/validate_m365_bff_failed_partial_safe_completion.py
  - python scripts/validate_m365_azure_bff_live_activation.py
  - python -m unittest tests.test_windows_offline_cli_portability tests.test_spfx_bff_catalog_readback_regression tests.test_m365_bff_failed_partial_safe_completion
  - PYTHONPATH=src python3 -m unittest tests.test_m365_bff_failed_partial_safe_completion tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git fetch --no-tags --prune origin main
  - git diff --name-status origin/main...HEAD
  - git log --oneline origin/main..HEAD
  - git diff origin/main...HEAD
  - git diff --check origin/main...HEAD
  - gh pr checks 747 --watch
  - python scripts/validate_m365_bff_failed_partial_safe_completion.py --verify-pr-checks --expected-pr 747 --expected-head-from-local-git HEAD --protected-identity-resolver-file <repo-external-json> --protected-identity-resolver-sha256 <sha256> --operator-account-id <provider-qualified-operator-account> --owner-solo-approval-reference <issue-746-comment-url>
```

## Zweck und Abgrenzung

Diese Spec beschreibt den sicheren Weg vom aktuellen partiellen Zustand zur
Möglichkeit eines neuen, separat freizugebenden Live-Laufs für den ausschließlich
synthetischen Workspace `notary_team_01`. Sie autorisiert selbst weder einen
Provider-Write noch eine lokale Lock-Freigabe, einen Live-Retry oder die
Erzeugung einer gültigen Live-Freigabe.

Die sichtbare Teams-Meldung `Kein Zugriff auf diesen Arbeitsbereich` wird nicht
durch eine UI-Umgehung behoben. Der Abschluss muss die unveränderte Kette
`Teams/SPFx -> AadHttpClient -> Entra-geschützter BFF -> serverseitiges
Zugriffsgate -> Microsoft Graph REST v1.0` nachweisen. Bis dahin bleibt die
Meldung ein erwartbares fail-closed Ergebnis.

## Dokumentierte Provenienz und zu verifizierende Ausgangshypothese

GitHub-Flächen sind kein Produkt- oder Runtimezustand. Die folgenden Angaben
sind historische Provenienz und bilden nur die Ausgangshypothese. Der aktuelle
lokale und providerseitige Zustand bleibt `UNVERIFIED` und damit `BLOCKED`, bis
die gebundenen lokalen Artefakte und die doppelte read-only Inspection frisch
bestanden sind. Vier bestehende Issues haben unterschiedliche Rollen:

- [#620](https://github.com/notariat8/NaC/issues/620) bleibt der Parent für die
  sichtbare M365-MVP-Testumgebung. Sein Lauf vom 19. Juli endete an Schritt 6
  `grant_target_site_read` als `FAILED_PARTIAL`; Lock und Ledger wurden damals
  geordnet abgeschlossen. Dieser Lauf ist nur historische Provenienz.
- [#632](https://github.com/notariat8/NaC/issues/632) bleibt der maßgebliche
  Live-Aktivierungsvertrag und die vertraglich festgelegte Freigabefläche für
  einen späteren neuen Live-Lauf.
- [#739](https://github.com/notariat8/NaC/issues/739) enthält die aktuelle
  dokumentierte Live-Laufspur und das getrennte lokale Schritt-7-Release-Gate.
  Der jüngste dokumentierte Lauf
  `nac-bff-live-20260908-issue739-v4` bestand die Schritte 1 bis 6 und endete an
  Schritt 7 `deploy_function_package` mit
  `AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS`. Die drei Lock-Journale blieben
  quarantänisiert.
- [#743](https://github.com/notariat8/NaC/issues/743) dokumentiert einen älteren
  Unterbrechungsfall, für den laut Issue der sichere lokale Zustand fehlte.
  Seine Evidence darf
  nicht mit der aktuellen #739-Laufspur vermischt oder zur Rekonstruktion
  fehlender Bindungen verwendet werden.

Der Repo-Stand enthält mit `bff-azure-function-deployment-reconcile` bereits
die enge Inspection ohne neuen Owner-Gate. Sie ist auf exakt den
terminalen Schritt-7-Fall begrenzt und akzeptiert nur zwei gleiche, fest auf die
Ziel-Function begrenzte ARM-Snapshots mit der Klassifikation
`FUNCTION_DEPLOYMENT_NOT_APPLIED`. Diese Spec erweitert deren
Sicherheitswirkung nicht, sondern ordnet sie in eine vollständige
Abschlusssequenz ein.

## Bewertete Lösungswege

### A. Read-only Reconciliation und anschließend neuer Lauf

Der unterstützte POSIX-Host prüft zuerst alle lokalen Bindungen, dann die
zulässige Netzwerkreichweite und erst danach die exakt allowlisteten
read-only Providerzustände. Nur eine eindeutige Klassifikation darf zu einer
separaten lokalen Quarantänefreigabe und später zu einem neuen Offline-Owner-
Gate führen. Das ist der gewählte Weg, weil er alte Evidence erhält und jede
Mutation an einen neuen, engen Owner-Gate bindet.

### B. Unmittelbarer idempotenter Voll-Rerun

Ein neuer zwölfstufiger Lauf könnte vorhandene Ressourcen wiederverwenden.
Solange der aktuelle Lock, die Schritt-7-Evidence und der Providerzustand nicht
eindeutig reconciled sind, würde dies jedoch die bestehende Quarantäne umgehen.
Der Weg bleibt gesperrt.

### C. Manueller Neuaufbau oder Cleanup

Eine manuelle Löschung, Berechtigungsänderung oder erneute Bereitstellung könnte
den Zielzustand vereinfachen, zerstörte aber Provenienz und verließe den
freigegebenen Nicht-Rollback-/Nicht-Lösch-Rahmen. Dieser Weg ist nicht Teil des
Designs.

## Gewählte Orchestrierungsfolge

Die Bezeichnungen im folgenden Diagramm sind Orchestrierungsphasen, keine neuen
persistierten Run-States. Der alte Run-State bleibt durchgehend
`FAILED_PARTIAL`.

```text
LOCAL_PRECHECK
  -> BLOCKED
  -> POSIX_READY
       -> NETWORK_BLOCKED
       -> READ_ONLY_RECONCILIATION
            -> BLOCKED
            -> FUNCTION_DEPLOYMENT_NOT_APPLIED
                 -> OWNER_GATE_REQUIRED_FOR_LOCAL_RELEASE
                 -> LOCK_JOURNALS_RELEASED
                      -> NEW_OFFLINE_OWNER_GATE_REQUIRED
                      -> LIVE_RUN_SEPARATELY_APPROVED
```

`LOCK_JOURNALS_RELEASED` bedeutet ausschließlich, dass die drei lokalen
Lock-Journale für den nachweislich nicht angewandten Schritt-7-Deploy append-only
freigegeben wurden. Der alte Lauf bleibt `FAILED_PARTIAL`; State, Evidence,
Ledger und Providerzustand bleiben unverändert. Dieser Status ist weder
`PASSED` noch eine Live-Freigabe.

## Phase 1: lokaler POSIX-Preflight

Vor Credential-, Netzwerk- oder Providerzugriff muss die lokale Prüfung
mindestens bestätigen:

1. unterstütztes POSIX-Betriebssystem mit den bestehenden `flock`-,
   `O_NOFOLLOW`-, Descriptor-, Eigentümer- und Berechtigungssemantiken;
2. sauberer Git-Arbeitsbaum sowie exakter Commit und Tree;
3. exakte Aktivierungs-, Korrelations-, Approval- und Zielbindung des aktuellen
   #739-Laufs;
4. bytegenaue State-, Evidence-, Ledger-, Prepared-Manifest-, Function-ZIP- und
   Journalintegrität;
5. exakte Toolchain- und Binary-Bindings ohne Symlink-, Pfad- oder
   Nachlade-Drift;
6. keine konkurrierende Lock-Eigentümerschaft.

Windows bleibt für Live, Recovery und Provider-Reconciliation vor jedem dieser
Zugriffe mit `PLATFORM_SECURITY_BACKEND_UNAVAILABLE` gesperrt. Die portable
Windows-Offline-CLI darf ausschließlich statische Validierung und Planansicht
bereitstellen.

## Phase 2: Netzwerk- und Provider-Reconciliation

Die zentral verwaltete NVIDIA-Sandbox-Policy ist eine externe Vorbedingung. Vor
einem neuen Owner-Gate werden ausschließlich die drei in #739 dokumentierten,
eng gebundenen Hostziele geprüft: Function-Host, SCM-Host und Azure-CLI-
Blob-Host. Eine lokale Allow-Regel, ein Wildcard-Ausweichen oder eine breitere
Policyänderung ist nicht Bestandteil dieser Arbeit.

Nach erfolgreichem Read-only-Netzwerkcheck darf ausschließlich die bestehende
Schritt-7-Inspection mit einem bereits hergestellten authentifizierten Kontext
laufen. Sie darf keine interaktive Authentifizierung starten, Credential-
Material anlegen, ändern oder persistieren und keine Berechtigung verändern.
Sie liest die dokumentierten ARM-Endpunkte für die exakte Ziel-Function zweimal.
Zulässig ist nur ein stabiler Snapshot, der
`FUNCTION_DEPLOYMENT_NOT_APPLIED` beweist. Ein beobachtetes Deployment, ein
fehlendes Feld, Drift zwischen den Snapshots, eine Umleitung, ein Auth- oder
Policyfehler oder ein nicht allowlistbares Providerergebnis liefert `BLOCKED`.

Die Ausgabe enthält nur Status, stabile Fehlercodes, Zähler und kanonische
Hashes. Strikte Allowlists gelten für Standardausgabe, Fehlerausgabe, Logs,
temporäre Artefakte, Exceptions, Telemetrie, Shell-Historie und Approval-
Kommentare. Rohantworten, IDs, URLs, Tokens, Credentialwerte, lokale
Secretpfade, personenbezogene Daten und Mandatsdaten werden weder dorthin noch
in GitHub oder das Repo übernommen; unbekannte oder nicht redigierbare Felder
blockieren.

## Phase 3: getrennte lokale Quarantänefreigabe

Die Inspection ohne neuen Owner-Gate darf keine Datei verändern. Erst ein neuer
unveränderlicher Kommentar in Issue #739 vom exakt verifizierten Provider-
Login `<protected-provider-login>` aus dem zugriffsgeschützten Resolver mit
zulässiger Author-Association und der exakten Aktion
`RELEASE_QUARANTINE_FOR_NOT_APPLIED_FUNCTION_DEPLOYMENT` bindet den Provider-
Transport. Governance-Autorität entsteht erst, wenn der provider-qualifizierte
Account durch die Registry auf einen aktiven Principal mit der Owner-Rolle
`prozessverantwortung` und der Qualifikation `process_design` aufgelöst wird.
Für Issue #746 ist keine anwendbare, konkret zitierte gesetzliche,
regulatorische, vertragliche oder verbindliche Security-Pflicht zu zwei
verschiedenen natürlichen Personen belegt. Deshalb darf derselbe aktive
Principal die Entscheidung revisionsfest als `OWNER_SOLO_APPROVAL`
dokumentieren; sie ist keine Vier-Augen-Freigabe. Wird später eine solche
Pflicht mit Quellenreferenz, Version, kanonischem Digest und Scope als
anwendbar gebunden, blockiert ein einzelner Principal mit
`BLOCKED_SINGLE_PRINCIPAL`. Erst bei zwei aktiven, passend qualifizierten und
verschiedenen Principals ist `FOUR_EYES_APPROVAL` zulässig. Danach darf der
Operator den bestehenden Reconciler mit `--confirm-release-quarantine`
ausführen. Dieses Gate bindet Kommentar-Body
und dessen Hash sowie State-, Evidence-, Ledger-, Lock-, Provider-,
Prepared-Input-, Function-Paket-, Commit-, Tree- und Toolchain-Hashes.

Die einzige Mutation ist das crash-sichere, append-only Anhängen eines
`RELEASED`-Datensatzes an jedes der drei Journale. Es gibt keinen Azure-, Entra-, Graph-, SharePoint-, Teams-,
App-Catalog- oder Credential-Write. Unbekannte Journal-Tails oder jede Drift
blockieren. Ein gerissener Append darf nur mit derselben unveränderten
Freigabebindung idempotent fortgesetzt werden.

## Phase 4: neuer Live-Lauf als eigener Gate

Nach nachgewiesener Quarantänefreigabe wird aus einem neuen sauberen Commit und
Tree auf dem unterstützten POSIX-Host ein vollständiger Offline-Owner-Gate
erzeugt. Er bleibt an die vorhandene, vertraglich festgelegte Issue-#632-Fläche,
den exakt verifizierten Provider-Login und die zulässige Author-Association als
Transportnachweise gebunden. Zusätzlich werden Freigabe- und Operator-Account
über die Registry auf aktive, passend qualifizierte Principals aufgelöst. Der
Personenmodus folgt derselben quellgebundenen Entscheidung: ohne anwendbare
konkret zitierte Zwei-Personen-Pflicht `OWNER_SOLO_APPROVAL`, mit einer solchen
Pflicht und nur einem Principal `BLOCKED_SINGLE_PRINCIPAL` und bei verschiedenen
qualifizierten Principals `FOUR_EYES_APPROVAL`. Eine Rollenbezeichnung allein
ist kein Quellenbeleg. Alte #632-/#739-Kommentare sind keine Freigabe für diesen
Lauf.

Die spätere Live-Freigabe muss mindestens den neuen Aktivierungs-Hash, Commit,
Tree, Ziel-, Permission-, Schrittfolgen-, Provisioner-Bootstrap- und
Toolchain-Binding sowie die unveränderte Nicht-Rollback-/Nicht-Lösch-Regel
enthalten. Erst nach separater Owner-Zustimmung darf genau ein kontrollierter
Live-Lauf starten. Alle bestehenden Stop-, Lock-, Evidence-, Redaktions- und
Readback-Regeln bleiben unverändert.

Die drei Zustimmungen sind nicht austauschbar: Die Freigabe dieser Design-Spec
ist weder die Freigabe der lokalen Quarantänemutation noch die Freigabe des
späteren Live-Laufs.

## Akzeptanzkriterien

- **AC-746-01:** Diese deutsche führende Spec und ihre englische Übersetzung
  dokumentieren denselben Ausgangszustand, dieselben Varianten, Trust
  Boundaries, Stop Conditions und getrennten Gates.
- **AC-746-02:** #620, #739 und #743 werden als getrennte Provenienzspuren
  zusammen mit dem maßgeblichen #632-Live-Aktivierungsvertrag verbunden; weder
  alte Evidence noch ein alter Owner-Kommentar werden als aktueller Erfolg,
  aktueller State oder neue Freigabe behandelt.
- **AC-746-03:** Der Abschlussweg prüft auf einem unterstützten POSIX-Host vor
  Providerzugriff den exakten lokalen State, Ledger, alle Lock-Journale,
  Prepared Inputs, Paket, Commit, Tree, Toolchain und Zielbindung; fehlende oder
  widersprüchliche Bindungen liefern `BLOCKED`.
- **AC-746-04:** Die Provider-Inspection bleibt vollständig read-only,
  zielgebunden, doppelt erhoben und redigiert. Ausschließlich
  `FUNCTION_DEPLOYMENT_NOT_APPLIED` erlaubt den Übergang zum getrennten lokalen
  Release-Gate.
- **AC-746-05:** Windows-Live-, Recovery- und Reconciliation-Pfade stoppen vor
  Credential-, State-, Netzwerk- oder Providerzugriff mit
  `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`; POSIX-Sicherheitssemantiken werden
  nicht abgeschwächt.
- **AC-746-06:** Der nach Spec-Freigabe zu erstellende Implementierungsplan
  beschreibt test-first die POSIX-/Windows-Matrix, Reconciliation-
  Entscheidungstabelle, stabile Fehlercodes, Redaktion, Crash-Fenster und
  exakte Gate-Übergänge als Orchestrierungs-/Operationsplan unter
  Wiederverwendung der bestehenden #739-CLI, Verträge und Tests. Reconciler-
  Code, ARM-Allowlist und Release-Algorithmus bleiben ohne separat belegten
  Defekt unverändert. Negativtests decken Replay alter #632- oder #739-
  Kommentare, Wiederverwendung der Spec-Freigabe, falsches Issue, falschen
  Login oder Author-Association, veränderten Kommentar-Body oder Hash,
  Binding-Drift sowie die ausschließlich unter identischer Freigabe zulässige
  Fortsetzung eines partiellen Journal-Appends ab.
- **AC-746-07:** Spec-Traceability verbindet Issue, DE/EN-Spec, den späteren
  DE/EN-Plan, alle AC-IDs und konkrete lokale sowie Remote-Validierung.
- **AC-746-08:** Dieser Draft-PR führt keine Tenant-, Provider-, Credential- oder
  Live-Aktion aus. Lokale Quarantänefreigabe und neuer Live-Lauf bleiben zwei
  separate, hashgebundene Owner-Gates.

## Validierungsmodell

Die Manifestbefehle sind keine plattformunabhängig gemeinsam auszuführende
Liste. Der native Windows-Pfad führt ausschließlich die portable Offline- und
Fail-closed-Suite aus. Die POSIX-BFF-Suite, der Aktivierungsvalidator, Graft und
der strikte Doctor laufen auf dem unterstützten POSIX- beziehungsweise
`ubuntu-latest`-Pfad. Der spätere Plan muss diese Zuordnung für jeden Befehl als
`windows_native`, `posix_local`, `ubuntu_remote_ci` oder `post_pr_remote`
maschinenlesbar festhalten.

Der Plan muss außerdem eine AC-Evidenzmatrix führen:

`AC-ID -> Artefakte -> Plattform -> Positivtest -> Negativtest -> erwarteter
Status/Fehlercode -> lokaler Befehl -> Remote-Check/Evidence`.

Mindestens ein Issue-#746-spezifischer Validator oder ein gleichwertig enges
Mapping auf exakte bestehende Testmethoden prüft die Provenienztrennung,
Preflight-Reihenfolge, Null-Schreibzähler, Redaktionssentinels, jeden
Blockierpfad und alle drei Journal-Crashfenster. Ein rohes Modul- oder
Validatornamenslisting genügt nicht. Der bestehende M365-Live-
Aktivierungsvalidator ist Regressionsevidence, aber allein kein Nachweis für
alle AC-746-Kriterien.

AC-746-01 benötigt zusätzlich zur allgemeinen Sprachparitätsprüfung einen
unabhängigen semantischen DE/EN-Review oder eine gemeinsam normalisierte
maschinenlesbare Zustands-/Gate-Tabelle. AC-746-02 benötigt eine redigierte,
hashgebundene Provenienzreferenz auf die unveränderlichen GitHub-Kommentare oder
einen gleichwertigen owner-freien, read-only GitHub-Nachweis; Issue-Flächen
selbst bleiben ausdrücklich kein Produktzustand.

Vor Merge werden vollständige Datei-, Commit- und `base...head`-Diff geprüft.
Remote müssen mindestens `Privacy and Secrets Guard / secret-scan`, `Privacy
and Secrets Guard / privacy-lint` und `NaC Quality Gate / quality-gate`
als exakte Namen vorhanden und erfolgreich sein. Fehlende, übersprungene,
abgebrochene oder anders benannte Ersatzchecks blockieren; der spätere
`post_pr_remote`-Nachweis wertet die strukturierte Checkliste deterministisch
aus. Bis Plan, Implementierung und diese Evidence vorliegen, bleiben AC-746-01
bis AC-746-08 offen; der aktuelle Draft behauptet keine Abnahme.

## Stop Conditions

Die Sequenz stoppt ohne Mutation bei nicht unterstützter Plattform, unsauberem
Arbeitsbaum, fehlender oder abweichender Laufbindung, State-/Ledger-/Lock-
Integritätsfehler, Toolchain- oder Binary-Drift, Netzwerkpolicy-Block,
Credentialfehler, unbekannter Providerantwort, Snapshot-Drift, beobachtetem oder
nicht sicher ausgeschlossenen Deployment, nicht redigierbarer Evidence oder
fehlgeschlagener unabhängiger Prüfung.

## Nicht-Ziele

- kein Live-Retry oder Provider-Write in diesem PR;
- kein Resume, Rollback, Delete oder manuelles Unlock;
- keine neue oder breitere Permission;
- keine lokale Umgehung zentraler Netzwerkpolicy;
- keine Änderung der Teams-UI zur Unterdrückung eines berechtigten Deny;
- keine Behauptung, dass die Function App das neue Paket ausführt;
- keine produktiven Daten oder Erweiterung auf andere Workspaces.

## Review-Gate

Der Owner hat diesen Spec-Stand auf Commit
`012c441b74cfd1a1de61fd3d48ed09282aaba328` freigegeben. Der verlinkte DE/EN-
Implementierungsplan hat `plan -> review -> fix` abgeschlossen;
`implement -> review -> fix` läuft. Diese Freigabe ersetzt weder das lokale
Issue-#739-Release-Gate noch das Issue-#632-Gate für einen späteren Live-Lauf.
Der auf `012c441b...` freigegebene Ursprungsscope umfasst nicht die spätere
Account-zu-Principal-Governance-Reparatur und die aktuelle erweiterte
Artefaktliste. Dieser kombinierte Scope benötigt nach Abschluss der Fixes eine
neue, exakt an den finalen PR-Head gebundene Owner-Freigabe. Die vorliegende
lokale Governance-Entscheidung wählt für Issue #746 `OWNER_SOLO_APPROVAL`, weil
keine anwendbare externe Zwei-Personen-Pflicht mit Quellenreferenz und Scope
  belegt ist; sie ist keine Vier-Augen-Freigabe. Die versionierte öffentliche
Registry enthält nur synthetische Beispiele. Ein repository-externer,
eigentümergebundener POSIX-Resolver mit exakt Modus `0600` muss genau drei bekannte
Accounts demselben Principal zuordnen und seinen SHA-256 an die
final-head-gebundene Freigabe binden. Account und Principal erscheinen in
öffentlicher Evidence ausschließlich als zweckgetrennte SHA-256-Bindungen.
Diese Identitätsauflösung bleibt für
  jedes spätere #739- oder #632-Gate separat erforderlich. Die Abnahme bleibt
  außerdem wegen noch ausstehender ausführbarer Evidence für Credential-, Redaktions- und
#739-Hashgrenzen sowie dynamische Fehlercodepfade ausdrücklich `BLOCKED`.
