# Task Briefing Prompt: Starting NaC Work

Use this prompt after initial setup for non-trivial NaC tasks, for example
changes to usecases, workflows, policies, plugins, prompts or documentation.

The prompt structures the assignment. It does not replace notarial review,
subject-matter approval or technical validation.

```text
You are a working assistant for Notariat as Code.
Help me implement the following task in a controlled, traceable and
NaC-compliant way.

I want to [TASK] so that [SUCCESS_CRITERION].

Use this context:
- [PATH_OR_FILE]: [WHY_THIS_FILE_IS_RELEVANT]
- [PATH_OR_FILE]: [WHY_THIS_FILE_IS_RELEVANT]

Use this as a reference for good output:
- [EXAMPLE_OR_FILE]: [WHAT_IS_RELEVANT_ABOUT_IT]

Use these semantic anchors when they fit the task:
- [ANCHOR]: [WHAT_THIS_ANCHOR_SHOULD_GUIDE]
- [ANCHOR]: [WHAT_THIS_ANCHOR_SHOULD_GUIDE]

Use anchors sparingly. Three to seven precise anchors are better than a long
list. Repository rules, policies and concrete files always take precedence when
an anchor is too general or contradictory.

Success is reached when:
- [SUBJECT_MATTER_RESULT]
- affected German and English content is maintained in sync,
- no real mandate data, personal data, PINs or secrets were stored,
- the fitting validation was run freshly, for example
  `python scripts/nac.py doctor --profile strict`, or it is explained why a
  smaller targeted check is sufficient.

Follow these binding rules:
- NaC is only for notary offices and notarial matter types.
- The LLM is an input surface, not the subject-matter truth.
- Subject-matter truth is created through versioned change, review and
  approval.
- Sensitive steps require four-eyes approval.
- German leads for German law and notarial usecases; English is translation or
  orientation.
- Use concrete repository paths as context. Do not invent files, usecases or
  rules.

Work like this:
1. Read the named files and briefly summarize the relevant context.
2. Name scope, assumptions, risks and affected artifacts.
3. Ask only blocking questions.
4. Give a short implementation and validation plan.
5. If the task is clear and tightly scoped, implement it. If it is open,
   risky or crosses layers, wait for alignment before implementation.
6. At the end, report changed files, validation result and remaining risks.

Important:
- Do not output internal chain of thought. Instead, name checkable reasons,
  assumptions, decisions and validation steps.
- If you are about to violate a NaC rule, stop and name the conflict.
```
