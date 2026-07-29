# BusinessCaseType Live-Write-Readiness S4e

Status: `S4E_OFFLINE_READINESS`

Issue: [#702](https://github.com/notariat8/NaC/issues/702)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-live-write-readiness-s4e
leading_issue: https://github.com/notariat8/NaC/issues/702
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4E-01
  - AC-S4E-02
  - AC-S4E-03
  - AC-S4E-04
  - AC-S4E-05
  - AC-S4E-06
  - AC-S4E-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_live_write_readiness tests.test_business_case_type_live_write_readiness_cli tests.test_business_case_type_live_write_readiness_contract
  - python3 scripts/validate_business_case_type_live_write_readiness.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Ziel

S4e beschreibt den letzten rein lokalen Prüfpunkt vor einer produktiven
Adapterkomposition. Der Slice führt keine Credentials, Providerclients oder
Live-Aufrufe ein. Er macht stattdessen maschinenlesbar sichtbar, welche
gebundenen Adapter und getrennten Identitäten vor einem synthetischen
Live-Write in `notary_team_01` fehlen.

Die CLI bewertet einen vertraglich gepinnten Repository-Snapshot. Sie führt
keine Live-Discovery durch und behauptet insbesondere weder den aktuellen
Entra-Zustand noch eine Live-Freigabe. Erst ein späteres owner-gated Gate darf
die gebundenen Adapter und Identitäten gegen Providerzustand verifizieren.

## Identitätsentscheidung

`NaC M365 Provisioning` bleibt Bootstrap- und Inspection-Identität. Sie darf
keine Geschäftsvorfallsdaten schreiben. Der spätere Write-Pfad benötigt eine
eigene Identität mit exakt Microsoft Graph `Sites.Selected` und Site-Rolle
`write`. Diese Identität, die Provisioning-App und die BFF-UAMI müssen
paarweise verschieden sein. Die BFF-UAMI bleibt bei `Sites.Selected/read`.

## Redigierte Adapterbindungen

Das Readiness-Modell akzeptiert nur SHA-256-Bindungen für:

- Owner-Comment-Verifier und vertrauenswürdige GitHub-CLI,
- Provisioning-Bootstrap und öffentliches Zertifikat,
- Write-Token-Provider und Graph-HTTP-Port,
- Azure-Blob-WORM-Transport, Containerziel, CMK/Encryption Scope und
  gesperrte Immutability Policy.

Rohkennungen, Pfade, Zertifikate, Schlüssel, Token oder Providerantworten
werden weder gelesen noch ausgegeben.

## Status

`S4E_READY_OFFLINE` bedeutet ausschließlich, dass alle produktiven
Adapterbindungen als redigierte Hashes vorliegen und die Funktionstrennung
stimmt. Der Status erteilt keine Live-Freigabe. Fehlt insbesondere die
dedizierte Write-Identität, lautet der Status fail-closed `BLOCKED`.

## Akzeptanzkriterien

- **AC-S4E-01:** Fehlende dedizierte Write-Identität blockiert ohne
  Credential-, Netzwerk- oder Tenant-Aktivität.
- **AC-S4E-02:** Provisioning-, Write- und BFF-Principal sind paarweise
  verschieden; Permission und Site-Rollen sind exakt.
- **AC-S4E-03:** Owner-, Toolchain-, Bootstrap- und Zertifikatsbindungen
  werden ausschließlich als SHA-256 verarbeitet.
- **AC-S4E-04:** WORM-Ziel, CMK/Encryption Scope und Locked Policy werden
  ausschließlich redigiert gebunden.
- **AC-S4E-05:** Secret-, Datei-, HTTP-, DNS-, Graph-, Azure- und
  Tenant-Zähler bleiben null.
- **AC-S4E-06:** Der Slice erstellt oder ändert keine Entra-, SharePoint-,
  Teams-, Azure- oder Credential-Ressource und autorisiert keinen Live-Write.
- **AC-S4E-07:** CLI, Contracts, Validator, Tests, Strict-Gate,
  unabhängiger Review und Protected-PR-Checks bestehen.
