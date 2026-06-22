# Notarkammer Demo 2026-06: XNP Preflight and Audit Trail

Status: owner-free Protected PR track for the 1h live demo.

This checklist is executed before the presentation and kept as demo evidence.
It protects the live demo from ad-hoc debugging, real mandate data, local
card-reader or XNP improvisation and unapproved operating actions. All examples
remain synthetic; the explicit boundary is: no real mandate data, no secrets,
no release, no apply, no runtime change, no cloud change.

## CET/CEST Timeline

All times are local chamber/Berlin time: CET in winter (UTC+1) and CEST in
summer (UTC+2). June 2026 uses CEST; no demo note should use UTC only.

| CET/CEST Time | Goal | Result |
| --- | --- | --- |
| T-03:00 | Open a fresh browser profile, avoid cache, prepare demo tabs. | Five tabs are loaded or marked for fallback. |
| T-02:45 | Check public onboarding, DNS readiness and an existing request-status page by GET only. | Customer journey is presentable or marked for fallback. |
| T-02:30 | Check the local card-reader/SAK path for XNP as a readiness gate. | Evidence shows `ready`, `manual_review` or a Stop-Line. |
| T-02:00 | Check XNP localhost, XNotar exchange folder and XJustiz package boundary. | Only non-sensitive status and hash evidence exists. |
| T-01:45 | Check OIDC login intent, protected start status and workspace gate. | Login stops before workspace unless the demo is approved. |
| T-01:40 | Classify ATP healthcheck status as a store gate. | `enabled`, `disabled`, `unavailable` or `not_checked` without secret output. |
| T-01:30 | Align the 1h demo script with the visible browser and workstation states. | No new storyline is started. |
| T-01:00 | Read the Stop-Lines aloud and finalize browser tab order. | The demo can start without live debugging. |
| T-00:15 | Read-only viewing only, no further changes. | The presentation window remains stable. |

## Command safety

All commands in this preflight may prepare or read only. `curl` examples are
viewing checks. `tenant apply-request` examples must include `--dry-run`.
POST, OCI CLI, productive apply steps, Vault, wallet, ATP and Identity secret
access remain stop-lines and are not executed during the meeting.

## Browser Checks

Run every check in a fresh browser window without a saved session.

1. `https://notariat8.de`
   - Expected: The home page loads and shows no real mandate data.
   - Fallback: Use the already loaded home page; do not deploy live.
2. `https://notariat8.de/prozessmodell.html`
   - Expected: Immobilienkaufvertrag, duration logic and critical path are
     visible.
   - Fallback: Use a local screenshot or an already opened tab.
3. `https://app.notariat8.de/healthz`
   - Expected: The status is short and non-sensitive, for example `ok`.
   - Fallback: Close the health tab and show the fail-closed workspace.
4. `https://app.notariat8.de/login`
   - Expected: Sign-in opens, but no real credentials are entered.
   - Fallback: Do not debug login; switch to the process model and workspace
     boundary.
5. `https://app.notariat8.de/workspace`
   - Expected: Without a valid session, the workspace remains closed.
   - Fallback: Explain exactly this state as the security evidence.

## What Can Be Shown Today

| Track | Demonstrable State | Read-only Check | Fallback |
| --- | --- | --- | --- |
| Public Onboarding | `https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` shows domain, admin email, DNS guidance and setup status without mandate data. | `curl -fsS "https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example" >/tmp/nac-onboarding-readiness.html` | Show an already loaded tab; submit no request. |
| DNS Check | `https://app.notariat8.de/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` shows the expected TXT record and current status. | `python scripts/nac.py tenant dns-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --format json` | If DNS is not `verified`, explain `pending`/`mismatch` as normal setup status. |
| Request Status | An existing request can be shown via `/onboarding/requests/<request_id>?audience=customer` as a status page only. | `curl -fsS "https://app.notariat8.de/onboarding/requests/onr_demo_20260621_100000?audience=customer" >/tmp/nac-request-status.html` | If the store is disabled or the ID is unknown, explain `not found`/`unavailable` as the ATP gate. |
| OIDC Login To Protected Start | `/login?tenant_hint=notariat-musterstadt` and `/api/tenant/login-intent?tenant_hint=notariat-musterstadt` show the start of the login flow without credentials. | `curl -fsS "https://app.notariat8.de/api/tenant/login-intent?tenant_hint=notariat-musterstadt" >/tmp/nac-login-intent.json` | Do not continue login; show protected start status. |
| Workspace Metadata-only Gate | `/workspace` remains closed without an approved session and shows metadata status only, no matter file. | `curl -i "https://app.notariat8.de/workspace"` expects `401` or closed HTML containing `Keine Mandatsdaten geladen`. | Explain fail-closed as the security evidence. |
| BPMN Process Model | Immobilienkaufvertrag is visible and validatable as a BPMN/process model. | `python scripts/nac.py bpmn validate` and `python scripts/nac.py bpmn show immobilienkaufvertrag --format text` | Use the public process-model page or screenshot. |
| ATP Healthcheck Status | ATP is only the store gate for onboarding requests; healthcheck output must not expose wallet, secret or DSN values. | `python scripts/nac.py tenant customer-plan --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --saas-admin-email saas-owner@example.com --format json` shows `shared_atp_with_tenant_id`; `/healthz` shows runtime status only. | For `onboarding_request_store_disabled` or `onboarding_request_store_unavailable`, do not analyze ATP live; mark the status as a demo gate. |
| Apply/Provisioning Status | Only review artifacts exist; no OCI write is performed. | `python scripts/nac.py tenant apply-request --tenant-slug kanzlei-notariat --domain kanzlei-notariat.example --admin-email admin@kanzlei-notariat.example --admin-display-name "Admin Notariat" --identity-domain-url https://idcs.example.invalid --identity-domain-id ocid1.domain.oc1.example --dns-verified --owner-approval-id DEMO-OWNER --audit-event-id DEMO-AUDIT --rollback-plan-id DEMO-ROLLBACK --dry-run --format json` | If a gate is missing, explain the blocker; execute no apply. |

