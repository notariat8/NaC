# Azure-BFF Schritt-7-Reconciliation

Status: `IMPLEMENTED_OFFLINE`

Datum: 11. September 2026
Führendes Issue: [#739](https://github.com/notariat8/NaC/issues/739)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-azure-bff-function-deployment-reconciliation
leading_issue: https://github.com/notariat8/NaC/issues/739
risk_gate: Human Approval
delivery_mode: Owner Direct
plan: docs/de/superpowers/plans/2026-09-11-m365-azure-bff-function-deployment-reconciliation.md
review_gates:
  - Human Approval
  - Security
acceptance_ids:
  - AC-739-R1
  - AC-739-R2
  - AC-739-R3
  - AC-739-R4
  - AC-739-R5
  - AC-739-R6
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
  - python3 scripts/validate_m365_azure_bff_live_activation.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Problem

Der gebundene Live-Lauf für `notary_team_01` ist in Schritt 7 mit
`AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS` terminal fehlgeschlagen. Die
allgemeine Finalization-Recovery darf diesen Providerzustand absichtlich nicht
auflösen. Dadurch bleiben die Journale `target`, `legacy` und `legacy_host` auf
`HELD`, obwohl read-only ARM-Daten inzwischen zeigen, dass der Deploy nicht
angewendet wurde.

## Entscheidung

Ein separater zentraler `nac`-Befehl behandelt nur diese genaue Form. Die
Inspection validiert State, Evidence, die 18 Ledger-Ereignisse, Prepared-Manifest,
Function-ZIP und alle Lock-Journale. Sie führt zwei identische Azure-Snapshots
über feste GET-URLs für genau `func-nac-bff-test-funktion8` aus. Nur ein
Site-Zeitstempel vor dem Schrittstart, keine neuere Deployment-Aktivität, eine
leere `deploymentStatus`-Liste und ein fehlender OneDeploy-Status ergeben
`FUNCTION_DEPLOYMENT_NOT_APPLIED`.

Die Inspection mutiert nichts. Das Lock-Release benötigt einen neuen
unveränderlichen Owner-Kommentar in Issue #739, der sämtliche Artifact-, Lock-,
Provider-, Commit-, Tree- und Toolchain-Hashes bindet. Vor jeder lokalen
Mutation werden diese Bindungen erneut geprüft. Der Reconciler hängt
crash-sicher nur `RELEASED` an die drei Journale an; alter State, Evidence,
Ledger und Azure bleiben unverändert.

## Akzeptanzkriterien

- **AC-739-R1:** Nur der exakte terminale Schritt-7-Zustand mit sechs bestandenen Schritten, 18 gültigen Ledger-Ereignissen und dem Ambiguitätscode ist zulässig.
- **AC-739-R2:** Zwei gleiche, allowlist-gebundene ARM-Snapshots beweisen `FUNCTION_DEPLOYMENT_NOT_APPLIED`; jede positive, fehlende oder driftende Information blockiert.
- **AC-739-R3:** Die owner-freie Inspection verändert keine lokale Datei und führt keinen Provider-Write aus.
- **AC-739-R4:** Ein Release benötigt die exakte neue #739-Freigabe von `ofunk` und alle ausgegebenen Hash-Bindings.
- **AC-739-R5:** Das Release verändert weder den historischen State noch Evidence, Ledger oder Azure und gibt alle drei Journale append-only frei.
- **AC-739-R6:** Crashs nach einem Journal-Append sind mit derselben Freigabe idempotent recoverbar; unbekannte Tails oder Bindungsdrift blockieren fail-closed.

## Nicht-Ziele

Kein Resume des alten Laufs, kein nachträgliches `PASSED`, kein Azure-Deploy,
kein Rollback, kein Delete und keine Erweiterung auf andere Schritte oder Apps.
