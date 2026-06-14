# OIDC-Callback: Nonce-Gebundener State Implementierungsplan

> **Für agentische Worker:** ERFORDERLICHE SUB-SKILL: Nutze superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Schritt für Schritt umzusetzen. Schritte nutzen Checkboxen (`- [ ]`) zur Nachverfolgung.

**Ziel:** Den OIDC-Login-`nonce` in den signierten `state`-Vertrag von notariat8 binden, damit der nächste Q2B-Schnitt ein ID-Token gegen den ursprünglichen Login-Intent prüfen kann, ohne rohe Nonce-Werte in Git, Logs, Browsertext oder öffentliche Callback-Ausgaben zu schreiben.

**Architektur:** `nac_identity.oidc_state` akzeptiert einen optionalen rohen Nonce, speichert nur einen deterministischen Nonce-Hash im signierten State-Payload und gibt nur Nonce-Bindungsmetadaten plus den für serverseitige Prüfung nötigen Hash zurück. `nac_identity.oci_login` erzeugt den Nonce vor dem State und signiert die Nonce-Bindung. `nac_identity.oci_callback` und der Web-Callback halten den Arbeitsbereich geschlossen und zeigen nur sichere Fortschrittsformulierungen.

**Tech Stack:** Nur Python-Standardbibliothek, `unittest`, Lieferung per Protected PR. Dieser Plan enthält keinen OCI-Write.

---

### Task 1: Signierter State trägt Nonce-Bindungsmetadaten

**Files:**
- Modify: `src/nac_identity/oidc_state.py`
- Modify: `tests/test_oci_tenant_identity.py`

- [ ] **Step 1: Failing Test für nonce-gebundenen State schreiben**

Ergänze einen Test, der signierten State mit `tenant_hint`, `signing_key`, `nonce`, festem `now` und TTL baut und danach validiert. Prüfe:

- Validierungsstatus ist `valid`,
- `tenant_hint` bleibt erhalten,
- `nonce_bound` ist `True`,
- ein `nonce_hash` wird für spätere serverseitige ID-Token-Nonce-Prüfung zurückgegeben,
- das serialisierte Validierungsergebnis enthält weder rohen Nonce noch Signing Key.

- [ ] **Step 2: Test für RED laufen lassen**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_signed_state_binds_nonce_without_returning_raw_nonce
```

Expected: FAIL, weil `build_signed_state` noch kein `nonce` akzeptiert.

- [ ] **Step 3: Nonce-Hash-Unterstützung implementieren**

Erweitere `build_signed_state` um `nonce: str | None = None`. Wenn ein Nonce vorhanden ist, speichere `nonce_hash = sha256(nonce).hexdigest()` im signierten Payload. Erweitere `validate_signed_state`, sodass `nonce_bound` und `nonce_hash` nur bei gültigem State zurückgegeben werden. Ältere States ohne Nonce bleiben mit `nonce_bound=False` gültig.

- [ ] **Step 4: State-Tests laufen lassen**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity
```

Expected: OK.

### Task 2: Login-Intent signiert den erzeugten Nonce

**Files:**
- Modify: `src/nac_identity/oci_login.py`
- Modify: `tests/test_oci_tenant_identity.py`
- Modify: `tests/test_nac_web.py`

- [ ] **Step 1: Failing Login-Intent-Tests schreiben**

Ergänze oder verschärfe Tests, sodass die signierte Login-Intent-Validierung beweist:

- `state_binding.nonce_bound` ist `True`,
- Validierung des zurückgegebenen State liefert `nonce_bound=True`,
- der zurückgegebene `nonce_hash` passt zum erzeugten Nonce,
- weder das State-Validierungspayload noch der serialisierte Login-Intent enthalten den Signing Key.

- [ ] **Step 2: Tests für RED laufen lassen**

Run the focused login-intent tests and expect FAIL until `oci_login` signs the nonce.

- [ ] **Step 3: Nonce vor dem State-Signieren erzeugen**

Erzeuge in `build_login_intent` den Nonce vor `build_signed_state`, übergib ihn an den State-Builder und setze `nonce_bound=True` in den Signed-State-Bindungsmetadaten. Der Opaque-State-Fallback bleibt `nonce_bound=False`.

- [ ] **Step 4: Web- und Identity-Tests laufen lassen**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_web
```

Expected: OK.

### Task 3: Callback-Fortschritt zeigt nonce-gebundenen State ohne Arbeitsbereichsöffnung

**Files:**
- Modify: `src/nac_identity/oci_callback.py`
- Modify: `tests/test_oci_tenant_identity.py`
- Modify: `tests/test_nac_web.py`

- [ ] **Step 1: Callback-Tests schreiben**

Ergänze Tests, die beweisen, dass ein Callback mit gültigem nonce-gebundenem State:

- als `received` akzeptiert wird,
- intern `state_validation.nonce_bound=True` berichtet,
- `role_gate.status=closed` hält,
- HTML frei von rohem State, Code, Nonce, Nonce-Hash, Signing Key, Oracle/OCI-Wording und Secrets bleibt.

- [ ] **Step 2: Callback-Tests für RED laufen lassen**

Run the focused new callback tests and expect FAIL until callback result carries nonce-binding metadata safely.

- [ ] **Step 3: Nonce-Metadaten im Callback-Ergebnis normalisieren**

Erweitere `build_auth_callback_result`, sodass `state_validation` `nonce_bound=True` beibehält, aber keinen `nonce_hash` in das browsernahe Ergebnis übernimmt. `role_gate.reason` bleibt `session_not_established`.

- [ ] **Step 4: Callback-Tests laufen lassen**

Run:

```bash
env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity tests.test_nac_web tests.test_oci_functions_adapter
```

Expected: OK.

### Task 4: Quality Gate und PR

**Files:**
- Modify documentation only if acceptance language needs to mention nonce-bound state.

- [ ] **Step 1: Strengen Quality Gate laufen lassen**

Run:

```bash
env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: PASSED.

- [ ] **Step 2: Commit und Protected PR öffnen**

Commit auf `agent/128-nonce-bound-state`, Push, PR zu Issue #128 öffnen, Labels/Project-Felder setzen und Runtime-Deployment für ein separates Owner Release Approval offenlassen.
