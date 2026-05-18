# Plugin Plan: Commercial Register bundesAPI Spike

Status: `deprecated`

## Core Decision

This document is retained as a spike assessment only. The current productive
plugin path is **not** a generic commercial-register scraping connector.

The repository `bundesAPI/handelsregister` may be useful for technical learning,
but it must not be adopted as a productive SaaS connector without license,
usage-terms, portal-boundary, rate-limit, data-protection and compliance review.

The active filing-oriented path is maintained in
[handelsregister-online-anmeldung.md](handelsregister-online-anmeldung.md).

## Goal

The spike may help evaluate:

- how commercial-register research can be represented as a plan,
- which metadata and evidence references are useful,
- which legal and technical boundaries block direct automation,
- how to avoid storing register documents or personal data by default.

## Non-Goals

- No productive scraping.
- No bypass of official portal usage terms.
- No high-volume lookup.
- No creation of a cross-customer register copy.
- No storage of real register documents in Git.
- No LLM processing of register documents without explicit policy approval.

## Day 0

- Check visible license and reuse permissions of the referenced spike.
- Check portal usage terms and legal basis.
- Decide whether the task is research evidence or filing preparation.
- Define allowed metadata and prohibited content.
- Keep all examples synthetic.

## Day 1

- Create only dry-run research plans.
- Capture purpose, search parameters, user role and case reference.
- Store metadata, hashes, source links and attestations by default.
- Keep retrieved documents in the customer DMS or official system unless a
  policy explicitly allows storage.

## Day 2

- Monitor rate-limit and portal-boundary risks.
- Review rejected or blocked research attempts as incidents.
- Reassess whether an official interface or manual evidence workflow is the
  better path.

## Adapter Boundaries

The adapter may:

- structure a research plan,
- record user attestation,
- hash imported evidence,
- document source and retrieval time.

The adapter must not:

- automate protected portals productively,
- circumvent rate limits or usage terms,
- use customer traffic to build a shared register database,
- write secrets or personal document content to Git.

## Source Assessment

The referenced open-source project is a spike input, not a production
dependency. Missing or unclear license information blocks code adoption.

## Acceptance Criteria For A Later Productive Connector

- Legal usage path is approved.
- License is compatible and documented.
- Rate limits and abuse controls are implemented.
- Evidence storage is metadata-first and tenant-isolated.
- Documents are hashed and stored only in approved systems.
- Every query has purpose, case reference, actor and timestamp.

## Sources

- Active filing path:
  [handelsregister-online-anmeldung.md](handelsregister-online-anmeldung.md)
- Register-related NaC plugin plans:
  [README.md](README.md)
