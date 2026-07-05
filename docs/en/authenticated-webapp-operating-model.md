# Authenticated Web-App Operating Model

This target model describes how public static content, real authenticated
users, local notary workstations and mobile participant access should fit
together in NaC.

## Core Decision

GitHub Pages with a Jekyll/Hydra-like theme is useful for public static
content:

- product communication,
- documentation,
- onboarding,
- release and status notes,
- synthetic demos without mandate data.

This static layer must not hold the subject-matter source of truth or real case
data. It is the public reading surface, not the place for login, matter access,
uploads, signing, card readers or approvals.

Real case work for authenticated users needs a separate authenticated web app
or mobile app. That operating edge calls reviewed NaC runtime and backend
services, writes evidence in a controlled way and remains bounded by policies,
roles, contracts and `nac` validation.

## Target Architecture

```mermaid
flowchart TD
    Static["GitHub Pages / Jekyll: static content"] --> Public["public orientation"]
    User["authenticated user"] --> AuthApp["authenticated web app or mobile app"]
    AuthApp --> OciIdp["OCI Identity Domains, OIDC/SCIM, group anchors"]
    OciIdp --> NacRole["NaC role and case gate"]
    NacRole --> Runtime["NaC runtime / backend"]
    Runtime --> DataRepo["separate data repository"]
    Runtime --> Storage["object store, database blob or OneDrive"]
    Runtime --> Audit["audit, hash, purpose, expiry, revocation"]
    Workstation --> O365["Office 365 / Microsoft 365 client layer"]
    O365 --> OneDrive["OneDrive / SharePoint / Outlook / Teams"]
    O365 --> AgentRegistry["Microsoft Agent 365 Agent Registry"]
    O365 --> M365Mcp["Microsoft 365 MCP servers through Microsoft Graph"]
    M365Mcp --> AiQ["NVIDIA AI-Q / NeMo Agent Toolkit"]
    AiQ --> Runtime
    Workstation["local notary workstation"] --> Card["card reader, XNP, eID bridge"]
    Card --> Runtime
```

Office 365 is mandatory on the client side. For NaC, that does not mean the
SaaS identity layer or the current OCI deployment changes. Office 365 is the
mandatory workstation, document, calendar, communication and collaboration
layer for the notary office; NaC may therefore plan integrations with OneDrive,
SharePoint, Outlook, Teams and future Microsoft 365 features, while every
access path remains bounded by NaC roles, matter binding, purpose binding,
audit and human approval.

Microsoft Agent 365 Agent Registry is included as a target-architecture
building block for agent governance. Microsoft Learn describes Agent Registry
Sync in the Microsoft 365 Admin Center as a Preview feature that can provide
central visibility and governance for agents from external AI-agent
environments. The listed platforms are Amazon Bedrock, Google Vertex AI,
Salesforce Agentforce and Databricks Genie. This is not a current deploy step.
For NaC it is not a production integration requirement. It is a future
control anchor: when NaC agents, MCP connectors or external agent platforms are
connected productively, their registration, visibility, accountability and
deactivation must be reconciled with Microsoft 365 agent governance.

The productive agentic runtime for these integrations is
[NVIDIA NeMo Agent Toolkit / AI-Q](architecture/nemo-agent-toolkit-aiq-m365.md).
Outlook, Teams, OneDrive and SharePoint are not bulk-copied into agent memory;
they are connected through Microsoft Graph and matter-, role- and
purpose-bound MCP servers. The required MCP servers are defined in the
architecture paper; they separate Microsoft 365 mail/calendar, Teams messages,
OneDrive/SharePoint files, Entra ID identity, NaC workflow, grants, document
pointers, audit evidence and local workstation sidecars.

The static site may link to the authenticated web app. It must not serve
tokens, secret upload links, raw documents, identity-card data, certificate
materials or mandate content.

