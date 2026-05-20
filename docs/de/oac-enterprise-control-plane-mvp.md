# NaC Enterprise Control Plane MVP (6 Monate)

## Ziel und Rahmen

Dieses Dokument konkretisiert ein realistisches MVP für `Notariat as Code` im bestehenden Modell `NaC + Enterprise GitOps + NaC`.

Das MVP schließt einen kleinen, aber vollständigen End-to-End-Kreis:

- deklarative Änderung in Git,
- Policy- und Freigabeprüfung,
- Reconciliation in Zielsysteme,
- Audit- und Drift-Sichtbarkeit.

Default für synchrone Pilotpfade sind `software_company`, `notary` und `wealth_management`.
Branchenmodule bleiben über `policies/process-policy.yaml` umstellbar.

## MVP-Scope

Fokusdomäne:

- Org + Access + Tooling Onboarding.
- Zusätzlicher Branchenpfad als MVP-Use-Case: `property_management` (Hausverwaltung).

Enthaltene Change-Typen (Schema v1):

- `team`
- `role_change`
- `joiner_mover`

Nicht im MVP:

- Compensation,
- Performance Management,
- komplexe Finanzplanung,
- autonome AI-Freigaben für sensible Themen.

## Referenzfluss

```mermaid
flowchart TD
    A[PR mit Team oder Rollen-Änderung] --> B[Schema Validation]
    B --> C[Policy Check]
    C --> D[Plan Preview im PR]
    D --> E[Merge nach main]
    E --> F[Reconciler startet Connector-Tasks]
    F --> G[IAM GitHub Jira Slack]
    G --> H[Soll Ist Vergleich und Audit Events]
    H --> I[Drift oder Fehler als Event]
```

## Repository-Zuschnitt für den Pilot

- `org-model` bleibt im aktuellen Repo als modellierende Prozessartefakte (`processes/` + neue Change-Typen) umgesetzt.
- `policy-repo` entspricht den bestehenden Richtlinien unter `policies/`.
- `connector-config` wird initial als Konfigurationsdateien unter `docs/de/` und später als eigenes Verzeichnis ausgepraegt.
- `schemas/` enthält die maschinenprüfbaren Vertragsdefinitionen.

## 6-Monats-Plan

### Monat 1: Modell fixieren

- Kernobjekte und Change-Typen verbindlich machen.
- Zielsysteme für Pilot festlegen (IAM, GitHub, Jira).
- Policy-Minimum für Freigaben und SoD prüfbar machen.

### Monat 2: Validation und Policy

- CI validiert die neuen Schemas.
- Policy Checks liefern PR-fähiges Feedback.
- Plan-Preview als menschenlesbare Änderungsfolge.

### Monat 3: Reconciler + erster Connector

- Merge-Ereignis startet Reconciliation.
- Erste reale Zielsystem-Änderung reproduzierbar und idempotent.
- Audit Trail für jede Ausführung.

### Monat 4: Zwei weitere Connectoren

- IAM, GitHub, Jira integriert.
- Retry, Fehlerklassifikation, Idempotenzpfad stabil.

### Monat 5: Observability und Drift

- Soll/Ist-Abgleich mit klaren Drift-Signalen.
- Dashboard für Durchlaufzeit, Fehler und Governance.

### Monat 6: Pilotbetrieb

- Ein echter Bereich arbeitet produktiv über den Flow.
- `joiner_mover`, `team`, `role_change` laufen Ende-zu-Ende.
- KPI-Review mit Skalierungsentscheidung.

## KPI-Set für das MVP

Delivery:

- Lead Time pro Team- oder Rollenwechsel.
- Automationsquote gegen manuelle Tickets.

Governance:

- Policy Violations pro PR.
- Audit Coverage pro ausgeführter Änderung.

User Value:

- Time-to-access für neue Mitarbeitende.
- Time-to-team-setup für neue Teams.

Platform Health:

- Drift Rate.
- Reconciliation Latency.
- Connector Failure Rate.

## AI-Einsatz im MVP

Erlaubt:

- Planvorschläge, Policy-Erklärung, Priorisierungshilfen.

Nicht erlaubt:

- finale Freigaben in sensiblen HR/Finance/Security-Schritten.

Prinzip:

- AI schlägt vor, Menschen entscheiden.
