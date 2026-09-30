# BFF-503-Stufenbeleg für die Teams-Testregisterkarte

Status: Repository-Umsetzung; kein Deployment und keine bestätigte Live-Ursache.

Führendes Issue: [#762](https://github.com/notariat8/NaC/issues/762). Die sichtbare Meldung „Arbeitsbereich ist derzeit nicht verfügbar“ beweist nur einen fehlgeschlagenen Abruf, nicht dessen serverseitige Ursache.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: bff-503-stage-diagnostic
leading_issue: https://github.com/notariat8/NaC/issues/762
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-09-30-bff-503-stage-diagnostic.md
review_gates:
  - Privacy
  - Secrets
  - External Service
affected_artifacts:
  - src/nac_bff/workbench_endpoint.py
  - src/nac_bff/fastapi_adapter.py
  - src/nac_bff/composition.py
  - tests/test_nac_bff_workbench_endpoint.py
  - tests/test_nac_bff_azure_function_host.py
acceptance_ids:
  - AC-762-01
  - AC-762-02
  - AC-762-03
validation_commands:
  - python -m unittest tests.test_nac_bff_workbench_endpoint tests.test_nac_bff_azure_function_host
  - python scripts/validate_spec_traceability.py
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Entscheidung

Der bestehende BFF gibt dem Client weiterhin nur die neutrale 503-Antwort. Ausschließlich im internen Serverlog wird bei einem 503 eine feste, nicht vom Request stammende Stufenkennung geschrieben: Budget, Uhr, Graph-Anfrage, Graph-Antwort, unerwarteter Graph-Fehler, ungültiges Graph-Ergebnis, BPMN-Asset, Projektion, Request-Timeout oder unerwartete HTTP-Grenze. Weder Ausnahmetext noch Token, Objekt-ID, Korrelationskennung, Listeninhalt oder Nutzerdaten gelangen in diesen Eintrag. Ein Loggerfehler verändert die neutrale Antwort nicht.

Das ist ein eng begrenzter Diagnose-Fix, **keine** behauptete Behebung des Teams-503. Ein realer Ursachenbeleg erfordert später einen separat freigegebenen BFF-Release und einen kontrollierten Test. Ein zusätzlicher Clientbeleg oder eine neue Telemetrie-Infrastruktur wird nicht eingeführt.

## Akzeptanz

- **AC-762-01:** Jeder erfasste 503-Pfad schreibt höchstens eine feste Stufe; 200, 401 und 403 schreiben keine 503-Stufe. Die alte HTTP-Antwort bleibt unverändert.
- **AC-762-02:** Sensible Ausnahmedetails sind weder in HTTP-Antworten noch in internen 503-Stufen enthalten; ungültige Stufen werden verworfen.
- **AC-762-03:** Synthetische Negativtests für Graph, BPMN, Projektion, Budget, Uhr und HTTP-Grenze bestehen; kein Microsoft-Zugriff oder Deployment ist Bestandteil dieser Änderung.
