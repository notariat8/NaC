# Customer-Centric DNS Success Page

Date: 2026-06-10

Issue: https://github.com/notariat8/NaC/issues/81

## Decision

After a successful domain verification, the public DNS check page is presented
as a setup status page, not as a technical diagnostics endpoint. The new
customer must understand:

1. The domain is confirmed.
2. The provided email address is checked for setup.
3. An invitation is sent only after approval.
4. No matter data, deeds, IDs, files or business values are collected.

## Customer View

The page uses only the product name `notariat8`. Internal repository,
provider, platform and role terms stay out of the customer view. In
particular, the customer page must not show terms such as `www-n8`, `NaC`,
`Oracle`, `OCI`, `Admin-Queue`, `Tenant-Slug` or internal roles.

The page visibly reflects the submitted information:

- domain,
- email address of the responsible person,
- domain verification status,
- invitation status.

This makes clear that notariat8 does not infer the email address, but checks
the value provided by the customer.

## Navigation

After a successful DNS check, `Einrichtungsstatus öffnen` is the primary next
step. `Erneut prüfen` remains available as a secondary action. The previous
wording `Domain-Readiness öffnen` is removed from the customer view because it
reads like internal product or process language.

## Technical Evidence

The DNS TXT record remains visible, but under `Technischer Nachweis`. It is no
longer the primary message of the page. Diagnostics and raw data remain
reserved for the internal view.

## Boundaries

- No automatic invitation in this step.
- No productive identity or infrastructure write.
- No secret, token or credential in HTML, Git, chat or logs.
- No provider or cloud hint in the customer view.
- No matter data in the public onboarding path.

## Acceptance

- The customer page names the domain and the email address of the responsible
  person.
- The customer page shows `Einrichtungsstatus öffnen`.
- The customer page explains the next steps as email check, approval and later
  invitation.
- The customer page shows `Technischer Nachweis` instead of a dominant DNS
  diagnostics section.
- The customer page contains no internal terms or provider hints.
- Existing internal admin and diagnostics views remain unchanged.
