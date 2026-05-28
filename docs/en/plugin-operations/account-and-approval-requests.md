# Account And Approval Requests For NaC Plugins

This file is the Day0 request register for productive plugin use in the
notary-office context. It intentionally contains no real account names,
secrets, mailbox identifiers, tax identifiers, certificate material or mandate
content.

## Global Controls

| Area | Request | Needed Before | Owner | Notes |
| --- | --- | --- | --- | --- |
| GitHub | Repository write access, branch protection, required checks and CODEOWNER review | productive plugin releases | platform owner | Private repo access must be explicit. |
| Evidence | DMS or audit store decision, retention class, hash policy and deletion hold process | any evidence import | compliance owner | Metadata-only by default. |
| Security | Secret storage decision for future connectors | any write adapter | security owner | Use local OS store or tenant Vault, not Git. |
| Review | Two-person approval matrix for notarial actions | Day1 notary-office workflows | notary | Required before card/PIN prompts, submissions, register applications, XNP/XNotar handoffs or notarial actions. |

## Plugin-Specific Requests

| Plugin | Accounts / Approvals To Request | Blocking For |
| --- | --- | --- |
| `nac-regulated-core` | GitHub repository write access; Approved reviewer roster; Evidence storage decision | Day1 productive use |
| `nac-handelsregister` | Mode decision: citizen preflight or notary-side workflow; Completed `nac-cyberjack-rfid` and `nac-bnotk-xnp` readiness for notary-side workflows; Notary appointment or notary office workflow; Bundesnotarkammer online procedure app; eID-capable official ID and PIN; Applicant and reviewer approval for the register application package | Day1 productive use |
| `nac-bnotk-xnp` | Completed `nac-cyberjack-rfid` card/SAK readiness; BNotK/XNP access for the notary office; Local XNP login and active Amtstaetigkeitskontext; XNotar/register module or exchange-folder route; Notarial software vendor interface approval; Local workstation admin approval | Day1 productive use |
| `nac-cyberjack-rfid` | BNotK chip/signature card or local Schneider/SCP-card availability; Security-class-3 card reader; BNotK SAK lite or XNP card path; secureFramework communication path; Approved hardware procurement; Local workstation admin approval; Driver/vendor support channel | Day1 productive use |
| `nac-grundbuch-portal` | State-specific Grundbuchportal access; Authorized professional role confirmation; Cost-center approval; Retention/DMS decision | Day1 productive use |
| `nac-oci-evidence` | OCI tenancy access; Compartment admin or delegated policy; Vault/key-management approval; Budget owner; Audit retention owner | Day1 productive use |

## External Write Adapter Hold Points

Do not implement or enable direct external write adapters until these are approved in writing:

- `Karte/SAK` for BNotK chip/signature card or local Schneider/SCP-card availability, security-class-3 reader, secureFramework and no PIN capture.
- XNP/notarial software official interface contract, completed `Karte/SAK`, local `XNP-Prüfung`, Amtstaetigkeitskontext and credential boundary.
- Grundbuchportal authorized direct adapter, state-specific terms and legitimate-interest evidence.
- Handelsregister online application route, mode decision, completed `Karte/SAK` and `XNP-Prüfung` for notary-side workflows, applicant authority and eID/app readiness.
- OCI Resource Manager apply permissions, Vault policy and audit retention.

## Day2 Recertification

- Reconfirm account ownership and role necessity at least quarterly for pilots and before production release.
- Reconfirm local workstation prerequisites after OS, XNP, browser, driver or card-reader updates.
- Re-run `python3 scripts/nac.py plugins validate` after each plugin manifest change.
