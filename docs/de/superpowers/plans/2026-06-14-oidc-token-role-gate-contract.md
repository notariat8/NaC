# OIDC Token-Claim- und Rollengate-Vertrag Implementierungsplan

> **Für agentische Worker:** ERFORDERLICHE SUB-SKILL: Nutze superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Schritt für Schritt umzusetzen. Schritte nutzen Checkboxen (`- [ ]`) zur Nachverfolgung.

**Ziel:** Einen reinen, lokal testbaren Vertrag für OIDC-Claim-Prüfung und notariat8-Rollengate ergänzen, der ohne Live-Token-Austausch fail-closed entscheidet.

**Architektur:** `nac_identity.oidc_role_gate` nimmt bereits serverseitig verifizierte Claim-Daten und erwartete Callback-Kontexte entgegen. Das Modul prüft Issuer, Audience, Nonce-Bindung und `nac-tenant-admin`, gibt nur sichere Metadaten zurück und öffnet keine Sitzung. `nac_identity.oci_callback` kann diesen Vertrag in einem späteren Q2D-Schnitt nach Token-Exchange/JWT-Prüfung konsumieren.

**Tech Stack:** Python-Standardbibliothek, `unittest`, Protected PR. Dieser Plan enthält keinen OCI-Write und keine Secrets.

---

### Task 1: Reinen Rollen-Gate-Vertrag testgetrieben einführen

**Files:**
- Create: `src/nac_identity/oidc_role_gate.py`
- Modify: `src/nac_identity/__init__.py`
- Modify: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Failing Tests schreiben**

Schreibe Tests für diese Fälle:

- gültige Claims mit passendem `iss`, `aud`, `nonce`, validiertem nonce-gebundenem State und Rolle `nac-tenant-admin` ergeben `status="open"` und `session_allowed=True`,
- fehlende Rolle ergibt `status="closed"` und `reason="role_missing"`,
- falscher Issuer oder falsche Audience schließen mit `issuer_mismatch` oder `audience_mismatch`,
- fehlende oder falsche Nonce-Bindung schließt mit `nonce_not_bound` oder `nonce_mismatch`,
- serialisierte Ergebnisse enthalten keine Roh-Tokens, Codes, States, Nonces, Nonce-Hashes oder Secret-Werte.

- [ ] **Step 2: RED verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_oidc_role_gate_opens_only_for_verified_admin_claims
```

Expected: FAIL, weil `nac_identity.oidc_role_gate` noch nicht existiert.

- [ ] **Step 3: Minimale Implementierung schreiben**

Implementiere `evaluate_oidc_role_gate(...)` mit expliziten erwarteten Werten:

- `expected_issuer`
- `expected_audience`
- `state_validation`
- `claims`
- optional `required_role="nac-tenant-admin"`

Die Funktion gibt einen dict-Vertrag mit `schema_version`, `status`, `reason`,
`role`, `session_allowed` und `guardrails` zurück. Sie darf keine rohen Eingaben
in die Ausgabe übernehmen. Der `nonce`-Claim aus `claims` wird nur gehasht und
gegen `state_validation["nonce_hash"]` verglichen; der Hash wird nicht in das
Ergebnis übernommen.

- [ ] **Step 4: GREEN verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity
```

Expected: OK.

### Task 2: Callback-Vertrag auf künftigen Rollen-Gate-Schritt vorbereiten

**Files:**
- Modify: `src/nac_identity/oci_callback.py`
- Modify: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Failing Test schreiben**

Ergänze einen Test, der zeigt: Nach gültigem State bleibt der Callback zwar
geschlossen, benennt aber den nächsten Schritt als Token-Claim- und Rollen-Gate-
Prüfung statt generischem Session-Aufbau.

- [ ] **Step 2: RED verifizieren**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_auth_callback_result_points_to_token_claim_role_gate_contract
```

Expected: FAIL, weil der Callback noch den alten `next_step` nennt.

- [ ] **Step 3: Minimalen Callback-Text aktualisieren**

Ändere nur den maschinenlesbaren `next_step` auf den Q2C-Vertrag. Browsernahe
Texte bleiben unverändert, damit kein neues Cloud-Verhalten entsteht.

- [ ] **Step 4: Identity- und Web-Tests laufen lassen**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_web tests.test_oci_functions_adapter
```

Expected: OK.

### Task 3: Quality Gate und PR

**Files:**
- All touched files above.

- [ ] **Step 1: Strict Quality Gate laufen lassen**

Run:

```bash
env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: PASSED.

- [ ] **Step 2: Commit, Push und PR**

Committe auf `agent/128-q2c-token-role-gate-contract`, pushe den Branch und
öffne einen Protected PR gegen `main`, verlinkt mit Issue #128. Kein OCI-Apply
und kein Live-Token-Austausch in diesem PR.
