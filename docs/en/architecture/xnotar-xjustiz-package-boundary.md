# XNotar/XJustiz Package Boundary

Status: offline metadata contract without live apply

## Purpose

This page describes the NaC boundary for future XNotar/XJustiz exchange
packages. It extends the notarial application interface inventory, but it does
not replace an XNotar or registry integration.

The machine-readable contract is
[workflows/contracts/xnotar-xjustiz-package-boundary.contract.json](../../../workflows/contracts/xnotar-xjustiz-package-boundary.contract.json)
and is validated by
[scripts/validate_xnotar_xjustiz_package_boundary.py](../../../scripts/validate_xnotar_xjustiz_package_boundary.py).

## Inventory Binding

The notarial application interface inventory exposes this boundary as the
metadata-only entry `xnotar_xjustiz_package_boundary`. The read-only MCP tools
`notarial_interface_inventory_list` and `notarial_interface_boundary_check` may
show this row and evaluate it as `allowed_metadata_only`, but they do not call
XNotar, BNotK, SharePoint or Microsoft Graph.

## Package Shape

For the MVP, only redacted package readiness is allowed:

- BPMN channel: `xnotar_xjustiz`
- XJustiz state: XJustiz 3.3.1
- expected message file: `xjustiz_nachricht.xml`
- expected attachments folder: `attachments/`
- allowed evidence: status, interface ID, module target, version pin, file
  counters, hash/pointer status plus no-secret and no-matter-data attestation

XML content, XSD content, attachment content, registry data, land-register
data, matter content, absolute paths, credentials, certificates or
IdentityTokens are not allowed in the product repository.

## Owner Gates

The following steps remain separately approved:

- XNotar test access,
- XJustiz payload mapping,
- license review before raw schema use,
- processing attachment content,
- productive XNotar handoff,
- sending to registry or land-register systems.

## Architecture Decision

NaC initially models XNotar/XJustiz as an external specialist-system gate. The
M365 MVP remains Teams, SharePoint and Microsoft Graph REST/MCP. This package
boundary may only provide metadata and redacted evidence; it may not read,
write, send or validate packages against raw XSD files.

This allows BPMN to model handoff and wait points today without pulling
specialist-system access, matter data or XJustiz payloads into NaC.
