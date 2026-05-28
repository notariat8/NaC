# Copilot Quickstart In 15 Minutes

## Target Group

For decision makers without specialist IT knowledge who want to start with
VS Code and GitHub Copilot.

## Minute 0-3: Check The Basics

- VS Code is installed.
- GitHub Copilot is enabled.
- The organization repository is open in VS Code.

## Minute 3-6: Read Mandatory Documents

Read in this order:

1. [docs/en/START_HERE.md](START_HERE.md)
2. [docs/en/fachanwender-guide.md](fachanwender-guide.md)
3. [policies/process-policy.yaml](../../policies/process-policy.yaml)
4. [policies/culture-policy.yaml](../../policies/culture-policy.yaml)
5. [policies/technology-policy.yaml](../../policies/technology-policy.yaml)

Goal: a shared baseline for roles, notarial usecases and language.

## Minute 6-9: Initialize Copilot With The Start Prompt

Use in Copilot Chat:

```text
Read these files:
- docs/en/START_HERE.md
- docs/en/fachanwender-guide.md
- policies/process-policy.yaml
- policies/culture-policy.yaml

Then explain without IT jargon:
1. Which three notarial usecases I should start first.
2. Which approvals are mandatory for those processes.
3. Which open decisions I need to make today.
```

## Minute 9-12: Choose The Notary-Office Path

Choose the notary-office onboarding prompt:

- Notary office: [prompts/en/onboarding/notary-first-setup.md](../../prompts/en/onboarding/notary-first-setup.md)

Synchronous MVP default in the reference repository: `notary`. Examples are
derived only from [usecases/](../../usecases), for example real-estate purchase
contract or signature certification.

## Minute 12-15: Start The Pilot Bindingly

- Define one pilot usecase, for example real-estate purchase contract or
  signature certification.
- Define reviewers and approval points.
- Start the first change request as a pull request.

## Result After 15 Minutes

You have:

- a concrete pilot focus,
- clear approval rules,
- a documented start point for the further rollout.
