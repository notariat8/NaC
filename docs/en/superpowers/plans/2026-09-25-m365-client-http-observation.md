# Implementation plan: Teams tab HTTP companion receipt

Date: 25 September 2026. Leading [Issue #748](https://github.com/notariat8/NaC/issues/748). Basis: the [specification](../specs/2026-09-25-m365-client-http-observation-design.md).

The goal is a narrowly scoped client observation, not a claim that access was fixed or that the BFF received a request. The existing six-field receipt and its historical [contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) remain unchanged.

1. **Test first:** Cover synthetic 401/403 responses, missing SPFx subject, unknown errors, concurrent loads and explicit download. No extra request or identity/content fields in the receipt. AC-748-HTTP-01/02/04.
2. **Client:** Only the actual `/workbench-snapshot` HTTP response produces a typed 401/403 class. A separate module binds it to the completed base receipt in a companion of at most 1024 bytes. The UI remains neutral and offers the second download only for a valid observation. AC-748-HTTP-01/02/03.
3. **Contract and verification:** A new verification contract and local validator accept only the closed fields, check both hashes and the unchanged base receipt, and reject substitution, extra fields and class changes. The production #748 preflight does not automatically ingest it. AC-748-HTTP-03/04.
4. **Review and gates:** Review data/logic/UI boundaries, privacy, DE/EN parity, spec traceability and the AI-SBOM decision. Then run SPFx tests, visual proof, Graft Build/Check and Strict Doctor. A new app version may enter the test App Catalog only after a separate release gate. A real Teams test and provider read remain separate next steps. AC-748-HTTP-05.

Stop on any new login/token/provider action, personal output, unattributable HTTP status or change to the historical receipt. This plan authorizes neither deployment nor a real diagnostic run.
