# Q2H Claim-Grenze Und Rollengate-Vertrag

Status: freigegeben für Issue #147.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2h-claim-boundary-role-gate-contract
leading_issue: https://github.com/notariat8/NaC/issues/147
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_auth_callback_result_marks_verified_claims_forwarded_to_role_gate_without_exposure tests.test_nac_web.NaCLocalWebTests.test_auth_callback_shows_role_gate_confirmed_without_opening_workspace
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

## Ziel

Q2H macht die interne Grenze zwischen serverseitig verifizierten OIDC-Claims
und dem notariat8-Rollengate explizit. Der Callback darf verified Claims nur
intern an das Rollengate weitergeben. Browsernahe Ergebnisse dürfen keine
Claims, Tokens, Nonces, Providerdetails, Secret-Referenzen oder Callback-Werte
enthalten.

## Scope

- `nac.oidc-claim-boundary/v0.1` als redigierter Vertragsteil.
- Rollengate-Entscheidung bleibt fail-closed bei fehlenden, unvollständigen
  oder nicht verifizierten Claims.
- Die Callback-Seite darf anzeigen, dass die Rollenprüfung bestätigt wurde.
- Kein Session-Cookie, keine Workspace-Öffnung und keine Mandatsdaten in
  diesem Slice.

## Ausdrücklich Nicht Im Scope

- Keine OCI-Schreibaktion.
- Kein Live-Test mit echten Benutzer-Credentials.
- Keine produktive Session-Aktivierung.
- Keine Öffnung eines geschützten Arbeitsbereichs.

## Akzeptanz

- AC-001: Der Auth-Callback-Vertrag enthält einen redigierten
  `nac.oidc-claim-boundary/v0.1`-Abschnitt.
- AC-002: Verifizierte Claims werden intern als an das Rollengate übergeben
  markiert, ohne Claim- oder Token-Werte in öffentlichen Ergebnissen
  auszugeben.
- AC-003: Das Rollengate bleibt geschlossen, wenn Claims fehlen, unvollständig
  oder nicht verifiziert sind.
- AC-004: Die Callback-Seite darf eine bestätigte Rollenprüfung anzeigen,
  öffnet aber keinen Arbeitsbereich und setzt kein Session-Cookie.
