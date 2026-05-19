# Data Repository: demo8notariat

NaC separates product logic from notary-office data. The product repository
`ofunk/NaC` contains usecases, BPMN models, plugins, rules, validators and
documentation. The data repository `ofunk/demo8notariat` is a separate target
for matters, participants, documents, events, exports and later production data
states.

For the demo, NaC writes synthetic data. The model is shaped so it can later
represent personal, case-related and document-heavy data.

## Folder Layout

The local clone should sit next to NaC:

```text
/home/ubuntu/NaC
/home/ubuntu/demo8notariat
```

The data repository is not kept as a subfolder of NaC. This keeps matter and
person data from accidentally landing in the product repository.

## Model Principle

The leading structure is JSON with stable IDs. Large files remain ordinary
files.

| Object | Path | Purpose |
| --- | --- | --- |
| Matter | `akten/<year>/<matter_id>/akte.json` | File number, status, notary, participants, documents and pointers. |
| Person or organization | `personen/<person_id>.json` | Master data, roles, display name and classification. |
| Document | `dokumente/<document_id>/metadata.json` | Title, type, matter reference, file paths and classification. |
| Binary file | `dokumente/<document_id>/original/*` | PDF, JPG, scan or other original file. |
| Matter event | `akten/<year>/<matter_id>/ereignisse.jsonl` | Timeline within one matter. |
| Journal | `journal/<year>/<month>/<date>.jsonl` | Repository-wide event stream. |
| Index | `index/*.json` | Read lists for the web app, search and Codex. |

The matter does not inline all data. It points to IDs:

```json
{
  "matter_id": "UVZ-2026-0001",
  "participant_person_ids": ["PER-DEMO-VERKAEUFER-ANNA-BERGER"],
  "document_ids": ["DOC-DEMO-2026-0001-GRUNDBUCH"]
}
```

Codex and the web app first load `akte.json` and then follow the IDs to people,
documents and events. This keeps each file small, diffable and readable across
many editors and many generations.

## Initialization

```bash
python scripts/nac.py tenant init \
  --repo ../demo8notariat \
  --name demo8notariat \
  --remote-url https://github.com/ofunk/demo8notariat.git
```

The command creates the manifest, model description, standard folders and
guidance files.

## Check Status

```bash
python scripts/nac.py tenant status --repo ../demo8notariat
```

The check shows manifest, Git status, remote, demo cases, matters, people and
documents.

## Write Sample Matter

```bash
python scripts/nac.py tenant write-sample-akte \
  --repo ../demo8notariat \
  --akten-id UVZ-2026-0001
```

NaC creates a synthetic real-estate purchase matter with matter JSON,
participants, document metadata, placeholders for PDF/JPG files, event log and
indices.

The older `tenant write-demo` command remains available as a KG-based demo
export:

```bash
python scripts/nac.py tenant write-demo immobilienkaufvertrag \
  --repo ../demo8notariat \
  --case-id DEMO-2026-0001
```

## GitHub Today, Sovereign Git Later

GitHub can be used for the demo. For production notary-office data, the same
model contract should move to a reviewed sovereign/GDPR Git provider or
equivalent local Git infrastructure.

When the platform changes, the data repository remote changes. The NaC product
repository and the matter structure do not.
