# Sicherer Abschluss der partiellen M365-BFF-Aktivierung – Implementierungsplan

Status: Plan-Fixes vollständig; durch Owner-Rollenentscheidung blockiert

Datum: 15. September 2026
Spec: [Sicherer Abschluss der partiellen M365-BFF-Aktivierung](../specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md)
Führendes Issue: [#746](https://github.com/notariat8/NaC/issues/746)
Draft-PR: [#747](https://github.com/notariat8/NaC/pull/747)
Delivery Mode: Protected PR
Risk Gate: Human Approval

## Ergebnis und Grenze

Die Umsetzung liefert einen prüfbaren Offline-Orchestrierungs- und
Operationsvertrag für den sicheren Abschluss der in #739 dokumentierten
partiellen Aktivierung. Sie erfindet keinen zweiten Reconciler: Die bestehende
zentrale CLI-Kante
`nac m365 teams-sharepoint bff-azure-function-deployment-reconcile`, ihr
Vertrag, ihr Validator und ihre Tests bleiben die einzige Ausführungskante für
Inspection und eine später gesondert freizugebende lokale Journalfreigabe.

Dieser Plan autorisiert ausschließlich Repository-Änderungen, statische
Prüfungen und synthetische Tests. Nicht autorisiert sind eine echte read-only
Provider-Inspection, die lokale Quarantänefreigabe aus Issue #739, ein neuer
Live-Lauf aus Issue #632, Authentifizierung sowie Tenant-, Provider- oder
Credential-Schreibaktionen.

## Änderungsflächen

| Fläche | Geplante Artefakte | Zweck |
| --- | --- | --- |
| Issue-#746-Vertrag | `workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml` | Provenienz, Phasen, Gates, Plattformen, Fehlercodes und AC-Matrix normalisieren |
| Enger Validator | `scripts/validate_m365_bff_failed_partial_safe_completion.py` | Struktur, bestehende #739-Kante, Negativnachweise und vollständige AC-Zuordnung erzwingen |
| Validator- und Operations-Tests | `tests/test_m365_bff_failed_partial_safe_completion.py` | Vertragsdrift, Gate-Replay, Redaktion, Null-Schreibgrenze und Journal-Crashfenster test-first abdecken |
| Bestehende Regressionen | vorhandene #739-, Live-CLI- und Windows-Portabilitätstests | Unveränderten Reconciler, ARM-Allowlist, Release-Algorithmus und Windows-Fail-closed-Grenze nachweisen |
| DE/EN-Dokumentation | Spec und Plan; CLI-Doku nur bei belegter Lücke | Operatorfolge und getrennte Freigaben verständlich halten |
| Traceability | `nac-spec-traceability`-Manifest der DE/EN-Spec | Issue, Specs, Pläne, ACs und Validierungsbefehle verbinden |
| AI-SBOM | `sbom/ai/nac-ai-sbom-draft.json`, `sbom/ai/nac-ai-sbom-export-mapping.json` | Den neuen agentischen Verification Contract mit Human-Review-, Provider-, Evidence- und Privacy-Grenze registrieren; kein Release-Export |

Änderungen am Produktions-Reconciler, an ARM-Allowlist, Release-Algorithmus,
Tenant-/Provideradaptern, Credentials, Teams-UI oder Berechtigungen sind nicht
eingeplant. Belegt ein roter Test dort einen Defekt, stoppt die Umsetzung; der
Defekt wird mit neuer Scope- und Risk-Gate-Prüfung separat vorgelegt.

## Verbindliche Phasen- und Gate-Tabelle

Die Phasen sind Orchestrierung und keine neuen persistierten Run-States. Der
alte Lauf bleibt `FAILED_PARTIAL`.

| Phase | Zulässige Eingaben | Zulässige Aktion | Erfolg | Sonst | Mutation |
| --- | --- | --- | --- | --- | --- |
| 0 Spec/Plan | freigegebener Spec-Commit und Repo-Evidence | statische Prüfung, synthetische Tests, geschützter PR | `OFFLINE_PLAN_VERIFIED` | `BLOCKED` | nur Git-/PR-Artefakte |
| 1 POSIX-Preflight | frische lokale #739-Artefakte auf unterstütztem POSIX-Host | Bindungen und Integrität lesen | `POSIX_READY` | `BLOCKED` | keine |
| 2 Provider-Inspection | `POSIX_READY`, erlaubte Netzwerkziele, bestehender Auth-Kontext | zwei gebundene ARM-GET-Snapshots | `FUNCTION_DEPLOYMENT_NOT_APPLIED` | `BLOCKED` | keine |
| 3 lokale Journalfreigabe | Phase-2-Evidence und neuer exakter #739-Owner-Kommentar | `--confirm-release-quarantine` | `LOCK_JOURNALS_RELEASED` | `BLOCKED` | drei deterministische append-only `RELEASED`-Datensätze |
| 4 neuer Offline-Gate | sauberer neuer Commit/Tree nach Phase 3 | neues #632-Aktivierungspaket erzeugen | `NEW_OFFLINE_OWNER_GATE_REQUIRED` | `BLOCKED` | lokale Offline-Evidence |
| 5 Live-Lauf | neue, exakt hashgebundene #632-Freigabe | genau ein kontrollierter Live-Lauf | vorhandene Live-Vertragszustände | `BLOCKED` oder vorhandener Fehlerzustand | nur gemäß separater Freigabe |

Nur Phase 0 wird in diesem PR gegen Repository- und PR-Artefakte ausgeführt.
Phasen 1 bis 5 werden weder gegen die aktuellen #739-Artefakte noch gegen
Credential-, Netzwerk-, Tenant- oder Providerzustand aufgerufen. Ihre Verträge,
Erfolgs- und Blockierpfade werden ausschließlich offline mit synthetischen
Fixtures und Ports ausgeübt. Die Spec-Freigabe ist kein gültiger Eingang für
Phase 3 oder 5.

## Plattform- und Befehlsmatrix

| Plattform-ID | Befehle | Zweck | Zulässige Seitenkanten |
| --- | --- | --- | --- |
| `windows_native` | Windows-Portabilitätssuite, Issue-#746-Test und portable Validatoren | Offline-Import, statischer Vertrag, frühes Fail-closed | keine Credential-, State-, Lock-, Netzwerk-, Subprozess-, Tenant- oder Providerkante |
| `posix_local` | gezielte #739-/Live-CLI-Tests, Issue-#746-Test und Aktivierungsvalidator | POSIX-Sicherheits- und Regressionsverträge | nur synthetische lokale Fixtures; keine echten Provideraufrufe |
| `ubuntu_remote_ci` | Graft, Strict Doctor und vollständige CI-Tests | autoritativer Linux-Gesamtnachweis | CI-Quellcodezugriff; keine Secrets, Logins oder Live-Aufrufe |
| `post_pr_remote` | strukturierte PR-Checkabfrage und vollständige `base...head`-Diff | geschützte Delivery nachweisen | GitHub-Metadaten read-only |

Windows liefert für Live, Recovery und beide Reconciliation-Kanten weiterhin
`PLATFORM_SECURITY_BACKEND_UNAVAILABLE`, `status: BLOCKED` und
`writes_started: false`, bevor eine verbotene Seitenkante erreicht wird.

## Maschinenlesbare Validierungszuordnung

Die folgenden IDs sind die verbindliche Auflösung der Befehls- und AC-Matrix.
Jeder Befehl gehört exakt zu einer Plattform; `acceptance_ids` und
`remote_evidence` machen seinen Nachweis maschinenlesbar.

```nac-validation-matrix
schema_version: nac.issue-746-validation-plan/v0.1
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
  - id: doc_links
    platform: windows_native
    command: python scripts/validate_doc_links.py
    acceptance_ids: [AC-746-01, AC-746-07]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: issue746_validator
    platform: windows_native
    command: python scripts/validate_m365_bff_failed_partial_safe_completion.py
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: ai_sbom
    platform: ubuntu_remote_ci
    command: python scripts/validate_ai_sbom.py
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: ai_sbom_export_mapping
    platform: ubuntu_remote_ci
    command: python scripts/validate_ai_sbom_export_mapping.py
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: issue746_windows_tests
    platform: windows_native
    command: python -m unittest tests.test_windows_offline_cli_portability tests.test_m365_bff_failed_partial_safe_completion
    acceptance_ids: [AC-746-02, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: issue746_posix_tests
    platform: posix_local
    command: PYTHONPATH=src python3 -m unittest tests.test_m365_bff_failed_partial_safe_completion tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
    acceptance_ids: [AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: activation_validator
    platform: posix_local
    command: python scripts/validate_m365_azure_bff_live_activation.py
    acceptance_ids: [AC-746-03, AC-746-04, AC-746-05, AC-746-06]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: graft_build
    platform: ubuntu_remote_ci
    command: graft build
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: graft_check
    platform: ubuntu_remote_ci
    command: graft check
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: strict_doctor
    platform: ubuntu_remote_ci
    command: python scripts/nac.py doctor --profile strict
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: fetch_main
    platform: post_pr_remote
    command: git fetch --no-tags --prune origin main
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [fresh origin/main]
  - id: diff_files
    platform: post_pr_remote
    command: git diff --name-status origin/main...HEAD
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [complete file list]
  - id: diff_commits
    platform: post_pr_remote
    command: git log --oneline origin/main..HEAD
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [complete commit list]
  - id: diff_patch
    platform: post_pr_remote
    command: git diff origin/main...HEAD
    acceptance_ids: [AC-746-01, AC-746-07, AC-746-08]
    remote_evidence: [complete base...head patch]
  - id: diff_whitespace
    platform: post_pr_remote
    command: git diff --check origin/main...HEAD
    acceptance_ids: [AC-746-07]
    remote_evidence: [complete base...head whitespace check]
  - id: pr_checks_watch
    platform: post_pr_remote
    command: gh pr checks 747 --watch
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [Privacy and Secrets Guard / secret-scan, Privacy and Secrets Guard / privacy-lint, NaC Quality Gate / quality-gate, NaC Windows Portability / windows-offline-cli]
  - id: pr_checks_enforced
    platform: post_pr_remote
    command: python scripts/validate_m365_bff_failed_partial_safe_completion.py --verify-pr-checks --expected-pr 747 --expected-head-from-local-git HEAD
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [exact required check names and successful states]
```

Jeder `commands`-Eintrag wird im geplanten Verification Contract zusätzlich
mit `scope` und `side_effect_class` materialisiert. Zulässige Werte sind:

- `scope: repository_static` und `side_effect_class: local_read_or_synthetic`
  für `windows_native` und `posix_local`;
- `scope: repository_aggregate` und `side_effect_class: ci_read_or_synthetic`
  für `ubuntu_remote_ci`;
- `scope: pr_747_expected_head` und
  `side_effect_class: github_read_only` für `post_pr_remote`.

Eine andere oder fehlende Zuordnung blockiert den #746-Validator. Auf diesem
Host wird der kanonische `python`-Befehl mit dem vom Codex-Workspace
bereitgestellten Python-3.11-Interpreter ausgeführt, weil kein unterstützter
Interpreter im Prozess-`PATH` liegt; CI muss `python` weiterhin reproduzierbar
über sein fest eingerichtetes Python 3.11 auflösen.

## Test-first-Reihenfolge

### 1. Issue-#746-Vertrag und zunächst rote Validatortests

- Eigenständigen Verification Contract mit stabiler Schema-Version,
  `leading_issue`, Spec-/Planpfaden, allen AC-IDs, vier Plattform-IDs und der
  vollständigen Phasen-/Gate-Tabelle anlegen.
- Tests zunächst für fehlende AC-Zuordnungen, verschmolzene #632/#739-Gates,
  GitHub-Issue als angeblichen Runtimezustand und erlaubte Windows-Live-Kante
  rot machen.
- Nur kanonische Bezeichner und Hashanforderungen speichern; keine echten
  Tenant-/Subscription-IDs, Hostnamen, Credentialwerte, Rohantworten oder
  lokalen Secretpfade.

### 2. Provenienz und drei nicht austauschbare Zustimmungen erzwingen

- #620, #632, #739 und #743 mit getrennten Rollen normalisieren; GitHub-
  Verweise sind Provenienz, nie aktueller Produktzustand.
- Drei unterschiedliche Gate-IDs verlangen: `SPEC_746_APPROVAL`,
  `ISSUE_739_QUARANTINE_RELEASE` und `ISSUE_632_NEW_LIVE_RUN`.
- Negativtests ändern Issue, Login, Author-Association, Kommentartext oder
  Kommentarhash und erwarten `BLOCKED` vor Mutation.
- Alte #632-/#739-Kommentare, der Spec-Kommentar und Cross-Issue-Replay müssen
  ausdrücklich scheitern.

### 3. Lokalen POSIX-Preflight vollständig abbilden

- State, Evidence, Ledger, drei Lock-Journale, Prepared Manifest, Function-ZIP,
  Aktivierungs-/Korrelationsbindung, Commit, Tree, Ziel und Toolchain/Binaries
  verlangen.
- Existenz, Eigentum/Berechtigung, No-follow, kanonischen Pfad und Hashbindung
  vor Netzwerk- oder Providerzugriff prüfen.
- Jede Bindung einzeln entfernen oder verändern; erwartet werden `BLOCKED`,
  Provider-Lesezähler `0` und Schreibzähler `0`.

### 4. Read-only Entscheidungstabelle an die bestehende #739-Kante binden

- Exakten CLI-Namen und bestehende doppelte ARM-GET-Inspection prüfen.
- Nur zwei identische, vollständig allowlistbare Projektionen mit
  `FUNCTION_DEPLOYMENT_NOT_APPLIED` dürfen Phase 2 erfolgreich abschließen.
- Deployment-Signal, fehlendes/unbekanntes Feld, Snapshot-Drift, Redirect,
  Authfehler, Netzwerksperre, Timeout oder nicht redigierbare Ausgabe ergeben
  `BLOCKED`.
- Synthetische Ports beweisen `provider_write_calls: 0`,
  `tenant_write_calls: 0` und `credential_write_calls: 0`.

### 5. Redaktions- und Ausgabevertrag prüfen

- Nur Status, stabilen Fehlercode, definierte Zähler und kanonische Hashes
  erlauben.
- Eindeutige synthetische Sentinels in Providerantwort, Exception,
  Standardausgabe, Fehlerausgabe, Log, temporäres Artefakt und vorgesehenen
  Approval-Text, Telemetrie und Shell-Historie injizieren; kein Sentinel darf
  einen Ausgabesink erreichen.
- Unbekannte oder nicht sicher redigierbare Felder blockieren an jedem
  einzelnen Sink.

### 5a. Status-, Fehlercode- und Zählervertrag präzisieren

- Der historische Lauf bleibt `FAILED_PARTIAL`; dessen bestehendes öffentliches
  Feld `writes_started: true` bedeutet ausschließlich, dass der alte Lauf vor
  der Reconciliation bereits Schreibschritte begonnen hatte. Es darf nicht als
  Schreibzähler des aktuellen Inspection-Aufrufs interpretiert werden.
- Erfolgreiche reine Inspection liefert weiterhin exakt
  `FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED`, zwei gleiche Snapshots und die
  Klassifikation `FUNCTION_DEPLOYMENT_NOT_APPLIED`.
- Der bestehende Vertragsabschnitt `stable_error_codes_exact` bleibt mindestens
  für die Owner-/Release-Gates exakt:
  `FUNCTION_DEPLOYMENT_CONFIRMATION_REQUIRED`,
  `FUNCTION_DEPLOYMENT_APPROVAL_ARGUMENTS_REQUIRED`,
  `FUNCTION_DEPLOYMENT_APPROVAL_ARGUMENTS_INVALID`,
  `FUNCTION_DEPLOYMENT_APPROVAL_INVALID`,
  `FUNCTION_DEPLOYMENT_APPROVAL_MISMATCH`,
  `FUNCTION_DEPLOYMENT_RECONCILIATION_UNSUPPORTED`,
  `FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_DRIFT`,
  `AZURE_FUNCTION_DEPLOYMENT_NOT_APPLIED_NOT_PROVEN`,
  `FUNCTION_DEPLOYMENT_LOCAL_ARTIFACT_CHANGED`,
  `FUNCTION_DEPLOYMENT_LOCK_SET_CHANGED` und
  `OWNER_COMMENT_VERIFICATION_FAILED`. Die vollständige erlaubte Menge wird
  nicht aus dieser Teilliste abgeleitet: Der neue Validator verknüpft
  strukturell `stable_error_codes_exact`, `_OBSERVATION_ERROR_CODES`, jeden
  literal oder dynamisch erreichbaren `_blocked`-Zweig des bestehenden #739-
  Moduls und `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`. Jede nicht fallgebundene
  Ergänzung, Entfernung oder Ausgabe eines fremden Codes blockiert.
- Nur die Test-/Validation-Evidence, nicht der öffentliche Runtime-Payload,
  erhält getrennte Zähler und Byte-Snapshots:
  `current_invocation_local_mutation_count`, `provider_read_snapshot_count`,
  `provider_write_count`, `tenant_write_count`, `credential_write_count`,
  `lock_call_count`, `network_call_count`, `subprocess_count` sowie Vorher-/
  Nachher-Hashes für State, Evidence, Ledger, Marker und alle drei Journale.
- Beim Preflight-Block sind alle Zähler `0` und alle Bytes unverändert. Bei
  Inspection sind lokale und alle Write-Zähler `0`, genau zwei Snapshots
  zulässig und Netzwerk/Subprozess nur nach dem bestehenden eng gebundenen
  Adaptervertrag erlaubt. Bei später freigegebener Journalmutation sind nur
  die drei deterministischen lokalen Appends zulässig; Provider-, Tenant- und
  Credential-Writes bleiben `0`.

### 5b. Credential-State am echten Adaptervertrag schützen

- Vor Phase 2 muss der bestehende Azure-CLI-Konfigurationsbaum no-follow,
  eigentümergebunden und byte-/metadaten-genau erfasst werden. Die Ausführung
  erhält nur einen privaten, read-only gebundenen Snapshot; Host-Credential-
  und Host-Konfigurationsdateien dürfen nicht beschreibbar sein.
- Interaktiver Login, Device Code, Token-Refresh, Cache-Neuanlage,
  Konfigurationsrewrite oder jede andere Persistenz muss vor beziehungsweise
  am Adapter fail-closed blockieren. Vorher-/Nachher-Hashes und Metadaten des
  Hostzustands müssen identisch sein.
- Der neue Test
  `test_credential_config_boundary_blocks_refresh_and_preserves_host_state`
  verwendet ausschließlich synthetische Credential-Sentinels und einen Fake-
  Azure-Prozess, der Refresh/Cache-Write versucht; erwartet werden `BLOCKED`,
  `credential_write_count: 0`, kein Sentinel-Sink und unveränderte Hostbytes.
- Lässt sich diese Garantie mit dem bestehenden Adapter nicht beweisen, bleibt
  Phase 2 gesperrt. Eine Produktionscodeänderung wird dann als separater Scope-
  und Risk-Gate-Befund vorgelegt und nicht still in #746 aufgenommen.

### 6. Journalfreigabe und Crashfenster regressiv prüfen

- Keinen neuen Release-Code schreiben. Die bestehenden Tests
  `test_exact_approval_releases_locks_without_changing_failed_run`,
  `test_wrong_owner_or_hash_never_releases_a_lock` und
  `test_crash_after_lock_append_is_recovered_idempotently` sind Pflichtnachweise.
- Drei Crashfenster verlangen: vor dem ersten Append, nach einem echten Präfix
  der drei deterministischen Appends und nach allen drei Appends vor Rückgabe.
- Nur derselbe unveränderte #739-Freigabehash darf ein echtes Präfix idempotent
  vervollständigen. Unbekannter Tail, andere Reihenfolge oder Freigabe blockiert;
  der alte Run bleibt `FAILED_PARTIAL`.

### 7. Regressionen, Traceability und Review abschließen

- Windows: Offline-Import bleibt verfügbar; Live, Recovery, Interruption- und
  Function-Deployment-Reconciliation sperren vor Parserdetails und Backend.
- POSIX: Sicherheitssemantiken, ARM-Allowlist und #739-Tests bleiben unverändert
  grün. Produktionscode- oder Allowliständerung ist ein Scope-Stop.
- DE/EN-Plan und Spec-Manifest synchron halten. Jede AC-Zeile zeigt auf
  Artefakt, Plattform, positiven/negativen Test, Status/Fehlercode, lokalen
  Befehl und Remote-Evidence.
- Scope-, Policy-, Validation- und DE/EN-Paritätsreviews prüfen die vollständige
  `base...head`-Diff; hohe/mittlere Befunde werden behoben und nachgeprüft.
- Keine Gantt-Änderung: Plan, Roadmap, Meilenstein und Pilotstatus ändern sich
  durch diese Planungsstufe nicht.

## Verbindliche neue Testmethoden und Fall-IDs

Der neue Issue-#746-Validator verlangt die folgenden exakten Methoden in
`tests/test_m365_bff_failed_partial_safe_completion.py` und ordnet sie den ACs
zu. Matrixmethoden müssen jede aufgeführte Fall-ID als benannten Subtest
ausführen; eine bloße Modul- oder Methodennennung genügt nicht.

| Methode | Pflicht-Fall-IDs | AC |
| --- | --- | --- |
| `test_contract_maps_every_acceptance_id_to_platform_command_and_evidence` | `AC-746-01` bis `AC-746-08` | alle |
| `test_provenance_roles_are_distinct_and_not_runtime_state` | `issue620_parent`, `issue632_live_contract`, `issue739_current_trail`, `issue743_historical_interruption` | AC-746-02 |
| `test_approval_replay_matrix_blocks_before_mutation` | `old_632_comment`, `old_739_comment`, `spec_746_comment`, `wrong_issue`, `wrong_login`, `wrong_author_association`, `changed_body`, `changed_hash`, `cross_issue_replay`, `owner_approved`, `owner_approval_reference`, `approval_body_sha256` | AC-746-02, AC-746-06, AC-746-08 |
| `test_registry_roles_and_separation_are_required_before_release` | `missing_process_role`, `missing_approval_role`, `inactive_identity`, `login_registry_mismatch`, `missing_operator`, `same_approver_and_operator`, `association_only` | AC-746-06, AC-746-08 |
| `test_preflight_binding_drift_matrix_blocks_before_provider` | `action`, `activation_hash`, `state_sha256`, `evidence_sha256`, `ledger_head_sha256`, `target_lock_sha256`, `legacy_lock_sha256`, `legacy_host_lock_sha256`, `provider_observation_sha256`, `failed_step`, `failed_step_started_at_utc`, `prepared_inputs_manifest_sha256`, `function_package_sha256`, `reconciler_commit`, `reconciler_tree`, `reconciler_toolchain_sha256`, `required_owner_login`, `correlation_id`, `target`, `binary`, `owner_permissions`, `nofollow_path`, `concurrent_lock` | AC-746-03 |
| `test_double_snapshot_accepts_only_stable_not_applied` | `stable_not_applied` | AC-746-04 |
| `test_provider_decision_block_matrix_has_zero_writes` | `deployment_applied`, `missing_field`, `unknown_field`, `snapshot_drift`, `redirect`, `auth_error`, `network_block`, `timeout`, `non_redactable` | AC-746-04, AC-746-08 |
| `test_redaction_sentinel_matrix_never_reaches_any_sink` | `provider_response`, `exception`, `stdout`, `stderr`, `log`, `temporary_artifact`, `approval_text`, `telemetry`, `shell_history`, jeweils `unknown_field` | AC-746-04, AC-746-06, AC-746-08 |
| `test_credential_config_boundary_blocks_refresh_and_preserves_host_state` | `interactive_login`, `device_code`, `token_refresh`, `cache_create`, `config_rewrite`, `host_bytes_changed`, `host_metadata_changed` | AC-746-04, AC-746-08 |
| `test_status_error_counter_and_hash_matrix_is_exact` | `historic_writes_started_not_current_write`, `inspection_required_status`, `not_applied_classification`, `stable_contract_codes_exact`, `observation_codes_exact`, `all_blocked_branches_case_bound`, `foreign_code_rejected`, `error_platform_backend_unavailable`, `preflight_all_counters_zero`, `inspection_two_snapshots_zero_mutations`, `release_three_local_appends_only`, `state_hash_unchanged`, `evidence_hash_unchanged`, `ledger_hash_unchanged`, `marker_hash_expected`, `three_journal_hashes_expected`, `network_and_subprocess_counts_bounded` | AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-08 |
| `test_windows_matrix_blocks_before_every_side_effect_edge` | `live`, `recovery`, `interruption_reconciliation`, `function_deployment_reconciliation`; jeweils `credential`, `state`, `lock`, `network`, `subprocess`, `tenant`, `provider` | AC-746-05 |
| `test_crash_before_first_append_keeps_all_journals_held` | `before_first_append` | AC-746-06 |
| `test_crash_after_true_prefix_completes_only_with_same_approval` | `after_first_append`, `after_second_append`, `changed_approval`, `unknown_tail`, `wrong_order` | AC-746-06 |
| `test_crash_after_all_appends_returns_idempotent_release` | `after_third_append_before_return`, `same_approval_replay` | AC-746-06 |
| `test_required_remote_checks_match_exact_context_names` | `pr_747`, `local_head_source`, `wrong_local_head`, `secret_scan`, `privacy_lint`, `quality_gate`, `windows_offline_cli`, `missing`, `duplicate`, `non_success`, `skipped`, `cancelled`, `renamed` | AC-746-07, AC-746-08 |
| `test_ai_sbom_registers_issue746_agentic_contract_without_release_export` | `human_review_owner`, `provider_boundary`, `evidence_binding`, `privacy_boundary`, `release_export_disabled` | AC-746-07, AC-746-08 |

Zusätzlich bleiben die drei exakt benannten #739-Regressionstests aus Schritt 6
Pflicht. Der neue Crashfenster-Nachweis ergänzt sie für „vor dem ersten Append“
und „nach allen drei Appends vor Rückgabe“, ohne den bestehenden Release-
Algorithmus zu ändern.

## AC-Evidenzmatrix

| AC | Artefakte | Plattform | Positivtest | Negativtest | Erwartung | Lokal | Remote |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-746-01 | DE/EN-Spec und -Plan, normalisierte Tabellen | Windows, Ubuntu | Sprachvalidator und Paritätsreview | abweichende Gate-Zeile | gleich oder `BLOCKED` | `language_parity`, `doc_links`, `diff_patch` | `NaC Quality Gate / quality-gate`, Review |
| AC-746-02 | Issue-#746-Vertrag | Windows, POSIX | getrennte Issue-Rollen | Altkommentar, falsches Issue, Replay | `BLOCKED`, Writes `0` | `issue746_validator`, `issue746_windows_tests`, `issue746_posix_tests` | `NaC Quality Gate / quality-gate` |
| AC-746-03 | Vertrag, bestehender #739-Reconciler | POSIX | vollständige Bindungsmatrix | fehlende/abweichende Bindung | `POSIX_READY` oder `BLOCKED`, Reads `0` bei Fehler | `issue746_posix_tests`, `activation_validator` | `NaC Quality Gate / quality-gate` |
| AC-746-04 | Reconciler, Live-Vertrag, Validator | POSIX | zwei identische NOT_APPLIED-Snapshots | Applied, Unknown, Drift, Redirect, Auth/Policy/Timeout | nur `FUNCTION_DEPLOYMENT_NOT_APPLIED` oder `BLOCKED`; Writes `0` | `issue746_posix_tests`, `activation_validator` | `NaC Quality Gate / quality-gate` |
| AC-746-05 | Windows-Fassade und Portabilitätssuite | Windows | Offline-Import | vier gesperrte Kanten | Plattformcode, Writes `0` | `issue746_windows_tests`, `activation_validator` | `NaC Windows Portability / windows-offline-cli` |
| AC-746-06 | Plan, Vertrag, Validator, Tests | alle | vollständige Matrix | Replay, Sentinel, Drift, drei Crashfenster | definierter Erfolg oder `BLOCKED` | `issue746_validator`, `issue746_windows_tests`, `issue746_posix_tests`, `activation_validator` | Quality/Windows gemäß Befehlsmatrix |
| AC-746-07 | beide Spec-Manifeste | alle | Links, ACs, Befehle auflösbar | fehlender Plan/AC/Befehl | grün oder `BLOCKED` | `spec_traceability`, `doc_links`, `graft_build`, `graft_check`, `strict_doctor`, alle `post_pr_remote`-IDs | exakte strukturierte PR-Checks |
| AC-746-08 | vollständige PR-Diff und Wächter | alle | Offline-Artefakte, synthetische Tests | echter Tenant-/Provider-/Credential-/Live-Aufruf | Zähler `0` | `issue746_validator`, beide Issue-#746-Test-IDs, `strict_doctor`, alle Diff-/PR-IDs | alle vier exakten Pflichtchecks |

## Validierungsbefehle

Native Windows-Offline-Prüfung:

```powershell
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python scripts/validate_m365_bff_failed_partial_safe_completion.py
python -m unittest tests.test_windows_offline_cli_portability tests.test_m365_bff_failed_partial_safe_completion
```

Unterstützter POSIX-/Ubuntu-Pfad, ausschließlich synthetische Ports:

```bash
PYTHONPATH=src python3 -m unittest tests.test_m365_bff_failed_partial_safe_completion tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
python scripts/validate_m365_azure_bff_live_activation.py
python scripts/validate_ai_sbom.py
python scripts/validate_ai_sbom_export_mapping.py
graft build
graft check
python scripts/nac.py doctor --profile strict
```

Geschützter PR-Nachweis:

```bash
git fetch --no-tags --prune origin main
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
git diff origin/main...HEAD
git diff --check origin/main...HEAD
gh pr checks 747 --watch
python scripts/validate_m365_bff_failed_partial_safe_completion.py --verify-pr-checks --expected-pr 747 --expected-head-from-local-git HEAD
```

Pflichtkontexte sind mindestens `Privacy and Secrets Guard / secret-scan`,
`Privacy and Secrets Guard / privacy-lint`, `NaC Quality Gate / quality-gate`
und für die Windows-Grenze `NaC Windows Portability / windows-offline-cli`.
Fehlend, übersprungen, abgebrochen oder umbenannt gilt als nicht bestanden.
Der zweite Befehl ermittelt den erwarteten SHA ausschließlich durch ein
internes read-only `git rev-parse HEAD`, liest danach PR #747 mit
`gh pr view 747 --json number,headRefOid,statusCheckRollup` und prüft genau eine
Instanz jedes Pflichtkontexts, Erfolgsstatus sowie
`lokaler HEAD == headRefOid`. Der SHA darf nicht aus derselben PR-Antwort als
Erwartungswert übernommen werden.

## Offene Rollenentscheidung

Die Spec-Freigabe auf Commit `012c441b...` autorisiert das Schreiben und Prüfen
dieses Plans, ist aber keine #739-Release- oder #632-Live-Freigabe. Vor der
späteren Implementierungsabnahme muss die verbindliche GitHub-Identity-Registry
mit den Gate-Identitäten übereinstimmen und aktive
`prozessverantwortung` sowie `freigabeverantwortung` nachweisen. Approver und
ausführender Operator müssen als verschiedene aktive Identitäten gebunden und
negativ getestet werden. Der aktuelle Unterschied zwischen `ofunk` in der Spec
und `ofunk-nvidia` in der Registry bleibt bis zu einer Owner-Entscheidung
`BLOCKED`; weder GitHub-Association noch Spec-Freigabe ersetzen diese Rollen.

## Stop Conditions

Die Umsetzung stoppt bei einer Änderung außerhalb der Offline-Artefakte, einem
nötigen Produktionscode-Fix, echten Runtime-/Providerdaten in Repo oder
GitHub, fehlender DE/EN-Parität, unvollständiger AC-Zuordnung, rotem Pflichtcheck
oder dem Versuch, die Spec-Freigabe als #739- oder #632-Gate zu verwenden.

Nach `implement -> review -> fix` endet der PR vor jeder echten Reconciliation.
Die nächste Freigabe wird erst anhand frischer, redigierter und hashgebundener
Evidence separat vorgelegt.
