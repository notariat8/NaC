# Architektur

## Architekturrahmen

Diese Architektur folgt dem Modell `Notariat as Code` mit `Enterprise GitOps` als Steuerungsprinzip.
`NaC` ist die konkrete Ausprägung dieses Rahmens.

Referenz: `docs/de/organization-as-code-positioning.md`

Das operative CLI-first-Ausführungsmodell steht in
[ausfuehrungsmodell.md](ausfuehrungsmodell.md).

## Schichten

1. `Prompt Frontend`
   Ein LLM oder Bot nimmt Anfragen in Alltagssprache entgegen und fuellt standardisierte Prozessanträge.
2. `Git Control Plane`
   Branches, Pull Requests, Reviews, Rulesets, Tags und Releases führen den offiziellen Lebenszyklus.
3. `Python Execution Plane`
   Die Engine validiert Schemas, prüft Zustandsübergaenge, berechnet Folgewerte und erzeugt Zusammenfassungen.
4. `Automation Plane`
   GitHub Actions führen PR-Checks, periodische Prozesse und Genehmigungsgates aus.

## NaC-Layer-Mapping

```mermaid
flowchart LR
  intentLayer[IntentLayerPoliciesRolesProcesses] --> controlLayer[ControlLayerPRReviewApproval]
  controlLayer --> executionLayer[ExecutionLayerRuntimeAutomation]
  executionLayer --> evidenceLayer[EvidenceLayerImmutableEventJournal]
```

## Datenfluss

```mermaid
flowchart TD
    User["Fachanwender"] --> Prompt["LLM Prompt Frontend"]
    Prompt --> Draft["JSON Prozessantrag"]
    Draft --> GitChange["Branch oder Pull Request"]
    GitChange --> Validate["Python Validierung"]
    Validate --> Review["Review und Rulesets"]
    Review --> Runtime["GitHub Actions Runtime"]
    Runtime --> Outputs["Berichte Exporte Artefakte"]
    Runtime --> MainState["Verbindlicher main Stand"]
    MainState --> Close["Tag oder Release für Abschluss"]
```

## Fachlicher Zustandsautomat

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Validated: schema und business rules
    Validated --> NeedsReview: sensitiver vorgang
    Validated --> Approved: auto-approval erlaubt
    NeedsReview --> Approved: reviewer stimmt zu
    Approved --> Executed: action oder cli führt aus
    Executed --> Archived: merge tag release
    Approved --> Rejected: reviewer lehnt ab
    Rejected --> Draft: neuer entwurf
```

## Steuerung per GitHub Actions

### `validate-process.yml`

- startet auf `pull_request` und `workflow_dispatch`
- validiert geänderte Prozessdateien
- erzeugt eine lesbare Zusammenfassung für Reviewer

### `run-process.yml`

- erlaubt einen gezielten manuellen Lauf für einen Vorgang
- nutzt den Python-CLI-Einstieg
- eignet sich für Bot-Aufrufe aus einem LLM-Frontend

Die lokale Operator-Webapp ist ein Bedienkanal für Arbeitsplatz-Gates. Sie
führt NaC nicht remote aus, sondern spricht eine per `nac operator --open`
gestartete `127.0.0.1`-Bridge an, die freigegebene lokale Prüfskripte im
Workspace startet und minimierte Readiness-Metadaten zurückgibt.

### `monthly-close.yml`

- läuft periodisch oder manuell
- aggregiert Buchungen und Rechnungen für einen Monatsabschluss
- erzeugt einen Abschlussbericht als Artefakt

## Governance-Mapping

- Pull Request: fachlicher Antrag
- Review: menschliche Freigabe
- Environment: harter Freigabepunkt für sensible Prozesse
- Ruleset: Repository-weite Durchsetzungsregel
- Tag: versionierter Abschluss
- Release-Artefakt: extern prüfbare Ableitung

## Referenz, Fork und Rückfluss

```mermaid
flowchart TD
    RefModel["Referenz-Musterunternehmen"] --> BranchPack["Branchenmodul anwalt notariat steuer software"]
    RefModel --> GenericPack["Generische Kernprozesse"]
    GenericPack --> CompanyFork["Unternehmens-Fork"]
    BranchPack --> CompanyFork
    CompanyFork --> LocalChange["Lokale Änderung als Change Request"]
    LocalChange --> LocalApprove["Lokale Freigabe und Versionierung"]
    LocalApprove --> CompanyRun["Betrieb im Unternehmen"]
    LocalApprove --> UpstreamProposal["Optionale Rückgabe an Referenz"]
    UpstreamProposal --> RefReview["Review im Referenzgremium oder Verband"]
    RefReview --> RefModel
```

Operative Details sind ausgelagert nach:

- `docs/de/operations/fork-and-release-operating-model.md`
- `docs/de/operations/release-sync-playbook.md`
- `docs/de/operations/parallelbetrieb-version-binding.md`
- `docs/de/issues/taxonomy.md`
- `docs/de/service-model/core-vertical-blueprint.md`
- `docs/de/service-model/vertical-starter-process-catalog.md`
- `docs/de/operations/single-repo-refactor-plan.md`

## Python-Komponenten

- `models.py`: normalisierte Datenklassen für Prozessanträge
- `registry.py`: Prozessdefinitionen mit erlaubten Zustandsübergaengen
- `schema_tools.py`: leichtgewichtige Validierung gegen JSON-Schemas
- `engine.py`: Orchestrierung, Idempotenzprüfung und Monatsabschluss
- `cli.py`: Kommandozeilenoberfläche für lokale und CI-Läufe
- `scripts/nac_hw_bridge.py`: per `nac operator` gestartete Localhost-Bridge
  für die lokale Operator-Webapp und Hardware-Readiness-Prüfungen
