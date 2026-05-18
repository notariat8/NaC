# Plugin Plan: GitHub Control Plane

Status: `proposed`

## Ziel

GitHub bleibt die verbindliche GitOps-Steuerung fuer NaC:

- Branches und Pull Requests bilden fachliche Aenderungsantraege.
- Reviews und Checks bilden Freigaben.
- Issues und Projects bilden Arbeit, Risiken und Drift ab.
- Actions erzeugen reproduzierbare Validierungs- und Artefaktlaeufe.

## Day0

- Lokale GitHub-Authentifizierung einrichten:

```bash
gh auth status
```

- Repo-Zugriff pruefen:

```bash
git remote -v
git pull
```

- Rollen und GitHub-Identitaeten gegen `policies/github-identity-registry.json` pruefen.

## Day1

- Branchschutz und Review-Regeln fuer `main` aktivieren.
- Required Checks an bestehende Workflows binden:
  - `quality-gate.yml`
  - `validate-process.yml`
  - `privacy-and-secrets.yml`
  - `governance-policy-sync.yml`
- Issue-Templates fuer Compliance, Features und Bugs nutzen.
- Plan Preview fuer Connector-Aenderungen als PR-Kommentar oder Artefakt erzeugen.

## Day2

- Regelmaessige Rechte- und Rollenrezertifizierung.
- Offene Drift- und Compliance-Issues reviewen.
- Workflow-Fehler klassifizieren:
  - Policy-Fehler
  - Test-/Validierungsfehler
  - externe Integrationsfehler
  - manuelle Nacharbeit
- Releases fuer verbindliche Prozessversionen taggen.

## Connector-Grenzen

Der GitHub-Connector darf:

- Issues, PRs, Checks und Releases lesen.
- geplante Aenderungen als Branch/PR vorschlagen.
- Status und Audit-Evidence schreiben.

Der GitHub-Connector darf nicht:

- Review-Regeln umgehen.
- direkt an `main` vorbei schreiben.
- Secrets im Repo speichern.
- menschliche Freigaben fuer sensible Prozesse ersetzen.

## Akzeptanzkriterien

- `gh auth status` ist lokal gruen.
- Pull Requests erzwingen Review.
- Governance- und Quality-Gates laufen.
- Jeder Connector-Apply ist ueber PR, Check oder Audit-Event nachvollziehbar.
