# Notarkammer Demo: XNP Source Matrix

Status: 2026-06-21

This matrix is a PR-only demo artifact. It translates publicly supportable
statements about XNP, XNotar, land-register, register and card-reader access
points into safe NaC demo claims. It is not a technical coupling promise and
not a production concept.

The demo rule is intentionally narrow: NaC shows external access points in
BPMN, checks only redacted evidence and works without case content. For the
presentation this means: no mandate data, no production XNP connection, no direct XNP-to-NaC coupling.

## Demo Claim Matrix

| ID | Claim | Source | What NaC may show in the demo | What NaC must not claim |
| --- | --- | --- | --- | --- |
| SRC-XNP-001 | XNP is the BNotK base application and includes modules such as UVZ, VVZ, notarial online procedures, beN, documents with PDF viewer and signature folder, user management and card management. | NotarNet XNP: https://notarnet.de/produkte/xnp | NaC may mark XNP as an external access point and local notarial work environment in BPMN, for example as a gate near documents, signature, beN or card management. | NaC must not claim that XNP is a NaC backend, that NaC remote-controls XNP or that a direct production connection exists. |
| SRC-XNOTAR-001 | XNotar supports electronic legal communication in register and land-register matters plus further domain modules. | NotarNet XNotar: https://notarnet.de/produkte/xnotar | NaC may show XNotar as a domain-specific external access point for land-register and register paths in BPMN and capture status as a redacted user attestation. | NaC must not claim that XNotar data flows automatically into NaC or that NaC replaces the domain application for land-register or register work. |
| SRC-XNP-BNOTK-001 | BNotK Onlinehilfe describes XNP as the base application whose modules provide access to BNotK applications and electronic legal communication; XNP-XNotar covers Grundbuch and Handelsregister. | BNotK Onlinehilfe XNP base application: https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html | NaC may explain in the demo that XNP/XNotar belongs to the domain work environment and that NaC only shows BPMN orchestration, audit status and evidence points. | NaC must not claim that the public help page proves a direct NaC interface, approval for live operation or a production XNP connection. |
| SRC-GRUNDBUCH-001 | BNotK Onlinehilfe shows land-register application steps such as basic data, properties, applications, parties, documents, validation, preparation, signing, preparing dispatch and dispatch via beN. | BNotK land-register application steps: https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-eines-grundbuchantrags-auf-einen-blick.html | NaC may make these steps visible in BPMN as an external land-register access point, waiting point and evidence gate. | NaC must not claim that land-register content is delivered directly from XNP to NaC or that NaC performs dispatch itself. |
| SRC-REGISTER-001 | BNotK Onlinehilfe shows register-filing steps such as basic data, legal entity, filing cases, parties, documents, validation, completing preparation, signing, preparing dispatch and dispatch. | BNotK register-filing steps: https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-einer-registeranmeldung-auf-einen-blick.html | NaC may model register filings as an external register access point in BPMN and keep local status attestation as evidence. | NaC must not claim that NaC automatically receives register data, sends register filings in production or replaces the domain review. |
| SRC-CARDREADER-001 | BNotK names tested REINER SCT card readers and, for other devices, points at least to class 3, display and own PIN pad. | BNotK card readers: https://onlinehilfe.bnotk.de/einrichtungen/zertifizierungsstelle/hinweis-zu-kartenlesegeraeten.html | NaC may show card-reader readiness as a local BPMN prerequisite or evidence point without storing PIN, card data or mandate content. | NaC must not claim to control or read card readers, signature cards or PIN entry from NaC. |

## Demo-Language Guardrails

- Allowed: "NaC shows in BPMN where XNP, XNotar, land-register, register or
  card-reader steps become relevant."
- Allowed: "Evidence is captured in redacted form; NaC stores no mandate data,
  no PINs, no signature-card data and no raw documents."
- Allowed: "The domain-system step remains in the designated notarial work
  environment."
- Not allowed: a direct technical production coupling, automated data intake
  from XNP/XNotar or NaC-controlled dispatch to the land-register office or
  register court.
- Not allowed: real case data, names, file references, PINs, tokens, local
  paths or operating details in demo material.

## Meeting Short Form

In this demo, NaC is the BPMN and audit frame. XNP, XNotar, land-register,
register and card readers appear as domain-specific external access points.
The public sources support the existence of those domain steps; they do not
support a production NaC coupling.
