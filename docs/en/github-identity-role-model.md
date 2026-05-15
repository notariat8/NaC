# GitHub Identity And Role Reference

## Can A Role Definition Live Directly In A GitHub Profile?

Short answer: not as a reliable, workflow-ready standard source for
subject-matter permissions.

GitHub profiles are meant for presentation, not as a binding permission
registry for domain roles.

## Binding Approach In This Repository

1. Technical role source in the repository:
   [policies/github-identity-registry.json](../../policies/github-identity-registry.json)
2. Role and qualification rules:
   [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)
3. Access and visibility rules:
   [policies/access-control-policy.yaml](../../policies/access-control-policy.yaml)
4. Onboarding questions and permissions:
   [policies/onboarding-flow.json](../../policies/onboarding-flow.json)

This makes the following auditable:

- which GitHub login has which technical role,
- which questions may be answered by which role,
- which qualifications are required for critical steps,
- which repository and issue visibility rules apply to employees and guests.

## Recommended Additional Safeguards

- GitHub Teams for technical access control at repository level.
- Optional IdP/SSO groups as an external governance source.
- Regular synchronization checks between team structure and registry file.
