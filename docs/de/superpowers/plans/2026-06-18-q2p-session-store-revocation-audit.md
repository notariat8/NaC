# Q2P Session-Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Server-seitiger Session-Store-, Widerrufs- und Audit-Vertrag für die bestehende notariat8 OIDC-Session-Boundary.

**Architecture:** `validate_session_cookie` bleibt abwärtskompatibel. Wenn ein `session_store` übergeben wird, muss der Store-Eintrag aktiv, nicht widerrufen und nicht abgelaufen sein; sonst bleibt der Startstatus geschlossen.

**Tech Stack:** Python stdlib, unittest, bestehende NaC Identity/Web-Module.

---

### Task 1: Contract und rote Tests

**Files:**
- Modify: `tests/test_oci_tenant_identity.py`
- Modify: `workflows/contracts/oci-tenant-identity.contract.json`

- [x] Schreibe Contract-Erwartungen für `server_session_store_in_contract_slice`, Widerruf, Audit und token-/claim-freien Store.
- [x] Schreibe Tests für aktive Store-Validierung.
- [x] Schreibe Tests für missing/revoked/expired Store-Fail-Closed.
- [x] Führe die Tests rot aus.

### Task 2: Minimale Implementierung

**Files:**
- Modify: `src/nac_identity/oidc_session.py`

- [x] Erweitere `validate_session_cookie` um optionale `session_store`- und `audit_log`-Parameter.
- [x] Validierte Cookie-Sitzungen bleiben ohne Store kompatibel.
- [x] Mit Store ist ein aktiver Store-Eintrag erforderlich.
- [x] Audit-Ereignisse bleiben redacted.

### Task 3: Verifikation und PR

**Files:**
- Modify: focused tests and documentation.

- [x] Führe Focus-, angrenzende Session/Web-Tests und Quality Gate aus.
- [ ] Erstelle Protected PR gegen `main`.
