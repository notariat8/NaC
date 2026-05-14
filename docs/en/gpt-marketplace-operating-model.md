# GPT Marketplace Operating Model

## Purpose

This document separates NoC plugin development from the possible OpenAI
distribution channels. The repository continues to use `plugins/` for
installable artifacts, but every release must be assigned to a concrete OpenAI
channel before publication.

## Distribution Channels

| Channel | Target | Consequence for NoC |
| --- | --- | --- |
| Public GPT Store | Publicly discoverable GPT for notary offices | Use only when current OpenAI review, builder profile, policy requirements, and privacy URLs are satisfied. |
| GPT with Actions | GPT calls external APIs through Actions | Every Action needs valid privacy and terms links plus a reviewed data-processing boundary. |
| Workspace or Enterprise app | Internal or customer-specific app installation | Do not treat as a public GPT Store release; run as a workspace or enterprise pilot. |
| Local Codex plugin | Local development and operations companion | Remains repo-local and is not automatically a GPT Store artifact. |

## OpenAI Rule Check

Before release, check the current OpenAI state:

- GPTs can be private, shared by link, shared in a workspace, or published in
  the GPT Store.
- Public GPT Store publication can depend on plan, workspace policy, builder
  profile, and product or policy review.
- OpenAI Help articles indicate that GPTs with Apps may not be eligible for the
  public GPT Store and should be treated as workspace or company distribution.
- GPTs with Actions need a valid Privacy Policy URL.

Current sources:

- [GPTs in ChatGPT](https://help.openai.com/en/articles/8798889-how-can-i-use-gpts)
- [Sharing and publishing GPTs](https://help.openai.com/en/articles/8793007-getting-your-gpt-featured)
- [Building and publishing a GPT](https://help.openai.com/en/articles/8798878-building-and-publishing-a-gpt)

## NoC Rule

Every plugin under `plugins/` must be assigned to a distribution channel before
publication. The assignment is tracked in `plugins/GANTT.md` and in the relevant
plugin plan. Notary usecases under `usecases/` must not be published directly as
plugins; they bind plugins and workflows into a business package.
