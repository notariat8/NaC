# Notary Usecases

This directory contains concrete notarial usecases. Usecases are separate from
installable plugins and reusable workflow execution logic. Static knowledge
graph state is case-local and belongs in the matching usecase folder.

## Boundary

- `plugins/` provides installable companion capabilities.
- `workflows/` provides reusable skills and deterministic Python workflow logic.
- `usecases/` describes concrete notarial business scenarios and their required
  plugin/workflow bindings.
- Each `usecases/<slug>/` folder owns its own static KG/DB files:
  `knowledge-graph.graph.json` for machine-readable state and
  `knowledge-graph.md` for human review.

## Canonical Top-10 Catalog

| Usecase | Folder | Status | Primary plugin dependencies |
| --- | --- | --- | --- |
| Immobilienkaufvertrag | `immobilienkaufvertrag/` | KG baseline | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| Grundschuld / Hypothekenbestellung | `grundschuld-hypothekenbestellung/` | KG baseline | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| GmbH-/UG-Gruendung | `online-gmbh-gruendung/` | KG baseline, active intake | `noc-regulated-core`, `noc-cyberjack-rfid`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-idaas` |
| Handelsregisteranmeldung | `handelsregisteranmeldung/` | KG baseline | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-cyberjack-rfid` |
| Beglaubigung von Unterschriften | `unterschriftsbeglaubigung/` | KG baseline | `noc-regulated-core`, `noc-idaas`, `noc-bnotk-xnp` |
| Testament / Erbvertrag | `testament-erbvertrag/` | KG baseline | `noc-regulated-core` |
| Erbscheinsantrag / Nachlassangelegenheiten | `erbscheinsantrag-nachlass/` | KG baseline | `noc-regulated-core` |
| Vorsorgevollmacht und Patientenverfuegung | `vorsorgevollmacht-patientenverfuegung/` | KG baseline | `noc-regulated-core`, `noc-idaas` |
| Schenkungsvertrag / Uebertragungsvertrag | `schenkungsvertrag-uebertragungsvertrag/` | KG baseline | `noc-regulated-core`, `noc-grundbuch-portal` |
| Ehevertrag / Scheidungsfolgenvereinbarung | `ehevertrag-scheidungsfolgenvereinbarung/` | KG baseline | `noc-regulated-core`, `noc-idaas`, `noc-grundbuch-portal` |

## Additional Active Intake Sources

| Usecase | Folder | Status | Primary plugin dependencies |
| --- | --- | --- | --- |
| AO52 nonprofit software company | `ao52aas-gemeinnuetzigkeit/` | Active intake | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-elster-eric` |
| Steuer-aaS tax readiness | `steuer-aas/` | Active intake | `noc-regulated-core`, `noc-elster-eric` |

## Canonical Next-10 Catalog

| Usecase | Folder | Status | Primary plugin dependencies |
| --- | --- | --- | --- |
| Loeschungsbewilligung / Grundbuchloeschung | `loeschungsbewilligung-grundbuchloeschung/` | KG baseline | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| Teilungserklaerung nach WEG | `teilungserklaerung-weg/` | KG baseline | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| Bautraegervertrag | `bautraegervertrag/` | KG baseline | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp`, `noc-idaas` |
| Gesellschafterbeschluss bei GmbH/UG | `gesellschafterbeschluss-gmbh-ug/` | KG baseline | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-cyberjack-rfid` |
| Geschaeftsanteilsuebertragung GmbH | `geschaeftsanteilsuebertragung-gmbh/` | KG baseline | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-idaas` |
| Vereinsregisteranmeldung | `vereinsregisteranmeldung/` | KG baseline | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-idaas` |
| Erbausschlagung | `erbausschlagung/` | KG baseline | `noc-regulated-core`, `noc-idaas` |
| Pflichtteilsverzicht / Erbverzicht | `pflichtteilsverzicht-erbverzicht/` | KG baseline | `noc-regulated-core`, `noc-idaas` |
| Adoption / familienrechtliche Erklaerungen | `adoption-familienrechtliche-erklaerungen/` | KG baseline | `noc-regulated-core`, `noc-idaas` |
| Vollmacht fuer Immobilien- oder Gesellschaftsgeschaefte | `vollmacht-immobilien-gesellschaftsgeschaefte/` | KG baseline | `noc-regulated-core`, `noc-idaas`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |

## Knowledge Graph Binding

The static KG is maintained inside each usecase folder:

- [immobilienkaufvertrag/knowledge-graph.graph.json](immobilienkaufvertrag/knowledge-graph.graph.json)
- [online-gmbh-gruendung/knowledge-graph.graph.json](online-gmbh-gruendung/knowledge-graph.graph.json)
- [bautraegervertrag/knowledge-graph.graph.json](bautraegervertrag/knowledge-graph.graph.json)
- [ao52aas-gemeinnuetzigkeit/knowledge-graph.graph.json](ao52aas-gemeinnuetzigkeit/knowledge-graph.graph.json)
- [steuer-aas/knowledge-graph.graph.json](steuer-aas/knowledge-graph.graph.json)

Every usecase folder must carry exactly one case-local KG graph and one Markdown
review view. Workflows should read that local KG as open-question state and
write updates through reviewed Git changes. Real mandate values must stay
outside the repository.

## Further Backlog Candidates

The next backlog candidates do not yet have canonical usecase folders. Once a
candidate becomes a usecase folder, it must receive its own
`knowledge-graph.graph.json` and `knowledge-graph.md` immediately:

- Genehmigungserklaerungen
- Rangruecktritt/Rangaenderung im Grundbuch
- Dienstbarkeiten
- Baulasten-bezogene Erklaerungen
- Niessbrauchsbestellungen
- Wohnrechte
- Auseinandersetzungsvertraege zwischen Erben
- Scheidungsimmobilien-Uebertragungen

## Intake Rule

External GitHub repositories that are really notarial usecases should be
canonicalized here. If an external repository is empty, only the canonical
folder and source reference are created here; no empty history is imported.

See `usecases/github-repo-intake.md` for the latest GitHub scan.

## Legacy Starter Aliases

`grundstueckskaufvertrag/` and `testament/` remain as older starter folders.
The canonical Top-10 entries are now `immobilienkaufvertrag/` and
`testament-erbvertrag/`.
