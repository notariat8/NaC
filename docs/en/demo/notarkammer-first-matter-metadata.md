# Notarkammer demo: first matter as metadata-only fixture

The fixture `tests/fixtures/demo/notarkammer-first-immobilienkaufvertrag.metadata.json`
describes the first presentable Immobilienkaufvertrag only as a
metadata-only starting point. It is not a matter file, not a production filing
and not a replacement for professional review.

It contains only safe demo metadata:

- demo identifiers for the notary office and matter
- Immobilienkaufvertrag as the primary matter type
- XNP/SNP as target systems only as metadata-only orientation
- references to BPMN, knowledge graph and cost-review module
- role classes instead of names
- document classes instead of document contents
- duration bands, parallel groups and critical-path markers
- guardrails for no mandate data, no production filing and no credentials
- guardrails for no OCI Apply, no secret material and no real register data

If design, release, apply or secret work is derived from this demo, it remains
outside this contract scope. The suggested gate set is: design review, release
review, apply approval, secret approval and professional notarial review.

Demo purpose: notariat8 can explain the first matter without showing mandate
data, identity documents, deeds, purchase prices, land-register data or
internal operating details.
