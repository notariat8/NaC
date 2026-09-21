# Current-State Diagnostics for Teams and BFF Access

Status: repository and synthetic implementation for Issue #748 in progress; acceptance and the real provider run remain separately blocked

The diagnostic examines only the current readable state of `notary_team_01`
and the “NaC Vorgangsansicht” Teams app. It does not replace the terminal Issue
#739 run and authorizes no Issue #632 action.

## Operation

Before preflight, the download explicitly triggered in the SPFx web part is
materialized locally without provider access. The receipt contains only the
neutral UI state, subject Boolean, a closed UTC window, and window and
correlation bindings:

```powershell
python scripts/nac.py m365 teams-sharepoint current-state-access-client-receipt-stage `
  --current-state-access-client-receipt C:\Downloads\nac-issue748-client-observation.json `
  --current-state-access-input-root C:\protected\issue748\input `
  --format json
```

The command validates exactly `end_utc`,
`request_correlation_binding_sha256`, `spfx_subject_available`, `start_utc`,
`ui_state`, and `window_binding_sha256`. `ui_state` must be `no_access`; the
closed UTC window must be positive and no longer than 15 minutes. The command
then exclusively creates
`client-observation-receipt.json`. It does not overwrite an existing receipt.
Login, network, provider, and deployment remain untouched.

The local preflight accepts only two absolute, repository-external directories
protected through the Windows security backend:

- The input directory contains the closed, hash-bound contract, resolver,
  target, client, toolchain, and owner evidence. The DPA receipt additionally
  binds a separate protected DPA agreement evidence document and the freshly
  measured `policies/data-protection-policy.yaml` repository blob. Self-
  asserted status or digest values are insufficient.
- The evidence directory accepts only the one-shot consume marker and the
  redacted final result.

The protected `toolchain.json` also binds the absolute path and SHA-256 digest
of a repository-external read-only driver. Before every execution, the Windows
security backend verifies its owner, DACL, reparse, file-ID, hardlink, and hash
bindings. The driver accepts only the fixed gate and diagnostic operations and
runs with a scrubbed environment, credential-write guard, bounded output, and
no retry. Owner approval alone does not replace this technical attestation.

```powershell
python scripts/nac.py m365 teams-sharepoint current-state-access-diagnostic-preflight `
  --current-state-access-input-root C:\protected\issue748\input `
  --current-state-access-evidence-root C:\protected\issue748\evidence `
  --format json
```

The later real run uses the same path arguments:

```powershell
python scripts/nac.py m365 teams-sharepoint current-state-access-diagnostic-run-read-only `
  --current-state-access-input-root C:\protected\issue748\input `
  --current-state-access-evidence-root C:\protected\issue748\evidence `
  --format json
```

Without a new owner approval bound to the final state, the second command
remains blocked with a redacted `BLOCKED` result. There are no CLI arguments
for tenant, account, principal, team, site, Function, or correlation values and
no login, retry, force, redirect, deployment, or write option.

## Result

Only two independent, canonically identical, redacted acquisitions may produce
exactly one of these classes:

- `SPFX_SUBJECT_MISSING`;
- `BFF_REQUEST_NOT_OBSERVED`;
- `BFF_AUTHENTICATION_REJECTED_401`;
- `BFF_AUTHORIZATION_REJECTED_403`.

Every deviation blocks without retry. The result permits only a new fix plan,
not a production change.

## Security Boundary

- authorization before the port factory and again before every read;
- seven closed ports, no general provider or search interface;
- no token, header, credential, or cache contents in evidence;
- no login, refresh, credential write, redirect, or retry;
- exactly one protected local evidence sink;
- absent a concretely cited applicable two-person duty,
  `OWNER_SOLO_APPROVAL` is permitted and is not four-eyes approval;
- if a concretely cited applicable duty requires two natural persons, one
  principal blocks with `BLOCKED_SINGLE_PRINCIPAL`;
- different accounts of the same principal extend no permission;
- #739 and #632 remain terminal and untouched respectively.

The [specification](superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md),
the [plan](superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md),
and the [verification contract](../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml)
are binding.
