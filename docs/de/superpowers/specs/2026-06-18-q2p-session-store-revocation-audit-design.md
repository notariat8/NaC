# Q2P Session-Store, Widerruf und Audit

Status: Owner-approved Design, Umsetzung per Protected PR.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2p-session-store-revocation-audit
leading_issue: https://github.com/notariat8/NaC/issues/165
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_contract_declares_dry_run_only_boundary tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_requires_active_server_session_record_when_store_is_supplied tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_fails_closed_when_server_session_is_missing_revoked_or_expired
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

**Ziel:** Vor jedem späteren vollständigen Arbeitsbereich oder Mandatszugriff muss eine serverseitige Sitzungskontrolle vorhanden sein. Das Browser-Cookie bleibt kurzlebig und enthält keine Token, Claims, Provider-Details oder Callback-Werte.

## Design

Q2P ergänzt die bestehende OIDC-Session-Boundary um einen optionalen serverseitigen Session-Store-Vertrag. Die bestehende Cookie-Prüfung bleibt für den geschützten Startstatus kompatibel. Sobald ein Session-Store an die Validierung übergeben wird, reicht ein korrekt signiertes Cookie allein nicht mehr aus: Ein aktiver Store-Eintrag ist erforderlich.

Ein Store-Eintrag darf nur sichere Sitzungsmetadaten enthalten: Session-ID, Ausstellungszeit, Ablaufzeit, optionalen Widerrufszeitpunkt und eine Audit-Referenz. Token, Claims, Provider-Details, Callback-Werte und Mandatsdaten sind ausgeschlossen. Fehlende, widerrufene, abgelaufene oder unsichere Store-Einträge führen fail-closed.

Die Audit-Kante protokolliert nur Status, Grund, Prüfzeitpunkt und optionale Audit-Referenz. Sie gibt weder Session-ID noch Cookie-Wert, Token, Claims oder E-Mail-Adressen aus.

## Sicherheitsregeln

- Browser-Cookie bleibt ein signierter, kurzlebiger Zeiger.
- Server-Session-Store ist Pflicht, bevor ein voller Arbeitsbereich oder Mandatszugriff aktiviert wird.
- Widerruf im Store schliesst die Sitzung sofort.
- Audit-Ereignisse sind redacted und enthalten keine vertraulichen Werte.
- Mandatsdaten werden durch Q2P nicht geladen.

## Abnahme

- AC-001: Mit übergebenem Session-Store reicht ein signiertes Cookie nur bei aktivem Store-Eintrag.
- AC-002: Fehlende, widerrufene und abgelaufene Store-Einträge schliessen fail-closed.
- AC-003: Store- und Audit-Ergebnisse geben keine Session-ID, Cookies, Token, Claims, Rollen oder E-Mail-Adressen aus.
- AC-004: Der bestehende geschützte Startstatus bleibt ohne Store-Adapter rückwärtskompatibel.