For external legal research and MCP connections, the web app may initially show
only a status and review backlog. The
[Legal Research Connector backlog](plugin-plans/legal-research-connectors.md)
separates source, license state, DPA/AI-SBOM review, security boundary and next
review step without turning the source into a product integration.

## Identity And Authorization

Oracle OCI Identity Domains is the productive identity layer for this SaaS
path. The public transition from `www-n8` into the NaC app is tenant-aware:
existing customers pass a tenant hint, while new customers first run through a
domain-readiness check. NaC then creates a reviewable admin-provisioning plan
for OCI Identity Domains.

The customer-facing surface is `notariat8`. `https://app.notariat8.de/login`
is the canonical entry point for users; direct OCI Identity Domain URLs, OCI
Console paths or internal domain names such as `nac-customers` are operational
details and not primary user guidance. In the short term, customer-facing login
copy, support guidance and demo runbooks must therefore describe notariat8 as
the product surface. OCI Identity Domains remains the internal broker and
trust layer behind that entry point.

Office 365 complements this path on the client and workstation side. OCI
Identity Domains remains the IdP and tenant-provisioning layer for the current
SaaS path; Microsoft 365 supplies workstation services and agent governance
unless a separate reviewed IdP change decides otherwise.

End users do not work in the OCI Console. NaC operates Identity Domains through
reviewed API and CLI contracts; productive writes to users, groups or
memberships require a separate owner review and explicit approval before
apply.

Later customer-IdP federation does not change that customer-facing surface. A
notary office may connect its own IdP, but the user still starts at
`https://app.notariat8.de/login`; OCI Identity Domains brokers between
notariat8 and the customer IdP. Federation, branding, group mapping, SCIM sync
or app-client changes each need separate design, security, DPA, role and owner
apply gates. This document authorizes no OCI write, no secret access and no
productive mandate-data processing.

The IdP login only answers whether a person is trusted for login. The
subject-matter permission is decided afterwards by the NaC role and case gate:

- role in the notary office,
- client or tenant binding,
- matter and case binding,
- purpose of access,
- approval state,
- four-eyes requirement for sensitive steps.

The first NaC app entry therefore uses a login-intent contract instead of an
implicit login. NaC builds the OIDC redirect to OCI Identity Domains through
`/.well-known/openid-configuration` and `/oauth2/v1/authorize`, requires
server-generated `state` and `nonce` values, and treats `tenant_hint` only as
context. The hint must not be translated into roles, groups, matter access or
OCI writes.

In this model, the auth callback is not yet a successful login. It is first a
closed intermediate event with its own `nac.auth-callback/v0.1` contract:
`code`, `state`, and provider error details are not displayed, not copied into
customer-facing text, and not treated as authorization. Without configured
server-side state validation and token exchange, the notariat8 workspace stays
closed; only after that may the NaC role and case gate decide access.

Token exchange is prepared as a server-side adapter. It accepts the code and
client secret only internally, returns no raw tokens, and forwards claims to the
notariat8 role gate only after ID-token verification. If the secret, metadata,
or verifier is missing, the login remains closed.

The stateful auth callback is wired to this adapter, but remains fail-closed:
secret reads and token exchange start only after valid state, a present
authorization code, complete OIDC metadata, and configured server-side ID-token
verification. After a positive notariat8 role gate, the callback may issue a
short-lived, signed session cookie; tokens, claims, nonces, provider details,
and callback values stay out of the cookie. This state still opens no
workspace.

The Q2J boundary validates that signed session cookie before serving
`/workspace`. In that slice, a valid cookie could open at most a protected
notariat8 start/status page; it did not load mandate data and it did not open
the full workspace. Missing, tampered, expired or unconfigured cookies still
return the login-required page.

Q2Q defines the next subject-matter boundary before any path beyond that start
status: verified session plus subject-matter role, tenant binding, case binding
and purpose binding. The contract initially opens only protected status
metadata; raw data, documents and the full workspace remain closed. For
sensitive steps, the gate may require four-eyes approval as an additional
condition.

