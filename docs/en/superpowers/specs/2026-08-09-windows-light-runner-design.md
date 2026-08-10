# Windows Light Runner – Design Spec

Status: Design approved, implementation pending
Last updated: 2026-08-09
Leading issue: (to be linked with implementation)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: windows-light-runner
leading_issue: https://github.com/notariat8/NaC/issues/632
risk_gate: Security
delivery_mode: Protected PR
review_gates:
  - Security
  - Platform
  - Human Approval
acceptance_ids:
  - AC-WLR-01
  - AC-WLR-02
  - AC-WLR-03
  - AC-WLR-04
  - AC-WLR-05
  - AC-WLR-06
validation_commands:
  - python scripts/validate_m365_azure_bff_live_activation.py
  - python scripts/nac.py doctor --profile strict
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_governance_sync.py
```

## Purpose

Migrate the NaC M365 BFF Live Activation Runner from Linux-exclusive hardening
(`memfd`, mount namespaces, `O_NOFOLLOW`) to Windows-native operation.
Equivalent security level for the single-operator notary workstation running
Windows 11, without WSL dependency.

## Scope

- `nac m365 teams-sharepoint bff-azure-activate-live` runs natively on Windows
- All 12 activation steps preserved
- Toolchain attestations (`bff-azure-activation-attestations`) use Windows paths
- Owner-gate (`bff-azure-activation-owner-gate`) unchanged
- Approval flow (GitHub issue comment) unchanged
- Ledger, evidence, lock journal unchanged

## Constraints

- Operating system: Windows 11 (as specified in `docs/en/minimum-requirements.md`
  for the `base` profile)
- `az` CLI and `m365` CLI as native Windows installations
- No WSL, Docker, or container required
- Single-operator machine – no multi-tenant threat model
- Hardened Linux features (`memfd`, private mount namespaces) are replaced by
  Windows built-in mechanisms, not 1:1 emulated

## Design Decisions

### 1. Binary Verification instead of memfd

**Linux (old):** Az CLI binary loaded via `memfd_create()` as a sealed
in-memory file descriptor, with no filesystem path attackable.

**Windows (new):**
1. Compute SHA-256 of the binary BEFORE subprocess launch
2. Binary on NTFS with owner-only permissions (`icacls` / `SetFileSecurity`)
3. Atomic copy: binary copied to temp directory, handle opened via `CreateFile`
   with `FILE_SHARE_READ` but without `FILE_SHARE_WRITE|DELETE`
4. SHA-256 of the opened handle verified against attestation
5. Subprocess launched from this handle

**Rationale:** On a single-operator machine, binary manipulation by foreign
processes is not a realistic threat. Handle-based verification ensures no swap
occurs between SHA check and process launch.

### 2. Job Objects instead of Mount Namespaces

**Linux (old):** Az CLI runs in a private mount namespace with an isolated
virtual filesystem.

**Windows (new):**
1. Job Object created with `JOB_OBJECT_LIMIT_ACTIVE_PROCESS` = 1
2. Environment variable allowlist before subprocess launch (only `PATH`,
   `SYSTEMROOT`, `AZURE_CONFIG_DIR`, `CLIMICROSOFT365_*`)
3. Subprocess launched inside the Job Object
4. No filesystem isolation – not required, as the operator already has full
   access and no foreign processes need isolation

**Rationale:** Mount namespaces protect against filesystem-based attacks by
co-tenant processes. On a single-operator machine, this threat model does not
exist. A Job Object is sufficient for process lifecycle control.

### 3. Lock via Windows Mutex

**Linux (old):** `fcntl`-based file lock with append-only journal.

**Windows (new):**
1. Global Windows mutex via `CreateMutexW` under
   `Local\nac-m365-bff-live-activation-{target-binding-sha256}`
2. Lock journal as append-only JSON file – unchanged from the Linux model
3. `AbandonedMutex` detection for crash windows (native Windows feature)

**Rationale:** Windows kernel mutexes are more robust than file locks for
process crashes. The journal remains as an audit trail.

### 4. O_NOFOLLOW Replacement Not Needed

**Rationale:** Windows symlinks require administrator privileges
(`SeCreateSymbolicLinkPrivilege`). The operator workstation has no foreign
processes capable of creating symlinks. Path canonicalization
(`GetFinalPathNameByHandle`) before each launch is sufficient.

## Risks

| Risk | Trigger Condition | Mitigation |
|---|---|---|
| Binary manipulation between SHA check and launch | Second process with admin rights on the machine | Handle-based verification; admin rights on notary workstation only for installation |
| Environment variable leak | `az`/`m365` CLI reads sensitive variables | Allowlist before subprocess |
| Concurrent activation | Two `nac` instances simultaneously | Global Windows mutex |
| NTFS permissions not set | Operator did not run `icacls` | Validator checks before first write |

## Acceptance Criteria

| ID | Criterion | Validation |
|---|---|---|
| AC-WLR-01 | `nac m365 teams-sharepoint bff-azure-activate-live` runs on Windows 11 without WSL | Manual run on Windows notary workstation |
| AC-WLR-02 | All 12 activation steps execute and produce identical ledger events as Linux (except platform-specific fields) | Ledger comparison with Linux reference run |
| AC-WLR-03 | Toolchain attestations compute SHA-256 from Windows installation paths | `bff-azure-activation-attestations --format json` → status=READY |
| AC-WLR-04 | `validate_m365_azure_bff_live_activation.py` PASSED | Validator run |
| AC-WLR-05 | Contract: `linux_memfd_and_proc_fd_required` = `false`, `azure_cli_private_user_and_mount_namespace_required` = `false` | Contract file diff |
| AC-WLR-06 | `nac doctor --profile strict` PASSED | Doctor run after implementation |

## Non-Goals

- No 1:1 emulation of Linux kernel features on Windows
- No container/Docker/WSL2 as runtime environment
- No changes to the 12 activation steps or their ordering
- No removal of hash bindings or owner gate
- No support for multi-tenant threat model

## Related Artifacts

- `workflows/contracts/m365-azure-bff-live-activation.contract.json`
- `docs/en/minimum-requirements.md`
- `policies/technology-policy.yaml`