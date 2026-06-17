# Q2J Geschützte Session-Startseite

Status: Owner-approved Design, Umsetzung per Protected PR.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2j-protected-session-start-page
leading_issue: https://github.com/notariat8/NaC/issues/153
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_allows_protected_start_page_without_opening_workspace tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_fails_closed_for_tampered_or_expired_cookie tests.test_nac_web.NaCLocalWebTests.test_workspace_requires_signed_session_cookie tests.test_nac_web.NaCLocalWebTests.test_workspace_opens_protected_start_page_with_valid_session_cookie_only tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_dispatches_workspace_as_protected_stateful_get_route tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_dispatches_workspace_fail_closed_without_cookie
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

Owner-Freigabe:

> Q2J Ansatz A: signiertes serverseitiges Session-Cookie prüfen und nur eine geschützte notariat8-Start-/Statusseite öffnen, keine Mandatsdaten, kein vollständiger Arbeitsbereich, fail-closed, Protected PR, keine OCI-Writes.

## Grenze

Q2J prüft das signierte `__Host-nac_session`-Cookie, das erst nach gültigem
State, serverseitigem Token-Austausch, geprüften Claims und positivem
notariat8-Rollengate gesetzt wird. Ein gültiges Cookie darf nur `/workspace`
als geschützte Start-/Statusseite öffnen.

Dieser Slice lädt nicht:

- Mandatsdaten,
- den vollständigen Arbeitsbereich,
- Tokens, Claims, Nonces, Callback-Werte, Providerdetails oder Cookie-Werte,
- OCI-Schreibaktionen.

Fehlende, manipulierte, abgelaufene oder unkonfigurierte Cookies bleiben
fail-closed.

## Abnahme

- AC-001: Fehlendes Session-Cookie führt zur Anmeldeseite.
- AC-002: Gültiges Session-Cookie führt zur geschützten notariat8-Start-/Statusseite.
- AC-003: Das Ergebnis enthält keine Token-, Claim-, Nonce-, Callback-, Provider-,
  Secret- oder rohen Cookie-Werte.
- AC-004: Die Seite nennt ausdrücklich, dass keine Mandatsdaten geladen werden.
