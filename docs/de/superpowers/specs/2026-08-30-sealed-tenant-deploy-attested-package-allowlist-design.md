# Versiegelte Tenant-Deploy-Allowlist für attested SPFx-Paketpfad

Status: `IMPLEMENTED_OFFLINE`

Datum: 30. August 2026
Führendes Issue: [#740](https://github.com/notariat8/NaC/issues/740)
Scope: Control-Plane-Allowlist des versiegelten `test-environment-deploy`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: sealed-tenant-deploy-attested-package-allowlist
leading_issue: https://github.com/notariat8/NaC/issues/740
risk_gate: None
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-08-30-sealed-tenant-deploy-attested-package-allowlist.md
review_gates:
  - Privacy
  - Human Approval
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - python3 -m unittest tests.test_m365_mvp_test_environment_deploy tests.test_m365_spfx_site_deployment
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
  - python3 scripts/nac.py doctor --profile strict
```

## Zweck

Die versiegelte `test-environment-deploy`-Control-Plane (Pfad
`nac m365 teams-sharepoint test-environment-deploy`) schlägt beim Schritt
`add_or_overwrite_tenant_app` mit `M365_CLI_COMMAND_NOT_ALLOWLISTED` fehl, gewrappt
als `command_runner_exception`. Ursache ist eine Regression: der Plan-Builder
`build_spfx_site_deployment_plan` nutzt defaultmäßig
`ATTESTED_PACKAGE_RELATIVE_PATH`
(`assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg`), die
Runner-Allowlist `_matches_spfx_app_add` / `_is_bound_package_path` akzeptiert
als `--filePath` für `m365 spo app add` aber nur
`PACKAGE_RELATIVE_PATH` (`spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg`).
Die committede Past-Evidence (PASSED, 14 Commands) nutzte noch
`PACKAGE_RELATIVE_PATH` und belegt, dass der versiegelte memfd-Upload via
`spo app add --filePath /proc/self/fd/N` funktioniert. Einzig die
Allowlist-Pfadform blockiert den attested-Pfad.

## Scope

Im Scope liegen:

- Erweiterung von `_is_bound_package_path` und `_matches_spfx_app_add` in
  `src/nac_m365_graph/mvp_test_environment_deploy.py`, sodass neben
  `spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg` auch
  `assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg` als gebundenes
  Artefakt für `m365 spo app add --filePath` akzeptiert wird,
- Beibehaltung der harten Pfad-Checks: absolut, kein `..`, fester erwarteter
  Suffix, regular File,
- Regression-Test, der beide Pfadformen durch die Allowlist lässt und eine
  Regression (attested-Pfad wieder unakzeptiert) fehlschlagen lässt,
- Bestätigung, dass der bestehende `PACKAGE_RELATIVE_PATH` weiterhin
  akzeptiert bleibt (kein Verlust bestehender Abdeckung).

Nicht im Scope liegen:

- Änderung am memfd-Upload-Verhalten, an der Sealed-Toolchain oder am
  Node-Runtime-Integrity-Preloader,
- Änderung an `build_spfx_site_deployment_plan`-Default oder am
  BFF-Aktivierungsfluss,
- neue Graph-Berechtigungen, Secrets, Zertifikate oder Tenant-Writes im
  Rahmen des Code-Fixes,
- Änderung an der Daten-Plane oder an `m365 spo`-Nutzung außerhalb der
  bestehenden Control-Plane-Allowlist,
- Live-Deployment-Nachweis (bleibt Owner-gated und separat).

## Randbedingungen

- Die Allowlist darf keine Sicherheitsgrenze schwächen: der Pfad muss absolut
  sein, darf kein `..` enthalten und muss mit dem festen Suffix enden; nur
  regular Files sind zulässig.
- Der attested-Pfad besteht die bestehende Plan-Validierung
  (`_validate_plan`, `_validate_control_plane_plan_binding`,
  `verify_package_sha256`) bereits — nur die Runner-Allowlist blockt.
- memfd-Upload ist durch Past-Evidence bewiesen und bleibt unverändert.
- Keine realen Secrets, keine Mandatsdaten, keine Tenant-Writes im Fix.

## Design-Entscheidungen

- **A1 (freigegeben):** Allowlist um den attested-Pfad erweitern. Die
  erwartete Suffix-Prüfung wird um die attested-Form
  (`assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg`) ergänzt,
  ohne die `PACKAGE_RELATIVE_PATH`-Form aufzugeben. Dies ist intent-treu mit
  dem Code-Kommentar „The standalone tenant deployment is bound to the
  reviewed, reproducible package artifact."
- Alternativ A2 (Materialisieren am spfx-Pfad) und A3 (Default zurück auf
  spfx-Pfad) wurden abgewogen und verworfen: A2 schreibt in den Workspace und
  widerspricht dem attested-Intent; A3 bricht den dokumentierten
  Standalone-Deploy-Intent und verlagert Verantwortung auf den Build-Schritt.

## Risiken

- **Gering:** die Allowlist-Oberfläche wächst minimal um eine zweite
  akzeptierte Pfadform; die harten Checks bleiben erhalten.
- **Kein memfd-Risiko:** Upload-Verhalten bleibt unverändert und ist bewiesen.
- **Keine Datenschutz-/Secret-Risiken:** Fix berührt keine Secrets, Mandatsdaten
  oder Tenant-Writes.

## Akzeptanzkriterien

- **AC-001:** `m365 spo app add --filePath <attested-pfad>` (absoluter Pfad
  auf `assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg`) wird durch
  `_matches_spfx_app_add` akzeptiert; `_is_bound_package_path` liefert `True`
  für den attested-Pfad und `False` für Pfade mit `..` oder falschem Suffix.
- **AC-002:** `m365 spo app add --filePath <spfx-pfad>` (Suffix
  `spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg`) bleibt
  akzeptiert (kein Verlust bestehender Abdeckung).
- **AC-003:** Ein Regression-Test deckt beide Pfadformen ab und schlägt fehl,
  sobald der attested-Pfad erneut unakzeptiert wird.
- **AC-004:** `python3 -m unittest tests.test_m365_mvp_test_environment_deploy
  tests.test_m365_spfx_site_deployment` ist grün;
  `python3 scripts/validate_spec_traceability.py` ist grün;
  `python3 scripts/nac.py doctor --profile strict` ist grün.
- **AC-005 (optional, Owner-gated, nicht Teil des Code-Fixes):** Nach
  CLI-Login und Owner-Freigabe läuft ein versiegelter
  `test-environment-deploy --owner-approved` gegen `notary_team_01` durch
  `add_or_overwrite_tenant_app` (Control-Plane-Evidence PASSED).

## Nicht-Ziele

- Kein Fix am memfd-Upload, an der Sealed-Toolchain oder am Node-Runtime-Preloader.
- Keine Änderung am Default von `build_spfx_site_deployment_plan`.
- Kein Live-Deployment als Teil des Code-Fixes.
- Keine Erweiterung der `m365 spo`-Allowlist über die bestehende
  Control-Plane-Befehlsform hinaus.
