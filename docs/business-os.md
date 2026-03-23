# Fachkonzept: Git als Business-OS

## Leitprinzip

Git wird als versioniertes Betriebssystem fuer Geschaeftsprozesse verstanden. Nicht die Benutzeroberflaeche, sondern der nachvollziehbare Zustandswechsel ist die fachliche Wahrheit. Ein Vorgang ist erst dann wirksam, wenn er:

1. als strukturierter Antrag vorliegt,
2. die fachliche Validierung besteht,
3. die erforderlichen Freigaben durchlaufen hat,
4. in den verbindlichen Hauptstand uebernommen wurde.

## Rollenmodell

- `requester`: startet einen Vorgang per Prompt.
- `operator`: pflegt Vorlagen, Schemas und Regelwerke.
- `reviewer`: gibt sensible Vorgange fachlich frei.
- `approver`: entscheidet ueber Zahlung, Rechnungsausgang oder Steuerabgabe.
- `auditor`: prueft Historie, Nachweise, Status und Abschluesse.
- `automation`: GitHub Actions und Python-Engine fuehren deterministische Schritte aus.

## Prozessdomänen

### Gruendung

Die Gruendung wird als Folge von kontrollierten Checkpoints gefuehrt:

- Gesellschaftsform festlegen
- Gruendungsdokumente erstellen
- Register- und Steueranmeldung vorbereiten
- Bankkonto, Rollen und Bevollmaechtigungen einrichten
- Laufende Compliance-Fristen anlegen

Typische Zustaende:

- `draft`
- `validated`
- `needs_review`
- `approved`
- `executed`
- `archived`

### Rechnungsstellung

Rechnungen werden als versionierte Vorgangsobjekte modelliert. Die Engine vergibt oder validiert Nummernkreise, prueft Pflichtfelder und erzeugt exportfaehige Artefakte.

Typische Zustaende:

- `draft`
- `approved`
- `issued`
- `paid`
- `cancelled`

### Buchfuehrung

Buchfuehrung wird als wiederholbarer Transformationsprozess verstanden: Aus Eingangsereignissen wie Rechnung, Zahlung oder Beleg entsteht ein idempotenter Buchungssatz. Git fuehrt Nachweis, Freigabe und Historie; Python fuehrt die Kontierungslogik aus.

Typische Zustaende:

- `draft`
- `validated`
- `posted`
- `closed`

### Steuer

Steuerfaelle aggregieren periodische Daten, dokumentieren Entscheidungen und fuehren zur vorbereiteten Abgabe. Die Abgabe selbst kann je nach rechtlichem Umfeld in ein externes Fachsystem muenden; Git bleibt die kontrollierende Nachweisschicht.

Typische Zustaende:

- `draft`
- `prepared`
- `approved`
- `submitted`
- `archived`

## Datenprinzipien

- Das LLM darf Eingaben strukturieren, aber keine fachliche Gueltigkeit behaupten.
- Deterministische Python-Logik entscheidet ueber Statuswechsel.
- Personenbezogene Daten sollen minimiert oder referenziert werden.
- Jeder wirksame Geschaeftsvorfall erhaelt einen stabilen `request_id`.
- Idempotenzschluessel verhindern doppelte Ausfuehrung.

## Git als Steuerungsschicht

- Ein Branch oder Pull Request repraesentiert Arbeit am Vorgang.
- Reviews repraesentieren Fachfreigaben.
- Merge nach `main` repraesentiert die verbindliche Uebernahme.
- Tags repraesentieren Abschluesse wie `close/2026-03`.
- Releases oder Artefakte repraesentieren exportierte Nachweise.

## Grenzen des Modells

- Git ist kein hochvolumiges Transaktionssystem.
- Git ist kein Ersatz fuer gesetzlich vorgeschriebene Portale oder Schnittstellen.
- Geheimnisse und besonders schutzbeduerftige Dokumente gehoeren nicht unverschluesselt ins Repository.
- Rechtliche Freigaben brauchen klar definierte Verantwortlichkeiten ausserhalb des LLM.
