# Implementation Plan S4g Production Edge Composition

1. Bind issue #708, DE/EN specs, DE/EN plans, and AC-S4G-01 through
   AC-S4G-08.
2. Domain-separate hashes of the actual S4d, S4f and S6b contract files and
   repository implementations separately for the identity-inspector implementation and snapshot attestation, owner verifier, writer
   token factory, Graph and Azure WORM REST transports; bind the WORM target as
   explicitly offline-unconfigured.
3. Verify provisioner, writer, and BFF through separate and independently
   pairwise-distinct Entra `app_id` and `service_principal_object_id` values whose
   complete namespaces are globally disjoint;
   limit writer to `Sites.Selected/write` and BFF to `Sites.Selected/read`.
4. Bind mutation state and evidence staging to separate local SQLite paths and
   fail closed for identical, synced, remote, unknown, symlink-based, weakly protected, or multiply linked files.
   Reject every non-snapshot identity port before readback.
5. Verify the Azure Blob WORM REST transport offline with injected token and
   HTTP ports, fixed hosts and API versions, `GET`/`PUT`, bounded sizes,
   create-only idempotency, and exact-version readback; exclude lock and delete
   operations.
6. Verify PostgreSQL promotion/acknowledgement/retention/cleanup, broker
   decision, signature-anchor decision, durable reconciliation, irreversible
   WORM lock, and owner-gated live activation as mandatory blockers.
7. Limit status and redacted evidence to
   `S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE` and
   `BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION`; prevent
   runtime construction and credential reads before the central gates.
8. Add the domain and verification contracts, validator, and negative contract
   tests, then run focused tests plus traceability, language, link, contract,
   and strict gates.
9. Independently review the complete `base...head` diff, resolve every P1/P2
   finding, and deliver only through the protected PR path.
10. Perform no tenant, Entra, Graph, Azure, credential, permission,
    infrastructure, or WORM-lock action.
