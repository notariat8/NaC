# Agentic 4h Evening Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vier Stunden owner-arme NaC-Arbeit vorbereiten, die parallel laufen kann, ohne OCI-Writes, Secret-Lesen, Mandatsdaten oder Vollworkspace-Zugriff.

**Architecture:** Das Paket trennt die Arbeit in unabhängige Lanes, die jeweils einen Protected PR oder ein gebündeltes Owner-Gate erzeugen können. Die Koordination hält GitHub als Single Source of Truth, protokolliert Zeit über das NaC Time Ledger und stoppt nur an Design-, Release-, Apply-, Secret-, destruktiven Git- oder Live-Daten-Gates.

**Tech Stack:** GitHub PRs/Issues/Projects, NaC Python Unit Tests, `scripts/quality_gate.py`, `nac time-ledger`, OCI Read-only-CLI-Evidenz soweit bereits freigegeben.

---

## Startfenster

- Vorbereitet um: 2026-06-19 17:12 CEST.
- Geplanter Start: 2026-06-19 17:42 CEST.
- Laufzeitbudget: 4 Stunden.
- Harte Ziel-Endzeit: 2026-06-19 21:42 CEST.
- Codex Thread Wake-up: in dieser Sitzung nicht verfügbar. Wenn der Thread zum Startzeitpunkt inaktiv ist, liegt das Paket bereit, startet aber nicht selbst.

## Aktive Inputs

- Offener PR: `notariat8/NaC#189`, verpflichtender serverseitiger Session-Store für `/workspace`.
- Zuletzt gelandete Queue: Q2T-Q2V und verwandte Release-Memory-Tracks.
- Bestehende Queue-Referenz: `docs/de/superpowers/plans/2026-06-19-agentic-8h-current-queue.md`.
- Aktuelle Guardrail: keine OCI-Writes, keine Secret-Werte, kein Vollworkspace, keine Mandatsdaten.

## Parallele Lanes

### Lane 1: PR #189 Follow-up und Release-Paket

**Objective:** PR #189 review-ready halten und das naechste Release-Gate erst nach Merge vorbereiten.

**Files:**
- Read: `src/nac_identity/oidc_session.py`
- Read: `src/nac_web/server.py`
- Read: `tests/test_nac_web.py`
- Read: `docs/de/authenticated-webapp-operating-model.md`

- [ ] **Step 1: PR-Status lesen**

Run:

```bash
gh pr view 189 --repo notariat8/NaC --json state,mergeStateStatus,headRefOid,baseRefName,headRefName,url
gh pr checks 189 --repo notariat8/NaC
```

Expected:

- PR ist offen bis Owner-Merge.
- Checks sind gruen, bevor Review angefragt wird.

- [ ] **Step 2: Kein Release vor Merge**

Rule:

```text
If PR #189 is not merged, do not request OCI DevOps build, Resource Manager variable refresh, or release approval.
```

- [ ] **Step 3: Post-Merge Release-Gate vorbereiten**

Wenn PR #189 gemerged ist, Merge-Commit holen:

```bash
gh pr view 189 --repo notariat8/NaC --json mergeCommit
```

Dieses Gate mit echtem Commit vorbereiten:

```text
Owner Release Approval for PR189 OCI DevOps build and Function deploy of notariat8/NaC@<merge_commit_sha> with NAC_RELEASE_COMMIT=<merge_commit_sha>
```

Vor dem Release stoppen.

### Lane 2: Workspace/Auth Track B Design Prep

**Objective:** Den nächsten Protected PR für explizite Role/Case/Purpose-Gate-Reason-Classes und redigierten Audit-Vertrag vorbereiten, ohne neuen Runtime-Zugriff umzusetzen.

**Files:**
- Read: `src/nac_identity/role_case_gate.py`
- Read: `src/nac_web/server.py`
- Read: `tests/test_nac_web.py`
- Read: `tests/test_oci_tenant_identity.py`
- Modify only after design approval: narrow tests and role/case gate code.

- [ ] **Step 1: Aktuelle Gate-Reasons inspizieren**

Run:

```bash
rg -n "role_missing|tenant_mismatch|case_missing|purpose_missing|four_eyes|evaluate_role_case_gate" src tests docs/en docs/de
```

Expected:

- Aktuelle Gate-Reasons stehen in `src/nac_identity/role_case_gate.py` und im `/workspace` Rendering.

- [ ] **Step 2: Owner Design Gate vorbereiten**

Diesen Gate-Text verwenden:

