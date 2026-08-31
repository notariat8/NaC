# Plan — Versiegelte Tenant-Deploy-Allowlist für attested SPFx-Paketpfad

Status: `IMPLEMENTED_OFFLINE`

Datum: 30. August 2026
Spec: [2026-08-30-sealed-tenant-deploy-attested-package-allowlist-design.md](../specs/2026-08-30-sealed-tenant-deploy-attested-package-allowlist-design.md)
Führendes Issue: [#740](https://github.com/notariat8/NaC/issues/740)
Delivery Mode: Protected PR
Risk Gate: None (lokale Allowlist + Tests; kein Secret, kein Tenant-Write im Fix)

## Zweck

Umsetzung des freigegebenen Designs **A1**: die Runner-Allowlist der versiegelten
`test-environment-deploy`-Control-Plane so erweitern, dass neben der isolierten
BFF-Build-Ausgabe (`PACKAGE_RELATIVE_PATH`) auch der atteste Paketpfad
(`ATTESTED_PACKAGE_RELATIVE_PATH`) als gebundenes Artefakt für
`m365 spo app add --filePath` akzeptiert wird — ohne die Sicherheitsgrenze zu schwächen.

## Änderungen

- `src/nac_m365_graph/mvp_test_environment_deploy.py`:
  - `ATTESTED_PACKAGE_RELATIVE_PATH` zusätzlich importieren,
  - `_is_bound_package_path` um die atteste Pfadform
    `assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg` ergänzen,
    **nur** für das gebundene sppkg (`filename == PACKAGE_NAME`), damit die
    zip/publish-Allowlist-Formen nicht ausgeweitet werden,
  - harte Checks bleiben: absolut, kein `..`, fester Suffix, regular File
    (via Plan-Validierung),
  - Intent-Kommentar in `_matches_spfx_app_add` (akzeptiert beide Formen via
    `_is_bound_package_path`, kein Tail-Change nötig).
- `tests/test_m365_mvp_test_environment_deploy.py`:
  - Import von `_is_bound_package_path` und `_matches_spfx_app_add`,
  - `test_spfx_app_add_allowlist_accepts_attested_and_spfx_package_paths`
    (Prädikate, beide Pfadformen + Negativfälle `..`/falscher Suffix/relativ,
    keine Ausweitung auf zip),
  - `test_m365_bound_artifact_accepts_attested_package_path` (sealed Runner
    End-to-End, memfd-Basename `nac-bpmn-viewer-715.sppkg`).

## Validierung

```bash
graft build
python3 scripts/validate_graft_context_layer.py
PYTHONPATH=src python3 -m unittest tests.test_m365_mvp_test_environment_deploy tests.test_m365_spfx_site_deployment
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
python3 scripts/nac.py doctor --profile strict
```

## Umsetzungsstand

A1 ist in der Fortsetzungs-Session (2026-08-30) bereits umgesetzt und lokal
validiert (89 betroffene Unittests OK, volle Suite 2763 OK, `graft check`
PASSED, `nac doctor --profile strict` exit 0, Diagnose-Reproduktion zeigt
`_matches_spfx_app_add` nun `True` für den attested-Pfad). Code und Tests bleiben
uncommitted, bis das führende Issue existiert; danach gemeinsamer Commit auf
Feature-Branch `fix/sealed-tenant-deploy-attested-package-allowlist`.

## Guardrails

- Keine Ausweitung der `m365 spo`-Allowlist über die bestehende Control-Plane-Befehlsform hinaus.
- Kein memfd- oder Sealed-Toolchain-Change.
- Keine Secrets, keine Mandatsdaten, keine Tenant-Writes im Fix.
- „Fertig" erst, wenn `nac doctor --profile strict` frisch grün, HEAD dem
  GitHub-Zielstand entspricht, Workspace sauber und die drei Remote-Checks
  (`secret-scan`, `privacy-lint`, `quality-gate`) grün sind.