All `curl` examples are GET/HEAD-style viewing checks. During the meeting,
submit no forms, run no POST requests, run no OCI CLI, and open no Vault,
wallet, ATP or Identity secrets.

## XNP and Card-Reader Gates

These gates may only be checked locally on the approved workstation. NaC does
not control XNP, card readers, SAK lite, secureFramework or PIN entry from the
cloud.

| Gate | Expected | Evidence |
| --- | --- | --- |
| BNotK card and card reader | Security-class-3 reader is locally available; PIN entry happens only on the reader or in the local certified component. | `nac-cyberjack-rfid` readiness without PIN, card data or raw attributes. |
| RFID for BNotK chip-card path | Contactless path is disabled unless a separate contactless use case is approved. | Manual attestation or local readiness status. |
| PC/SC, SAK lite or XNP card path | Driver, PC/SC and card path are locally plausible. | Minimized status list; no system secrets. |
| XNP localhost | XNP is reachable only locally; allowed port range remains `12774` through `12784`. | Host, port range and reachability status; no API key, no login token. |
| Local XNP sign-in | User role and official-activity context are confirmed locally only. | Yes/no attestation; no session values. |
| XNotar module | For register cases, the exchange folder is known and writable only after owner approval. | Path status as hash or placeholder; no document contents. |
| XJustiz package boundary | Package structure is explained only synthetically or with an empty test package. | Schema/structure status; no deed, UVZ, VVZ or register contents. |

## Audit Trail

The demo audit trail consists of a Protected PR, test output and minimized
evidence artifacts. It is not an operating journal and not a mandate file.

- Protected PR contains documentation and tests only.
- Evidence IDs may be synthetic, for example `DEMO-XNP-2026-06-001`.
- Timestamp, commit SHA, branch and test result are documented.
- Paths, ports and reader fingerprints are hashed or described as status only.
- No PIN, API key, login token, raw card data or deed content is stored in Git,
  PR comments or LLM context.
- Every deviation is marked as `ready`, `manual_review` or `blocked`.

## Fallback Decisions

| Situation | Decision |
| --- | --- |
| Public page is slow, process-model tab is present | Switch to the existing tab and say: "We are showing the checked demo view." |
| Login takes longer than two minutes | Do not wait; show the workspace fail-closed. |
| Card reader, PC/SC, SAK lite or secureFramework is unclear | Do not show the XNP/card path; explain only the preflight gate and Stop-Line. |
| XNP localhost is not reachable | Do not search ports during the meeting; document status as `manual_review` or `blocked`. |
| XNotar exchange folder or XJustiz structure is not safely bounded | Open no package; explain only the synthetic package boundary. |
| Local editor is unavailable | Use the public process-model page and mention GitHub PRs only as governance evidence. |
| Network is unstable | Open no new tabs; use only loaded demo tabs. |
| Public onboarding request status is unavailable | Do not debug ATP; show setup status as `unavailable` and fall back to public onboarding/DNS. |
| ATP healthcheck is `disabled` or `unavailable` | Open no secrets or wallets; explain the status as the store gate and stay with the BPMN/workspace path. |
| OIDC login intent returns only JSON or an error | Do not explain it live; show `/login?tenant_hint=notariat-musterstadt` or the closed workspace. |
| Workspace shows metadata status only | That is expected: protected start yes, full workspace no. |

## Stop-Lines

- Stop-Line: "We are not debugging live; the demo shows the checked process
  path."
- Stop-Line: "Without a session, the workspace remains closed. That is the
  intended security evidence here."
- Stop-Line: "XNP, XNotar and XJustiz remain local and are shown only when card
  path, role and evidence are green beforehand."
- Stop-Line: "For the chamber presentation, we use synthetic demo data only."
- Stop-Line: "This demo contains no release, apply, runtime or cloud action."

## Owner-Gates

These points remain open Owner-Gates and are not decided by the owner-free
track:

- Approval of the final 1h storyline by the demo owner.
- Approval on whether to show a real login during the meeting or only the
  closed workspace.
- Approval on whether a local XNP workstation is shown at all.
- Approval of the final browser window immediately before start.
- Merge decision for this protected PR.

## PR Track

- Branch: `agent/notarkammer-demo-preflight-audit`.
- Scope: only `docs/de/demo/`, `docs/en/demo/` and `tests/`.
- Checks: Language Parity, Documentation Links and Strict Quality Gate.
- No OCI, runtime, release, apply or infrastructure changes.
- Do not use real person, matter, deed, identity, register or property data.
