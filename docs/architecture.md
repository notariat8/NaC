# Architektur

## Architekturrahmen

Diese Architektur folgt dem Modell `Organization as Code` mit `Enterprise GitOps` als Steuerungsprinzip.
`OaC8` ist die konkrete Auspraegung dieses Rahmens.

Referenz: `docs/organization-as-code-positioning.md`

## Schichten

1. `Prompt Frontend`
   Ein LLM oder Bot nimmt Anfragen in Alltagssprache entgegen und fuellt standardisierte Prozessantraege.
2. `Git Control Plane`
   Branches, Pull Requests, Reviews, Rulesets, Tags und Releases fuehren den offiziellen Lebenszyklus.
3. `Python Execution Plane`
   Die Engine validiert Schemas, prueft Zustandsuebergaenge, berechnet Folgewerte und erzeugt Zusammenfassungen.
4. `Automation Plane`
   GitHub Actions fuehren PR-Checks, periodische Prozesse und Genehmigungsgates aus.

## OaC-Layer-Mapping

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
    MainState --> Close["Tag oder Release fuer Abschluss"]
```

## Fachlicher Zustandsautomat

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Validated: schema und business rules
    Validated --> NeedsReview: sensitiver vorgang
    Validated --> Approved: auto-approval erlaubt
    NeedsReview --> Approved: reviewer stimmt zu
    Approved --> Executed: action oder cli fuehrt aus
    Executed --> Archived: merge tag release
    Approved --> Rejected: reviewer lehnt ab
    Rejected --> Draft: neuer entwurf
```

## Steuerung per GitHub Actions

### `validate-process.yml`

- startet auf `pull_request` und `workflow_dispatch`
- validiert geaenderte Prozessdateien
- erzeugt eine lesbare Zusammenfassung fuer Reviewer

### `run-process.yml`

- erlaubt einen gezielten manuellen Lauf fuer einen Vorgang
- nutzt den Python-CLI-Einstieg
- eignet sich fuer Bot-Aufrufe aus einem LLM-Frontend

### `monthly-close.yml`

- laeuft periodisch oder manuell
- aggregiert Buchungen und Rechnungen fuer einen Monatsabschluss
- erzeugt einen Abschlussbericht als Artefakt

## Governance-Mapping

- Pull Request: fachlicher Antrag
- Review: menschliche Freigabe
- Environment: harter Freigabepunkt fuer sensible Prozesse
- Ruleset: Repository-weite Durchsetzungsregel
- Tag: versionierter Abschluss
- Release-Artefakt: extern pruefbare Ableitung

## Referenz, Fork und Rueckfluss

```mermaid
flowchart TD
    RefModel["Referenz-Musterunternehmen"] --> BranchPack["Branchenmodul anwalt notariat steuer software"]
    RefModel --> GenericPack["Generische Kernprozesse"]
    GenericPack --> CompanyFork["Unternehmens-Fork"]
    BranchPack --> CompanyFork
    CompanyFork --> LocalChange["Lokale Aenderung als Change Request"]
    LocalChange --> LocalApprove["Lokale Freigabe und Versionierung"]
    LocalApprove --> CompanyRun["Betrieb im Unternehmen"]
    LocalApprove --> UpstreamProposal["Optionale Rueckgabe an Referenz"]
    UpstreamProposal --> RefReview["Review im Referenzgremium oder Verband"]
    RefReview --> RefModel
```

Operative Details sind ausgelagert nach:

- `docs/fork-and-release-operating-model.md`
- `docs/release-sync-playbook.md`
- `docs/parallelbetrieb-version-binding.md`
- `docs/issue-taxonomie-pro-repo.md`
- `docs/service-business-core-vertical-blueprint.md`
- `docs/vertical-starter-prozesskatalog.md`
- `docs/repo-refactor-plan-single-repo-modules.md`

## Python-Komponenten

- `models.py`: normalisierte Datenklassen fuer Prozessantraege
- `registry.py`: Prozessdefinitionen mit erlaubten Zustandsuebergaengen
- `schema_tools.py`: leichtgewichtige Validierung gegen JSON-Schemas
- `engine.py`: Orchestrierung, Idempotenzpruefung und Monatsabschluss
- `cli.py`: Kommandozeilenoberflaeche fuer lokale und CI-Laeufe
