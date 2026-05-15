# Security And GDPR Guideline

## Most Important Statement

It is never 100 percent guaranteed that sensitive content will not end up in a
repository. This pattern repository therefore combines rules, reviews and
automated scans.

## Binding Rules

- No real passwords, tokens, API keys or private keys.
- No real personal data in example files.
- Only synthetic test data and placeholders.
- Only test email addresses using example domains.

## Repository Safeguards

- Policy: [policies/data-protection-policy.yaml](../../policies/data-protection-policy.yaml)
- DPA section for OpenAI-backed processing:
  [docs/en/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md)
- DPA checklist for SaaS operations:
  [docs/en/avv-checkliste-eventlock-saas.md](avv-checkliste-eventlock-saas.md)
- PR checks: [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md)
- Secret scan in CI:
  [.github/workflows/privacy-and-secrets.yml](../../.github/workflows/privacy-and-secrets.yml)
- Privacy lint in CI:
  [.github/workflows/privacy-and-secrets.yml](../../.github/workflows/privacy-and-secrets.yml)

## Incident Response

1. Revoke or rotate the secret immediately.
2. Remove affected data from the repository and replace it.
3. Document the incident as an issue.
4. Review and improve the approval process.

## Note For Forks

Forks must adopt these rules as well. Recommended action after forking: actively
check the policies and workflows.
