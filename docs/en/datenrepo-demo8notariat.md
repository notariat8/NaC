# Data Repository: demo8notariat

NaC separates product logic from case data. The product repository `ofunk/NaC`
contains usecases, BPMN models, plugins, rules, validators and documentation.
The data repository `ofunk/demo8notariat` is a separate target for synthetic
demo and test data.

## Folder Layout

The local clone should sit next to NaC:

```text
/home/ubuntu/NaC
/home/ubuntu/demo8notariat
```

The data repository is not kept as a subfolder of NaC. This keeps case data
from accidentally landing in the product repository.

## Initialization

```bash
python scripts/nac.py tenant init \
  --repo ../demo8notariat \
  --name demo8notariat \
  --remote-url https://github.com/ofunk/demo8notariat.git
```

The command creates a `.nac-tenant.json` manifest, standard folders and guidance
files. The manifest marks the repository as demo mode.

## Check Status

```bash
python scripts/nac.py tenant status --repo ../demo8notariat
```

The check shows manifest, Git status, remote and existing demo cases.

## Write Demo Data

```bash
python scripts/nac.py tenant write-demo immobilienkaufvertrag \
  --repo ../demo8notariat \
  --case-id DEMO-2026-0001
```

NaC creates a synthetic case file at `daten/demo/DEMO-2026-0001/case.json`.
The file contains only empty, metadata-only working state from the NaC usecase.
Real mandate data, PINs, card raw data, credentials, ID data and register
extracts are prohibited.

## GitHub Today, Sovereign Git Later

GitHub is acceptable for demo data. For productive notary-office data, GitHub
is not the target system here. Production requires a reviewed sovereign/GDPR Git
provider or equivalent local Git infrastructure.

The NaC contract stays the same:

```bash
python scripts/nac.py tenant status --repo <datarepo>
python scripts/nac.py tenant write-demo <usecase> --repo <datarepo>
```

When the platform changes, the data repository remote changes. The NaC product
repository does not.
