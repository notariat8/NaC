# M365 Site-Permission-Grenze

Status: Offline-Safety-Rework für geschützten PR
Datum: 19. Juli 2026
Scope: Trennung von SharePoint-Schema-Provisionierung, Site-Permission-Verwaltung und Runtime-Zugriff

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-site-permission-boundary-671
leading_issue: https://github.com/notariat8/NaC/issues/671
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-19-m365-site-permission-boundary.md
review_gates:
  - External Service
  - Human Approval
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
  - AC-005
  - AC-006
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_azure_activation_provisioner_bootstrap tests.test_nac_bff_azure_activation_owner_gate tests.test_nac_bff_azure_activation tests.test_m365_azure_bff_live_activation_contract tests.test_teams_sharepoint_graph_data_plane tests.test_nac_bff_graph_activation
  - PYTHONPATH=src python3 scripts/validate_m365_azure_bff_live_activation.py
  - PYTHONPATH=src python3 scripts/validate_teams_sharepoint_graph_data_plane.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```


## Akzeptanz

- AC-001: Die Provisioning-App verlangt im Vertragsmodell zusätzlich `Sites.FullControl.All` für die Site-Permission-Verwaltung.
- AC-002: Runtime-App und BFF-UAMI bleiben exakt auf `Sites.Selected` und Site-Rolle `read` begrenzt.
- AC-003: State-Validator und read-only Pre-Write-Inventar verlangen die exakte bestehende Provisioning-Client-ID sowie die exakte Sechser-Allowlist und blockieren eine fehlende oder ersetzte App, doppelte oder breitere Rollen sowie effektiv nicht nutzbare Rechte vor dem ersten Provider-Write.
- AC-004: DE-/EN-Architektur und Runbook dokumentieren die bestehende App, den app-ID-gebundenen CLI-Befehl und das separate Owner-Gate.
- AC-005: Fokussierte Negativtests, Contract-Validatoren und Strict-Gate müssen erfolgreich sein.
- AC-006: Dieser Slice verändert weder Entra noch Tenant, Consent, Credentials oder Live-Runtime.

## Entscheidung

Die owner-gated App `NaC M365 Provisioning` behält `Sites.Manage.All`
für Listen und Spalten und erhält im Sollvertrag zusätzlich
`Sites.FullControl.All` ausschließlich für `GET` und `POST` auf
`/sites/{siteId}/permissions`. Das Recht ist tenantweit und darf nicht in
eine Runtime-Identität übergehen.

Die BFF-UAMI bleibt exakt auf die Microsoft-Graph-Anwendungsrolle
`Sites.Selected` und den Ziel-Site-Grant `read` begrenzt. Die
allgemeine NaC-Runtime-App und historische Tenant-Snapshots werden durch diesen
Offline-Rework nicht umgeschrieben.

## Fail-Closed-Grenze

Der hashgebundene lokale Provisioner-State muss vor Erzeugung der Live-Factory
exakt die sechs erlaubten Graph-Anwendungsrollen enthalten. Dazu gehört genau
eine `Sites.FullControl.All`-Zuweisung; als Status sind nur `created` und
`existing` erlaubt. Fehlendes FullControl endet mit
`PROVISIONER_SITE_PERMISSION_GRAPH_ROLE_MISSING`, eine fehlende, doppelte oder
zusätzliche Rolle mit `PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH`. Beide Fälle
stoppen ohne Providerzugriff oder Tenant-Write.

## Ausgeschlossen

Dieser PR weist keine Entra-Berechtigung zu, erteilt keinen Admin-Consent,
ändert keine Credentials, führt keinen Live-Retry aus und verändert keine
historischen Applied-State-Artefakte.