Q2R wires `/workspace` to that gate. A valid session alone is no longer enough:
without subject-matter role, tenant, case and purpose binding, the route stays
closed. After a positive check, `/workspace` returns metadata-only protected
status. Mandate content, case identifiers, session values, provider details and
raw data are not copied into browser output.

The next Workspace/Auth track tightens this boundary: for `/workspace` and every
route beyond the protected start page, a signed cookie is no longer sufficient.
An active server-side session-store record must also exist. Missing,
unavailable, revoked, expired, or unsafe store records fail closed to the login
page. Audit evidence remains redacted metadata only; the full workspace and
mandate data remain closed.

The operational boundary for signed state values and callback logs is defined
in [OIDC State and Log Boundary](operations/oidc-state-log-boundary.md).

XNP and German eID paths with card readers remain local workstation gates. They
can provide identity or readiness evidence, but they replace neither OCI login
nor NaC authorization and they do not store PINs, raw card data, raw eID data
or certificate material in the repository.

## Mobile App And Secure Links

A mobile app such as `n8-demonotariat` can serve as a client or participant
app. After login and approval, the user does not receive blanket NaC access,
but only a tightly bounded secure link.

Consumer ChatGPT, free accounts or non-EU-resident ChatGPT access are not a
client gateway. A client must not send an identity-card photo, mandate document
or other raw document to such a chat so it can then be forwarded into an
Enterprise workspace. That detour is not matter-bound, not reliably revocable
and not checkable as a NaC audit path.

The first product path is therefore:

1. The NaC backend creates a secure link with purpose, expiry, matter binding
   and revocation.
2. The client opens a mobile web app or PWA; a native iOS/Android app is added
   only for NFC eID, push, device binding, liveness checks, offline operation
   or app-store trust.
3. The file or photo first lands in an EU-controlled storage target.
4. Optionally, a server-side backend processes metadata or extraction through
   approved services such as OpenAI API Europe with
   `https://eu.api.openai.com`; mobile devices do not receive API keys.
5. Internal users review the inbox through the NaC web app or an approved
   Enterprise workspace connector.

Allowed link targets are:

- upload into an object store,
- upload into a database blob,
- upload or read view in OneDrive,
- read-only view of current matter information, where the case permits it.

Every link must be short-lived, revocable, tenant-, matter- and purpose-bound.
NaC stores only evidence in the product repository, such as hash, storage
target class, matter binding, expiry, issuing role, approval state and audit
event. The secret link itself, access tokens and raw documents do not belong in
Git.

Uploads from the app first land in an inbox or import proposal. They are linked
to a matter only after human review, role checks and, where required, four-eyes
approval.

## Checkable Boundary

The minimum technical boundary is defined in the
[Secure Document Link contract](../../workflows/contracts/secure-document-link.contract.json)
and validated through the central NaC CLI:

```bash
nac contracts validate
```

The contract requires purpose, expiry, matter binding, storage target,
revocation and audit evidence. This turns the mobile or authenticated web app
from a product idea into a checkable NaC artifact path.

## Implementation Order

1. Keep using the static GitHub Pages layer for public content and synthetic
   demos.
2. Design the internal authenticated web app for notary-office users through
   OCI Identity Domains and the NaC role gate; users start at
   `https://app.notariat8.de/login`, not at direct OCI URLs.
3. Track Office 365 as the mandatory client layer and Microsoft Agent 365 Agent
   Registry as a Preview governance anchor in the target architecture and
   backlog.
4. Add NeMo Agent Toolkit / AI-Q as the productive agentic runtime and
   Microsoft 365 MCP boundary to integration planning.
5. Explicitly disallow consumer ChatGPT as a client-upload gateway.
6. Check card-reader, XNP and eID paths only locally through the
   `notary-workstation` profile.
7. Connect the mobile web app or PWA to storage targets first through
   short-lived secure links; build native apps only for concrete device needs.
8. Treat uploads as inbox items or import proposals first.
9. Make contract, validator, audit and human approval mandatory before
   productive links.