```text
Owner Design Approval for next Workspace/Auth Track B: formalize the /workspace role-case-purpose gate as a metadata-only authorization contract with explicit reason classes, optional four-eyes requirement, redacted audit evidence, and no exposure of tenant hints, case IDs, session IDs, claims, emails, provider details or mandate content; fail closed, protected PR, no OCI writes.
```

- [ ] **Step 3: Testziele nur vorbereiten**

Testnamen notieren, vor Design Approval nicht implementieren:

```text
tests.test_nac_web.NaCLocalWebTests.test_workspace_redacts_gate_reason_context_values
tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_role_case_gate_returns_explicit_safe_reason_classes
```

Vor Code-Edits stoppen, solange keine Owner Design Approval vorliegt.

### Lane 3: Onboarding Track C Customer Status Prep

**Objective:** Den kunden sichtbaren Onboarding-Status nach Admin-Review nur mit bestehenden sicheren Statusfeldern verbessern.

**Files:**
- Read: `src/nac_identity/onboarding_requests.py`
- Read: `src/nac_web/server.py`
- Read: `tests/test_nac_web.py`
- Read: `tests/test_onboarding_requests.py`

- [ ] **Step 1: Bestehende Request-Statusfelder inspizieren**

Run:

```bash
rg -n "request_status|invitation_status|review|onboarding/requests|admin/onboarding" src tests docs/en docs/de
```

Expected:

- Bestehende Felder reichen, um kunden sicheren Review-Fortschritt zu zeigen.

- [ ] **Step 2: Owner Design Gate vorbereiten**

Diesen Gate-Text verwenden:

```text
Owner Design Approval for next Onboarding Track C: improve the customer-facing request status page after admin review using only existing request_status and invitation_status fields and customer-safe copy; show that review is documented and invitation remains pending; no customer mail dispatch, no mandate data, no internal provider or admin terminology.
```

- [ ] **Step 3: Stop-Checks vorbereiten**

Nichts umsetzen, was:

```text
- Kundenmail versendet,
- Einladungsversand erzeugt,
- Lifecycle-States ohne Contract hinzufuegt,
- Provider-, OCI-, Admin-, Secret- oder interne Operator-Begriffe für Kunden sichtbar macht.
```

### Lane 4: Hygiene, Baseline und Context Pack

**Objective:** Den 4h-Lauf auditierbar halten und wiederholte Owner-Prompts für Routine-Evidenz vermeiden.

**Files:**
- Read: `docs/en/superpowers/plans/2026-06-19-agentic-8h-current-queue.md`
- Read: `docs/de/superpowers/plans/2026-06-19-agentic-8h-current-queue.md`
- Read: `out/observability/codex-time-ledger.jsonl` only if needed; do not commit output.

- [ ] **Step 1: Time-Ledger-Session starten**

Run:

```bash
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/nac time-ledger add --session-id 2026-06-19-agentic-4h-evening --task "4h evening agentic package" --phase start --category other --notes "Package start; no OCI writes, no secrets, no mandate data."
```

Expected:

- Ledger schreibt nach `out/observability/codex-time-ledger.jsonl`.
- Die Datei bleibt untracked.

- [ ] **Step 2: Baseline Checks**

Run:

```bash
git status --short --branch
git diff --check
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Wenn Socket-Tests in der Sandbox mit `PermissionError` scheitern, denselben Befehl außerhalb der Sandbox als Verifikations-Retry wiederholen, nicht als Produktarbeit.

- [ ] **Step 3: Branch-Hygiene-Audit**

Run:

```bash
git branch --merged main
git branch -r --merged origin/main
```

Nur ein exaktes Cleanup-Gate ausgeben. Keine Branches ohne Owner Approval löschen.

## Gebündeltes Owner-Paket

Am Ende des 4h-Fensters genau ein Paket liefern:

```text
1. PR #189 Status und, falls gemerged, das exakte Release-Gate.
2. Ein empfohlenes Design-Gate: Track B oder Track C, mit Begruendung.
3. Branch-Cleanup-Gate mit exakter Branchliste, falls vorhanden.
4. Verifikationsevidenz und Time-Ledger-Summary.
```

## Harte Stop-Lines

Stoppen vor:

- OCI DevOps Build oder Function Deploy.
- Resource Manager Variable Refresh, Plan oder Apply.
- Secret-Werten, Vault Secret Read oder neuer Secret OCID.
- Branch-Löschung, Force Push, Reset oder destruktiver Git-Aktion.
- Änderung von Live Token Exchange Verhalten.
- Vollworkspace-Zugriff, Mandatsdaten, Dokumentlisten, Uploads oder echte Aktenzugriffe.

## Verifikationsbefehle

Vor Abschluss des Pakets verwenden:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
git diff --check
git status --short --branch
```
