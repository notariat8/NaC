# Maturity: What Is Usable Today

This page separates runnable core, pilot surfaces, planned work and deliberately
blocked automation. It helps decision makers assess NaC realistically.

## Maturity Matrix

| Area | State | What it means |
| --- | --- | --- |
| Clone and read the repository | Usable today | Structure, policies, usecases and start paths are publicly inspectable. |
| Run the unified `nac` CLI | Usable today | Status, KG, BPMN, configuration, web server and quality gate share one local operating surface. |
| Run the local quality gate | Usable today | Tests, language rules, privacy lint, plugin validation, KG validation and Gantt rules run locally. |
| Review usecase KGs | Usable today | Each usecase has a machine-readable KG and a human review view. |
| Show KG editor view | Usable today | Subject-matter staff can inspect open nodes as safe form/checklist views without editing `value` fields. |
| BPMN-js business layer | Profile present | BPMN 2.0 is the subject-matter process source; a first bpmn-js-ready model and Python validation exist. |
| Local web server | Usable today | BPMN models and KG editor views can be reviewed locally in the browser. |
| Private operating fork | Pilot-ready | A notary office can move the template into a private fork and define roles, approvals and local storage. |
| Local card/XNP readiness | Pilot-ready | Plugin paths first check technical readiness and metadata, not real signatures or productive filing. |
| System connectors | Planned / integration work | Write adapters need separate approval, privacy review, test mode and responsibility model. |
| Automatic register, portal or system filing | Deliberately blocked | No productive write action without reviewed connector, human approval and private operating frame. |
| Real mandate data in the public repo | Forbidden | Personal, register, financial, health, estate and family data do not belong in this repository. |
| AI as final legal decision | Forbidden | AI structures and prepares; human responsibility remains decisive. |

## Short Form For Decision Makers

NaC is strong today as an inspectable reference, local control framework and
pilot preparation. Productive office operation starts only in a private fork
with local systems, roles, privacy review and human approvals.

## Next Documents

- [docs/en/notar-start.md](notar-start.md)
- [docs/en/cli.md](cli.md)
- [docs/en/ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [docs/en/bpmn-js-business-layer.md](bpmn-js-business-layer.md)
- [docs/en/lokaler-webserver.md](lokaler-webserver.md)
- [docs/en/betriebsstart.md](betriebsstart.md)
- [docs/en/integration-start.md](integration-start.md)
- [docs/en/pruefung-standardisierung-start.md](pruefung-standardisierung-start.md)
