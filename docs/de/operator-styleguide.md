# NaC Operator Styleguide

Status: Erstfassung für konsistente Büroführung am 2026-05-20

## Zweck

Die Operator-Webapp ist eine Arbeitsoberfläche für das Notariat, keine
Dokumentationsseite und kein freies Modellierungswerkzeug. Jede Ansicht muss
erkennen lassen:

- wo die Nutzerin steht,
- wie sie zurück zur Übersicht kommt,
- welche Aktionen tägliche Aktenarbeit sind,
- welche Aktionen Kanzlei-Stammdaten oder freigabepflichtige Änderungen
  betreffen,
- auf welcher Workflow- und Checklisten-Version eine Akte läuft.

Die Gestaltung orientiert sich an [WCAG 2.2 konsistenter Navigation](https://www.w3.org/TR/WCAG22/#consistent-navigation)
und an behördlichen Service-Mustern wie [GOV.UK Service Navigation](https://design-system.service.gov.uk/components/service-navigation/)
und [Navigate a service](https://design-system.service.gov.uk/patterns/navigate-a-service/).

## Navigationsregel

Jede Arbeitsansicht außerhalb der Übersicht erhält oben eine einfache
Textnavigation:

- `← Zurück` führt zur vorherigen App-Ansicht.
- `Übersicht` führt immer zur Vorgangsübersicht.

Diese Navigation ist keine große Aktionsschaltfläche. Sie ist Orientierung und
Rückweg. Primäre Schaltflächen bleiben fachlichen Aktionen vorbehalten.

## Aktionshierarchie

Vorgangskarten sind immer in drei Blöcke gegliedert:

| Block | Sichtbarkeit | Zweck | Zielgruppe |
| --- | --- | --- | --- |
| `Aktenverwaltung` | immer offen | Akten öffnen, neue Demo-Akte anlegen, Statuszähler sehen | Büroalltag, alle berechtigten Nutzer |
| `Kontrolle` | immer offen, aber nachgeordnet | Checkliste prüfen | Sachbearbeitung, Notar, Qualitätskontrolle |
| `Kanzlei-Workflow` | eingeklappt | Ablauf ansehen, Änderung vorschlagen | Notar, Prozessverantwortliche, Review |

`Akten öffnen` ist die primäre Tagesaktion. `Neu` ist sekundär, weil zuerst
geklärt werden soll, ob bereits eine Akte oder ein Eingang existiert.
`Checkliste prüfen` ist nicht gleichwertig mit Aktenverwaltung, aber im
Büroalltag sichtbar. `Ablauf ansehen` und `Änderung vorschlagen` sind keine
täglichen Aktenaktionen; sie betreffen die freigegebenen Kanzlei-Stammdaten.

Die Checkliste ist deshalb keine reine Usecase-Vorlage. Die Usecase-Vorlage
definiert, welche Prüfpunkte es gibt. Beim Aktenstart wird daraus ein
aktenbezogener Checklistenstand erzeugt. Die Aktenansicht zeigt den nächsten
offenen Schritt, offene Punkte und erledigte Punkte aus genau diesem
aktenbezogenen Stand.

## Workflow Als Kanzlei-Stammdatum

Ein Workflow gehört nicht zur einzelnen Akte, sondern zum freigegebenen
Kanzlei-Standard je Usecase. Dazu gehören mindestens:

- BPMN-Ablauf,
- KG-/Checklisten-Artefakt,
- Version, z. B. `v1`,
- revisionsfester Hash der freigegebenen Artefakte,
- Freigabezustand und Freigaberolle.

Eine Änderung am Ablauf ist deshalb eine Änderung des Kanzlei-Workflows. Sie
darf nicht beiläufig aus einer Akte heraus erfolgen. Der erwartete Weg ist:

1. Änderung vorschlagen.
2. Validierung und fachliche Prüfung durchführen.
3. Notar oder Prozessverantwortlicher gibt neue Version frei.
4. Neue Akten nutzen ab dann die neue Version.
5. Laufende Akten bleiben auf ihrer gebundenen Version, bis ein dokumentierter
   Versionswechsel erfasst wird.

## Aktenbindung

Jede Akte erhält beim Anlegen ein `workflow_binding`-Metadatum. Dieses bindet
die Akte an:

- `workflow_id`,
- `workflow_version`,
- `workflow_revision_hash`,
- BPMN- und Checklisten-Artefakte mit SHA-256,
- Zeitpunkt der Bindung,
- Regel, dass die Akte auf dieser Version bleibt.

Damit kann eine Akte, die mit `Unterschriftsbeglaubigung v1` begonnen wurde,
auch nach Freigabe von `v2` weiter auf `v1` laufen. Ein Wechsel auf `v2` ist
eine eigene Aktenentscheidung und muss als Ereignis dokumentiert werden.

Der aktuelle MVP bindet Akten an `v1` plus Hash der vorhandenen BPMN- und
Checklisten-Artefakte. Für den produktiven Kanzleibetrieb braucht es zusätzlich
ein Freigaberegister je Kanzlei und Usecase mit Version, Freigabezeitpunkt,
Freigaberolle, freigebender Person, Gültigkeitsbeginn und Ablösungsregel.
Dieser Baustein ist im globalen Gantt als `Kanzlei-Workflow-Freigaberegister
bauen` vorgemerkt.

## Aktenbezogene Checkliste

Jede Akte erhält zusätzlich eine Datei `checkliste.json`. Diese Datei ist der
Fallstand der Checkliste, nicht nur ein Link auf die Vorlage. Sie enthält:

- die gebundene Workflow-Version,
- den Hash der KG-Checklisten-Vorlage,
- die Abschnitte `Offene Angaben`, `Dokumente`, `Entscheidungen`, `Prüfgates`
  und `Nachweise`,
- Status je Prüfschritt,
- den nächsten offenen Schritt für die Aktenübersicht.

Spätere Änderungen an der Kanzlei-Vorlage ändern diese Akten-Checkliste nicht
automatisch. Ein Wechsel auf eine neue Version braucht ein eigenes
Aktenereignis.

## Button-Regeln

- Pro Kontext gibt es höchstens eine primäre Schaltfläche.
- Primär ist nur die nächste normale Tagesaktion.
- Sekundäre Schaltflächen ergänzen die Tagesaktion.
- Governance-Aktionen werden in einem benannten Bereich gebündelt und nicht
  neben Tagesaktionen gestellt.
- Links zu Leseansichten bleiben klar als Links oder sekundäre Aktionen
  erkennbar.
- Schreibende oder freigaberelevante Aktionen brauchen Statusmeldung,
  Validierung und Review-Pfad.

## Begriffe

Die UI verwendet Bürobegriffe:

- `Übersicht` statt technischem Startpunkt,
- `Aktenverwaltung` für Akten öffnen und anlegen,
- `Kontrolle` für Checklistenprüfung,
- `Kanzlei-Workflow` für Ablauf und Bearbeitung,
- `Änderung vorschlagen` statt direktes Bearbeiten, wenn Stammdaten betroffen
  sind.
