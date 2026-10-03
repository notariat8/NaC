# Matter read access through membership of the notary Team

Status: Owner approved the specification; local test-first implementation, no live authorization.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: team-member-matter-read-620
leading_issue: https://github.com/notariat8/NaC/issues/620
risk_gate: Policy
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-10-03-team-member-matter-read.md
acceptance_ids:
  - AC-TEAMREAD-01
  - AC-TEAMREAD-02
  - AC-TEAMREAD-03
  - AC-TEAMREAD-04
  - AC-TEAMREAD-05
  - AC-TEAMREAD-06
validation_commands:
  - python -m unittest discover -s tests -p test_nac_bff_team_membership.py
  - python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
```

## Purpose and domain truth

One Team per notary. All members may see and open all matters of that Team.
Membership grants matter read access. The previous additional lead-notary,
clerk or deputy assignment is not a prerequisite for this read access.
The current HTTP 403 client receipt proves rejection, not its specific
server-side decision stage.

## Scope and constraints

The rule covers matters of the associated notary Team, not other Teams.
The first executable proof remains the existing synthetic MVP workspace
and test matter. This change does not claim complete multi-matter navigation
or a general multi-tenant runtime. The technical user Owner, personal login,
tenant boundary and existing API target boundaries remain intact. Membership
does not grant notarial qualification, approval, write access or deputy status.

## Approaches and decision

1. Mirror Team members into individual matter assignments: rejected;
   duplicate authorization data and drift, not the Owner's requested rule.
2. Check current membership of the bound Team server-side: recommended;
   one authorization source, clear Team boundary, deny when evidence is missing.
3. Trust browser assertions or unchecked group claims: rejected;
   insufficient freshness and target binding.

## Design

- Trusted configuration connects workspace, Team, SharePoint site and matter
  source. Team names and client parameters are not authorization evidence.
- The validated Entra subject and tenant IDs are checked server-side against
  current direct membership of the bound Team. The precise GET edge and its
  runtime permission will be specified and tested in the plan; no implicit
  expansion of Graph permissions.
- Membership evidence must be complete, bounded and unambiguous. Paging must
  not be ignored. Errors, missing permissions, wrong tenant, missing membership
  or ambiguous Team/site binding must not open a matter.
- The matter source and matter must belong to the verified Team. Membership
  of another Team or a technical Owner role label alone is insufficient.
- A neutral read authorization flows through BFF, DTO, projection and SPFx.
  Members must not be mislabeled as notaries or clerks to bypass existing checks.
- Additional Entra/SharePoint person mapping must not block Team read access;
  retain it where domain person fields actually require it.
- Positive membership evidence is used only within the current request; no
  new long-lived positive cache. Existing decision leases remain valid for
  at most 300 seconds. Removal takes effect on the next fresh access.
- Replace historical negative tests using a Team member with actual nonmembers
  or users of another Team. Do not prepare new positive tests by adding an
  individual matter assignment.

## Acceptance criteria

- AC-TEAMREAD-01: A validly authenticated member reads a matter of their Team
  without individual assignment or deputy approval.
- AC-TEAMREAD-02: A nonmember or member only of another Team receives neither
  matter content nor disclosure of its existence.
- AC-TEAMREAD-03: Wrong tenant, manipulated IDs, incomplete responses,
  transport failures and missing runtime permissions stop without positive access.
- AC-TEAMREAD-04: A neutral Team reader receives no notarial role or additional
  write, approval or deputy actions.
- AC-TEAMREAD-05: Team read access works without SharePoint person mapping;
  existing domain person and deputy checks remain isolated.
- AC-TEAMREAD-06: Policies, DE/EN documentation, agent mirrors, contracts,
  CLI interface and tests agree. Synthetic tests do not prove the live repair;
  that requires separately verified runtime permissions, release/deployment
  binding and an actual Teams test.

## Risks, test approach and non-goals

Scope mapping binds implementation to `live_access_decision.py`,
`composition.py`, `synthetic_workspace_graph.py`, `test_environment.py`,
`workbench_endpoint.py`, `workbench_projection.py` and SPFx consumers.
The existing site-only Graph transport will not gain an open Team-path
allowance, but an exactly bound membership edge. Synchronize the Generic
Workbench, Workbench Live Read Binding, Matter Access Delegation and
Teams/SharePoint Data Plane contracts. AC-620-05 in the MVP acceptance contract
will distinguish nonmembers from members without individual assignments.
Do not reinterpret GitHub repository access rules as M365 Team rules or
remove them globally.

The main risk is conflating read authorization with a domain role. Add endpoint,
projection and action-boundary tests before implementation. Further negative
tests cover cross-Team/cross-tenant access, membership removal, paging,
malformed responses and missing Graph permissions. Preserve existing person
mapping, deputy and write-path tests.

No tenant writes, new login, new permission, automatic Team migration or
deployment through this specification. No weakening of secret protection,
domain approvals, #739 quarantine or #632 gates.

Next step after spec review: DE/EN plan, test-first local implementation,
independent review and focused tests before full completion gates.
