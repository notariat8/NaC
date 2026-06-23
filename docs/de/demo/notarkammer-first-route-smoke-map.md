# Notarkammer-Demo: First-Route-Smoke-Map

Status: 2026-06-23

Diese Protected-PR-Checkliste ist der kürzeste Live-Validierungspfad für
den ersten Vorgang `Immobilienkaufvertrag`. Sie verbindet Login-Status, die
erste Vorgangs-Metadaten-Fixture, XNP/SNP-BPMN-Touchpoints und fail-closed
Grenzen, ohne Laufzeitverhalten zu ändern.

Scope: nur Dokumentation, Tests und synthetische Fixture-Referenzen. No OCI
writes, no secrets, no mandate data, no productive XNP action.

## Evidence-Anker

| Anker | Nachweis bereithalten | Demo-sichere Aussage |
| --- | --- | --- |
| `login_status` | `https://app.notariat8.de/login` oeffnet oder die vorbereitete Presenter-Ansicht greift. | Login ist eine Statusgrenze, keine Datenansicht. |
| `workspace_fail_closed` | `https://app.notariat8.de/workspace` bleibt ohne gültige Sitzung und Rolle geschlossen. | Ein geschlossener Workspace ist akzeptabler Nachweis, wenn Sitzung oder Rolle fehlen. |
| erster Vorgang als Metadaten | `tests/fixtures/demo/notarkammer-first-immobilienkaufvertrag.metadata.json` mit `DEMO-MATTER-IMMOBILIENKAUF-01`, `notarkammer-first-matter-demo/v0.1` und `xnp_snp_target_metadata_only`. | Der erste Vorgang ist metadata-only und verweist auf `notarkammer-first-matter-metadata.md`. |
| XNP/SNP-BPMN-Touchpoints | `bpmn/immobilienkaufvertrag.bpmn` und `notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md`. | XNP/SNP wird als modellierte Grenze für Nachweise, Parallelität und kritischen Pfad gezeigt. |

## Vierstufige Live-Validierung

| Step | Check | Go | Fallback |
| --- | --- | --- | --- |
| R1 | `https://app.notariat8.de/login` oeffnen und `login_status` beschreiben. | Sagen, dass der Login-Status sichtbar ist. | Vorbereitete Ansicht oder Sprechertext nutzen; keine Anbieter-Interna prüfen. |
| R2 | `https://app.notariat8.de/workspace` ohne versteckte Sitzungsannahme oeffnen. | Wenn Sitzung und Rolle vorhanden sind, nur sicheren Workspace-Shell-Status zeigen. | Wenn geschlossen, `workspace_fail_closed` als erwartete Schutzgrenze benennen. |
| R3 | Ersten Vorgang über `DEMO-MATTER-IMMOBILIENKAUF-01` zeigen. | Fixture-Metadaten, Vorgangstyp `immobilienkaufvertrag` und `bpmn/immobilienkaufvertrag.bpmn` verbinden. | Auf `notarkammer-first-matter-metadata.md` bleiben und metadata-only Scope erklären. |
| R4 | XNP/SNP- und BPMN-Evidence-Touchpoints erläutern. | Evidence-Matrix für Entwurf, Signatur, Vollzug und Ruecklaufklassen nutzen. | Auf BPMN- und Matrix-Dokumente wechseln; keinen produktiven Zugriff behaupten. |

## Grenzen, die live genannt werden

- no mandate data
- no secrets
- no productive XNP action
- no productive filing
- no OCI writes
- fail-closed ist ein gültiges Demo-Ergebnis
