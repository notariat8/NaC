# Persistent Onboarding Request And Admin Queue

Date: 2026-06-10

NaC issue: https://github.com/notariat8/NaC/issues/83

NaC adapter issue: https://github.com/notariat8/NaC/issues/85

OCI issue: https://github.com/notariat8/oci-landing-zone/issues/44

## Decision

After successful DNS verification, notariat8 creates a real onboarding request
with a stable `request_id`. This request is the first persistent status in the
new-customer onboarding flow. It replaces static admin-queue previews with a
traceable request lifecycle.

The target persistence layer is OCI ATP. Without a production-configured
store, the public POST route must not silently write to local files, `/tmp`,
Git or in-memory state. It must fail closed or visibly report that request
submission is not enabled.

## Alternatives

### Not Chosen: Local File Or `/tmp`

A local file would be fast, but it would not be real SaaS operation. It would
not be reliable in Functions, could disappear after cold starts, and would blur
the later target architecture.

### Not Chosen: GitHub Issues As Customer Queue

GitHub is the control and review plane for development and governance, not the
production customer-onboarding database. Customer email addresses and lifecycle
state do not belong in GitHub Issues as productive app state.

### Chosen: ATP-Backed Request Store

ATP is the target store for `tenant_registry` and `onboarding_requests`. NaC
talks to this store through a small repository contract. The Function uses only
server-side configuration and later Vault/resource-principal-capable secrets.
No credentials are stored in Git, chat, query parameters or HTML.

## Customer Workflow

1. The customer opens the DNS success page.
2. The customer sees the domain, responsible email address and status.
3. The customer clicks `Einrichtung anfragen`.
4. NaC validates domain, tenant reference, email address and DNS status.
5. NaC creates a stable `request_id`.
6. The customer sees `Anfrage eingegangen`, `E-Mail-Prüfung ausstehend` and
   `Einladung noch nicht versendet`.

The customer view uses only `notariat8` as the product name. It shows no OCI,
Oracle, NaC-internal, admin-queue, tenant-slug or provider details.

## SaaS Admin Workflow

1. `/admin/onboarding` lists real onboarding requests from the store.
2. Each request shows `request_id`, domain, responsible email address,
   DNS status, request status and next owner step.
3. The SaaS admin can prepare a review artifact from the request.
4. Productive identity, compartment, ATP or invitation writes remain bound to
   separate Owner Apply gates.

## Request Contract

Minimal request:

```json
{
  "schema_version": "nac.onboarding-request/v0.1",
  "request_id": "onr_...",
  "domain": "kanzlei-notariat.example",
  "tenant_slug": "kanzlei-notariat",
  "admin_email": "verwaltung@kanzlei-notariat.example",
  "dns_status": "verified",
  "request_status": "submitted",
  "invitation_status": "not_sent",
  "created_at": "2026-06-10T00:00:00Z",
  "updated_at": "2026-06-10T00:00:00Z"
}
```

`request_id` is not secret. It is a stable, auditable identifier and may appear
in links or admin views. It must not contain an email address, secret domain
hash or credentials.

## API Boundary

The Functions runtime remains GET/HEAD-only by default. Exactly one new POST
exception is allowed:

- `POST /onboarding/requests`

This route accepts only domain, tenant reference and responsible email address.
It accepts no matter data, files, IDs, business values, API keys or tokens.

If no store is configured, the route responds with a clear service status and
writes nothing.

## Store Boundary

The NaC code defines a small store contract:

- `create_request(payload)`,
- `get_request(request_id)`,
- `list_requests(limit)`.

The productive adapter is ATP-backed. A test adapter may be used only in unit
tests and must not be enabled in the live Function configuration.

## ATP Target Model

First tables:

- `tenant_registry`
- `onboarding_requests`

Required fields in `onboarding_requests`:

- `request_id`
- `tenant_id`
- `tenant_slug`
- `domain`
- `admin_email`
- `dns_status`
- `request_status`
- `invitation_status`
- `created_at`
- `updated_at`
- `created_by_surface`

Later extensions for audit events, contract status, DPA status and apply
artifacts must be possible without a schema break.

## M2 mTLS Wallet Runtime

The first productive ATP instance requires mTLS. NaC keeps that boundary and
does not switch to walletless connectivity merely to simplify the first apply.

At runtime, the Function reads only through Resource Principal:

- the database password as a Vault secret,
- the wallet password as a Vault secret,
- the ATP wallet zip from a private KMS-encrypted Object Storage bucket.

Secret contents must not be stored in Git, chat, query parameters, HTML,
Resource Manager variables or Function config. Function config contains only
secret OCIDs and non-secret connection parameters. The wallet is extracted into
the ephemeral Function filesystem, paths are not rendered into customer HTML,
and there is no local productive persistence fallback.

If the wallet object, wallet password secret, or Resource Principal permission
is missing, the store remains fail-closed or returns
`onboarding_request_store_unavailable`. A half-enabled state must not persist a
request.

## Security Boundaries

- No matter data in onboarding requests.
- No credentials in requests, HTML, query string, logs or Git.
- No productive local fallback store.
- No productive identity apply in this slice.
- No email sending in this slice.
- No end-customer access to OCI Console.

## Acceptance

- The customer page offers `Einrichtung anfragen` after DNS success.
- With the store disabled, `POST /onboarding/requests` writes nothing and
  fails closed.
- Tests prove that no internal or provider terms appear in customer HTML.
- The admin queue can render real request objects.
- The ATP infrastructure track is separate and Apply-gated.
- For mTLS ATP, the Function can extract wallet material from Object Storage
  ephemerally without writing secret values to Git, HTML, query parameters or
  Function config.
