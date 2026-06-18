# Q2O Geschützten Startstatus aktivieren

Status: Owner-approved Design, Umsetzung per Protected PR.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2o-protected-start-status-activation
leading_issue: https://github.com/notariat8/NaC/issues/166
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_auth_callback_sets_secure_session_cookie_after_verified_role_gate tests.test_nac_web.NaCLocalWebTests.test_auth_callback_keeps_protected_startstatus_closed_without_session_cookie tests.test_nac_web.NaCLocalWebTests.test_workspace_opens_protected_start_page_with_valid_session_cookie_only tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_dispatches_workspace_as_protected_stateful_get_route
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

Owner-Freigabe:

> Q2O Ansatz A: after Q2N callback-log evidence is complete, enable only the protected notariat8 start/status page for verified server-side sessions; no full workspace, no mandate data, fail-closed, protected PR, release gate first, no OCI writes without separate Owner Apply Approval.

## Grenze

Q2O aktiviert nach erfolgreicher serverseitiger Anmeldung nur den Übergang zur
geschützten notariat8 Start-/Statusseite. Die Aktivierung setzt ein signiertes
Session-Cookie voraus, das erst nach gültigem State, serverseitigem Token-Austausch,
geprüften Claims und positivem notariat8-Rollengate ausgegeben wird.

Dieser Slice öffnet nicht:

- den vollständigen Arbeitsbereich,
- Mandatsdaten,
- Token-, Claim-, Nonce-, Callback-, Provider-, Secret- oder Cookie-Werte,
- OCI-Schreibaktionen.

Fehlt das Session-Cookie oder kann es nicht geprüft werden, bleibt der Startstatus
geschlossen.

## Abnahme

- AC-001: Der Auth-Callback zeigt bei gebundener Session "Startstatus freigegeben".
- AC-002: Der Auth-Callback bietet bei gebundener Session einen Link zu `/workspace`.
- AC-003: Ohne gebundene Session bleibt der Startstatus geschlossen und `/workspace`
  wird nicht angeboten.
- AC-004: Die Seiten nennen ausdrücklich, dass keine Mandatsdaten geladen werden.
