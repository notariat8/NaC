# Implementation plan: Team membership as matter read access

Issue: [#620](https://github.com/notariat8/NaC/issues/620).
Spec: [Team read access](../specs/2026-10-03-team-member-matter-read-design.md).
Status: Owner approved the spec; local implementation, no deployment.

1. Plan → Review → Fix: verify trusted fixed MVP Team/site binding and
   complete direct membership evidence. No client-supplied roles.
2. Test-first: neutral access mode `team_member` and role `team_reader`;
   positive test without person mapping/individual assignment. Nonmember,
   other Team, wrong tenant, invalid IDs, paging and incomplete responses deny.
   No fallback to individual assignment for nonmembers.
3. GET edge: bound group metadata, group/site binding and members of the
   exactly configured MVP group. Accept only complete bounded responses;
   initially deny paginated responses rather than allowing partial evidence.
   No permission expansion or token/provider action in local tests.
   Concrete edges: `GET /groups/{boundTeamId}?$select=id,groupTypes,resourceProvisioningOptions`,
   `GET /groups/{boundTeamId}/sites/root?$select=id,webUrl` and
   `GET /groups/{boundTeamId}/members?$select=id&$top=100`.
   No OData type cast: it requires a potentially delayed index and additional
   advanced-query parameters. See the
   [official members API](https://learn.microsoft.com/en-us/graph/api/group-list-members?view=graph-rest-1.0).
   `{boundTeamId}` is the fixed provisioned MVP Team ID, not a request ID.
   Runtime membership reads need Application `GroupMember.Read.All` or proven
   existing stronger read permissions; site reads require existing
   `Sites.Selected` with a matching site grant or proven stronger permissions.
   Missing rights remain a separate live gate, not automatic consent.
4. Synchronize membership adapter, RawGraph transport and composition.
   Team read access requires no SharePoint person mapping. Preserve existing
   person and deputy logic separately for domain actions.
5. AccessDecision, endpoint, projection, DTO and SPFx carry `team_member` /
   `team_reader` without approval/write capabilities. Lease at most 300 seconds;
   no new cross-request membership cache.
6. Synchronize policies, agent mirrors, start documents, contracts, CLI
   documentation, AI-SBOM and affected validators. AC-620-05 becomes a
   nonmember negative test; Team members are positive cases.
7. Implement → Review → Fix: independent security and validation review,
   focused Python/SPFx tests, parity/traceability/governance, Graft and full
   Strict Doctor. Local commits; do not portray publication or live deployment
   as already completed or proven by spec approval.

Preserve the MVP allowlist; no general multi-matter/multi-tenant runtime.
Before live repair verify runtime GET permissions and release binding,
then perform controlled positive member and negative nonmember tests.
