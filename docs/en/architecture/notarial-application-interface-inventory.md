# Notarial Application Interface Inventory

Status: offline inventory without live apply
Last content update: 2026-07-07

## Purpose

This page records the owner-provided BNotK and XJustiz interface sources as a
NaC architecture inventory. It is not a production access path, not a
credential store and not an approval for specialist-system write actions.

The machine-readable contract is
[workflows/contracts/notarial-application-interface-inventory.contract.json](../../../workflows/contracts/notarial-application-interface-inventory.contract.json)
and is validated by
[scripts/validate_notarial_application_interface_inventory.py](../../../scripts/validate_notarial_application_interface_inventory.py).

## Source State

| Source | State | Repository Boundary |
| --- | --- | --- |
| BNotK Onlinehilfe, application interfaces: https://onlinehilfe.bnotk.de/technischer-bereich/softwarehersteller/anwendungsschnittstellen.html | page state 2026-06-01, owner-provided offline archive from 2026-07-07 | Module, protocol and boundary metadata only; no HTML or asset copy in the repository |
| BNotK Onlinehilfe, beN: https://onlinehilfe.bnotk.de/technischer-bereich/softwarehersteller/ben.html | owner-provided offline archive from 2026-07-07 | Architecture boundaries such as XTA-WS, OSCI, certificate, IdentityToken and polling only; no WSDL or sample payload copy in the repository |
| XJustiz 3.3.1 XSD package | owner-provided ZIP `xjustiz_3_3_1_xsd.zip`, package files timestamped 2021-11-04 | Package metadata only; no raw XSD copy without license and source approval |

## Interface Matrix

| ID | Area | Interface Family Visible From The Source | NaC MVP Meaning |
| --- | --- | --- | --- |
| `mandantenportal` | Mandantenportal | JSON export and OpenAPI | Candidate for later import/status boundary; in the MVP only an external source point and metadata hint |
| `uvz` | Urkundenverzeichnis | NSW import, read access from UVZ and write access into UVZ | Boundary gate only; no production write and no UVZ raw data in the repository |
| `vvz` | Verwahrungsverzeichnis | Import/export and data query | Boundary gate only; later private payload and role review required |
| `xnotar_handelsregister` | Commercial register via XNotar | Handoff of matters and documents from NSW to XNotar | BPMN handoff point and redacted evidence, no NaC-controlled dispatch |
| `xnotar_grundbuch` | Land register via XNotar | Handoff of matters and documents from NSW to XNotar | BPMN handoff point and wait/response gate, no land-register raw data in NaC |
| `xnotar_sonstige_antraege` | Other XNotar applications | Handoff of matters and documents from NSW to XNotar | Modeled as an external specialist-system boundary |
| `enova` | XNotar-eNoVA | OpenAPI specification and SDS/XJAB-adjacent handoffs | Candidate for a later test-access gate; no MVP live apply |
| `zvr` | Zentrales Vorsorgeregister | REST API function calls from NSW | Separate integration path with BNotK/ZVR approval, certificates and owner gate |
| `ben` | besondere elektronische Notarpostfach | XTA-WS, EGVP/OSCI container, TLS client certificate, IdentityToken, mailbox polling and transport status | Local companion/evidence path; no secrets, no message content and no production sending in the product repository |
| `xjustiz_331` | XJustiz 3.3.1 | 66 XSD files with base dataset, messages, register, Vorsorgeregister, eEB, ZTR and further domain modules | Schema reference for a later mapping and validation pipeline; no XSD full text and no payload test dataset in the repository |

## Architecture Decision

For the M365 MVP, the active data plane remains Teams, SharePoint and
Microsoft Graph REST/MCP. The BNotK, beN and XJustiz sources do not become the
central runtime storage. They define integration boundaries and later connector
gates.

The first allowed NaC implementation is:

1. Model interfaces as BPMN gates or external systems.
2. Allow MCP tools only as read-only inventory and planning tools.
3. Move live calls, certificates, IdentityToken handling, mailbox access and
   payload mappings into a private operating frame.
4. Store redacted evidence, but no messages, register data, deed content,
   XML payloads, raw XSD copies or BNotK full text.

## Non-Goals

- no storage of BNotK HTML, BNotK assets, beN sample payloads or XJustiz XSD
  files in the product repository,
- no beN, UVZ, VVZ, ZVR, Mandantenportal or XNotar live connection,
- no credentials, client certificates, tokens, PINs or notarial-office
  identifiers in the repository,
- no production specialist-system write action without a separate private
  operating frame, privacy review, test access and owner apply gate.

## Next Technical Derivation

The next useful technical step is a read-only MCP tool contract for
`notarial_interface_inventory_list` and `notarial_interface_boundary_check`.
These tools may only expose the metadata and gate decisions maintained here;
they must not call external BNotK systems and must not ingest source artifacts.
