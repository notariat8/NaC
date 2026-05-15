# Testament / Erbvertrag

Status: KG baseline  
KG node: `case.testament_erbvertrag`  
Primary source anchors: BeurkG, BGB succession rules

## Goal

Prepare a notary-office usecase package for testamentary dispositions and
inheritance contracts. The workflow must support intake, drafting and execution
tracking while preserving the rule that capacity, free will, interpretation and
binding legal effects remain human notarial decisions.

## Scope

- Intake for testator identity, capacity flags, family situation, asset
  categories, wishes, prior dispositions, executor choices and custody route.
- Drafting support for testament, joint will or inheritance contract.
- Review gates for capacity, binding effects, revocations and custody.

## Out of Scope

- No automated final interpretation of testamentary wishes.
- No real estate, family or health details in Git.
- No replacement for notarial capacity and free-will review.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `testator.identity` | Who makes the disposition and how are identity and capacity reviewed? | Notary | Personal data |
| `capacity.flags` | Are there capacity, language, health or support flags? | Notary | Sensitive personal data |
| `family.structure` | Which spouse, children, relatives or dependents are relevant? | Testator | Family data |
| `assets.categories` | Which asset categories are relevant without storing values in Git? | Testator | Financial data |
| `dispositions.wishes` | Who should inherit or receive legacies and under which conditions? | Testator | Sensitive personal data |
| `prior.dispositions` | Which prior wills or inheritance contracts exist? | Notary | Sensitive legal data |
| `executor.choice` | Should executor, substitute heirs or administration rules be included? | Testator | Sensitive personal data |
| `custody.register` | Which custody and central register route applies? | Notary clerk | Mandate metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Draft testament or inheritance contract | Human-reviewed draft. | Synthetic or metadata only. |
| Prior dispositions reference | Checks revocation and binding effects. | Evidence reference only. |
| Capacity and instruction evidence | Supports notarial review. | Evidence reference only. |
| Custody and registration trace | Tracks post-execution handling. | Metadata only. |

## Decisions

- Instrument type: single testament, joint will or inheritance contract.
- Whether executor provisions are included.
- Whether prior dispositions are revocable, binding or unclear.
- Whether special communication, witnesses or support are needed.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Capacity and free-will review | Notary | Execution |
| Binding effects and revocation review | Notary | Draft release |
| Draft read, approved and signed | Notary | Custody |
| Custody and register handling complete | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Regulated intake, review and evidence model. |

## Workflow Dependencies

- `workflows/contracts/`: sensitive intake and approval contract.
- `workflows/python/`: deterministic completeness and red-flag checks.

## Delivery Tasks

1. Convert KG nodes into a sensitive estate-intake schema.
2. Add capacity and free-will red-flag checklist.
3. Add prior-disposition review placeholder and blocking logic.
4. Add custody/register state model.
5. Validate with synthetic family and estate-category fixtures.

## Acceptance Criteria

- Capacity and prior-disposition gates block draft release where incomplete.
- Asset information is stored only as category metadata.
- Custody/register evidence can be tracked without real mandate data.
- Legacy starter `usecases/testament/` remains as non-canonical starter.

