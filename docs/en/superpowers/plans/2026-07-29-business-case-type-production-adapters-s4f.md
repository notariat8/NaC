# Implementation Plan S4f Production Adapters

1. Bind issue #704, spec, plan, and AC-S4F-01 through AC-S4F-07.
2. Implement GitHub owner verifier, certificate factory, and Graph HTTP port.
3. Implement the restart-safe local SQLite evidence staging outbox without
   completion authority.
4. Add S4f composition status and CLI; verify each of these as an explicit
   blocker: central PostgreSQL outbox with promotion, acknowledgement, retention, and
   local cleanup, broker product,
   signature/anchor method, provider-side identity and site-grant readback,
   Azure WORM REST transport, irreversible WORM policy lock, dedicated Entra
   writer identity with site grant, and owner-gated live activation.
5. Add domain/verification contracts, validator, tests, and agent context.
6. Run focused tests, contract gates, and strict gate.
7. Perform independent base...head review and fix all P1/P2 findings.
8. Create protected PR, verify remote CI, merge, and clean the branch.
