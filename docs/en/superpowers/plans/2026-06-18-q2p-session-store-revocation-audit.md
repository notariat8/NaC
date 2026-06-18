# Q2P Session Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a server-side session-store, revocation, and audit contract to the existing notariat8 OIDC session boundary.

**Architecture:** `validate_session_cookie` remains backward compatible. When a `session_store` is supplied, the store record must be active, not revoked, and not expired; otherwise the protected start status remains closed.

**Tech Stack:** Python stdlib, unittest, existing NaC identity/web modules.

---

### Task 1: Contract and Red Tests

**Files:**
- Modify: `tests/test_oci_tenant_identity.py`
- Modify: `workflows/contracts/oci-tenant-identity.contract.json`

- [x] Add contract expectations for `server_session_store_in_contract_slice`, revocation, audit, and token-/claim-free store records.
- [x] Add tests for active store validation.
- [x] Add tests for missing/revoked/expired store fail-closed behavior.
- [x] Run the tests red.

### Task 2: Minimal Implementation

**Files:**
- Modify: `src/nac_identity/oidc_session.py`

- [x] Extend `validate_session_cookie` with optional `session_store` and `audit_log` parameters.
- [x] Keep validated cookie sessions backward compatible without a store.
- [x] Require an active store record when a store is supplied.
- [x] Keep audit events redacted.

### Task 3: Verification and PR

**Files:**
- Modify: focused tests and documentation.

- [x] Run focused tests, adjacent session/web tests, and the quality gate.
- [ ] Open a protected PR against `main`.
