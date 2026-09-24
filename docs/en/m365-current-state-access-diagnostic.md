# Current-State Diagnostics for Teams and BFF Access

## Status on September 24, 2026: driver release not ready

After the documented merges of [PR #749](https://github.com/notariat8/NaC/pull/749)
and [PR #751](https://github.com/notariat8/NaC/pull/751), the client receipt
control is available. This does not yet explain the Teams error: the new
[read-only driver design](superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md)
in Draft PR #752 is a separate delivery boundary. Its current source contract
blocks Microsoft access with `BLOCKED_NO_REFRESH_CAPABILITY` before consuming
the one-shot diagnostic gate. A contract test or synthetic diagnostic is
neither a built Windows release nor a real provider finding. In particular,
`OFFLINE_REVIEWABLE` still requires a complete bundle, source/runtime/SBOM/
license evidence, and closed local file attestation. `LIVE_CAPABLE` additionally
requires a technically proven no-refresh channel, complete projections, and
separate exactly bound approvals for driver release and one read.

The existing CLI commands gain no free URL, query, token, or login options.
The lost #739 run and #632 remain untouched.

Historical status of the original #749 draft: repository and synthetic implementation complete; merge, SPFx deployment, and a real provider run were separately approval-gated. See the dated section above for the current status.

The diagnostic examines only the current readable state of `notary_team_01`
and the “NaC Vorgangsansicht” Teams app. It does not replace the terminal Issue
#739 run and authorizes no Issue #632 action.

## Operation

The first step requires the receipt-capable SPFx version to have passed PR
acceptance, received a separate deployment approval, been deployed to the test
app catalog, and had its package/source binding verified read-only. Neither the
repository implementation nor a later read-only-run approval authorizes a
deployment. Only then does the operator explicitly select “Diagnosebeleg
speichern” in the actually deployed neutral “Kein Zugriff auf diesen
Arbeitsbereich” view.

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

The committed Windows screenshots remain the visually reviewed reference
evidence. Linux CI renders the same synthetic cases into a temporary runner
directory and verifies states, overflow, the receipt button, bindings, and the
zero-network and zero-auto-download boundaries. Platform-specific font and PNG
bytes are not falsely treated as functional equality.

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
bindings. The operating system alone cannot attest which HTTP method the
driver uses internally. The real run therefore remains blocked until the
specific driver is separately approved as a reviewable, versioned release
with source binding, classic SBOM, license, a GET-only resource allowlist, and
zero-login, zero-refresh, zero-redirect, zero-retry, and zero-write contracts.
PR #749 does not deliver that driver release. Owner approval or a binary digest
alone does not replace this supply-chain and behavior review.

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

The separate [read-driver design](superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md)
has a local-only build and verification path. `python
scripts/validate_m365_current_state_read_driver.py` checks the checked-in
contracts only. An actual external package must additionally pass `--candidate
<absolute-path>` against the current Git commit, source archive contents,
every bundle file, Windows owner/DACL binding, and CycloneDX, SPDX, and license
evidence. A passing source check is not proof of a package. The production
port still blocks with `BLOCKED_NO_REFRESH_CAPABILITY`; no real read is approved.

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
