# Rollenmodell: Generisch und fachspezifisch

## Ziel

Dieses Modell stellt sicher, dass:

- jede Person Tickets erstellen kann,
- nur qualifizierte Rollen fachkritische Schritte final entscheiden,
- Freigaben nachvollziehbar und revisionsfest dokumentiert sind.

## 1) Grundprinzip fuer alle Unternehmen

- Beobachten darf jede Rolle.
- Ein Ticket aufmachen darf jede Rolle.
- Selbst loesen darf jede Rolle nur innerhalb ihrer freigegebenen Kompetenz.
- Fachkritische Entscheidungen brauchen qualifizierte Rollen und ggf. Freigabe.

Beispiel: Wenn Kopierpapier fehlt, muss niemand Notar sein, um das zu melden.

## 2) Generische Mindestrollen

- `mitarbeiter`: darf melden, kommentieren, Status aktualisieren.
- `sachbearbeitung`: darf operative Tickets bearbeiten und abschliessen, sofern kein fachkritischer Impact.
- `prozessverantwortung`: darf Arbeitsregeln im Fachprozess freigeben.
- `freigabeverantwortung`: darf approval-pflichtige Schritte final freigeben.
- `revision_audit`: darf pruefen, aber nicht operativ entscheiden.
- `automation`: fuehrt technische Standardaufgaben aus, entscheidet nicht fachlich.

## 3) Fachspezifische Rollen (Beispiel Kanzlei)

- `anwalt_fachlich`: fachliche Entscheidung in Mandats-/RVG-relevanten Schritten.
- `reno`: operativer Ablauf, Fristen, Aktenkoordination.
- `refa`: organisationsnahe Sachbearbeitung und Ablaufunterstuetzung.
- `notar_fachlich` (nur Notariat): notarielle Freigaben.
- `steuerfachkraft` (nur Steuerbuero): deklarationsnahe Freigaben.

## 4) Qualifikation statt Titel

Entscheidend ist nicht nur die Stellenbezeichnung, sondern die dokumentierte Qualifikation.

Beispiel:

- `rechnung_rvg_erstellen`: erlaubt nur fuer Rollen mit `qualification: rvg_billing_trained`.

## 5) Entscheidungsmatrix (Self-Resolve vs Approval)

- `impact=low` und `compliance=none`: self-resolve erlaubt.
- `impact=medium` oder `financial=true`: review durch Prozessverantwortung.
- `impact=high` oder `legal=true`: approval durch freigabeberechtigte Fachrolle.

## 6) Workflow-Integration

```mermaid
flowchart TD
    Event[Ticket oder Anfrage] --> RoleCheck[Rolle und Qualifikation pruefen]
    RoleCheck --> ImpactCheck[Impact und Compliance pruefen]
    ImpactCheck --> SelfResolve{Self-Resolve erlaubt}
    SelfResolve -->|ja| Done[Ticket abgeschlossen]
    SelfResolve -->|nein| Review[Review durch zustaendige Rolle]
    Review --> Approval{Finale Freigabe noetig}
    Approval -->|ja| Approver[Freigabeverantwortung oder Fachrolle]
    Approval -->|nein| Done
    Approver --> Done
```

## 7) Gender und Rollennamen

Die interne Rollen-ID bleibt neutral und stabil, z. B. `anwalt_fachlich` als technische Kennung.
Die sichtbare Sprachform folgt `policies/culture-policy.yaml`.

Empfehlung:

- Technische IDs: neutral/stabil
- Sichttexte: je nach Policy (neutral, Paarform, etc.)
- Gleiche Rechte fuer alle Schreibformen
