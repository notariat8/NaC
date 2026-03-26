# Fachkonzept: Organization as Code mit OaC8

## Leitprinzip

Git wird als versioniertes Betriebssystem fuer Geschaeftsprozesse verstanden. Nicht die Benutzeroberflaeche, sondern der nachvollziehbare Zustandswechsel ist die fachliche Wahrheit. Ein Vorgang ist erst dann wirksam, wenn er:

1. als strukturierter Antrag vorliegt,
2. die fachliche Validierung besteht,
3. die erforderlichen Freigaben durchlaufen hat,
4. in den verbindlichen Hauptstand uebernommen wurde.

## Positionierung

- `Organization as Code` beschreibt das uebergeordnete Zielmodell.
- `Enterprise GitOps` beschreibt den operativen Aenderungsfluss.
- `OaC8` ist die konkrete Betriebsumsetzung in diesem Repository.

Referenz: `docs/organization-as-code-positioning.md`

## Rollenmodell

- `requester`: startet einen Vorgang per Prompt.
- `operator`: pflegt Vorlagen, Schemas und Regelwerke.
- `reviewer`: gibt sensible Vorgange fachlich frei.
- `approver`: entscheidet ueber Zahlung, Rechnungsausgang oder Steuerabgabe.
- `auditor`: prueft Historie, Nachweise, Status und Abschluesse.
- `automation`: GitHub Actions und Python-Engine fuehren deterministische Schritte aus.

Erweiterung fuer den operativen Betrieb:

- Ticket erstellen darf jede Rolle (`everyone_can_open_ticket=true`).
- Selbst loesen ist nur innerhalb der freigegebenen Kompetenz erlaubt.
- Fachkritische Schritte laufen ueber Review/Approval je Impact und Compliance.
- Fachliche Spezialfaelle koennen Qualifikationspflichten erzwingen (z. B. RVG-Rechnung).

Details: `docs/role-model.md` und `policies/role-model-policy.yaml`

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

## Generisch vs. branchenspezifisch

Die Prozesswelt wird in zwei Schichten organisiert:

- `generisch`: fuer alle Unternehmen nutzbar
- `branche`: zusaetzliche Fachlogik je Unternehmensart

Beispielstruktur:

- generisch: Rollen, Freigaben, Rechnung, Buchfuehrung, Steuer, Fristen
- branche anwaltskanzlei: Mandat, Fristenkontrolle, Aktenlogik
- branche notariat: Urkundenprozess, Vollzug, Registerkommunikation
- branche steuerbuero: Mandantenzyklen, Deklarationsablauf, Rueckfragenmanagement
- branche softwareunternehmen: Release, Incident, SLA und Lizenznachweise
- branche schreinerei: Aufmass, Werkstattablauf, Montage und Gewaehrleistung

Die Kombination aus generisch + branche bildet die operative Prozesslandkarte des jeweiligen Unternehmens.

## Variantenfaehigkeit statt Einheitsprozess

Unterschiedliche Unternehmen brauchen unterschiedliche Auspraegungen. Deshalb werden Varianten explizit versioniert:

- welche Variante gilt,
- fuer welche Einheit sie gilt,
- ab wann sie gilt,
- wer sie freigegeben hat.

So bleiben Unterschiede erlaubt, aber transparent und pruefbar.

Fuer den Mischbetrieb gilt zusaetzlich:

- Version wird je Vorgang beim Start gebunden,
- laufende Vorgaenge bleiben auf ihrer gebundenen Version,
- neue Releases gelten nur fuer neu gestartete Vorgaenge.

Details: `docs/parallelbetrieb-version-binding.md`

## Change Request und Vererbung

Empfohlenes Modell:

1. Referenzprozess (z. B. Verband oder Musterunternehmen)
2. Unternehmens-Fork mit lokaler Anpassung
3. Change Request mit Begruendung und Nachweis
4. Review und Freigabe
5. Versionierte Uebernahme in den lokalen Standard
6. optional Rueckfuehrung in den Referenzprozess

Dieses Modell erlaubt gemeinsames Lernen ohne Verlust der lokalen Steuerbarkeit.

## Grenzen des Modells

- Git ist kein hochvolumiges Transaktionssystem.
- Git ist kein Ersatz fuer gesetzlich vorgeschriebene Portale oder Schnittstellen.
- Geheimnisse und besonders schutzbeduerftige Dokumente gehoeren nicht unverschluesselt ins Repository.
- Rechtliche Freigaben brauchen klar definierte Verantwortlichkeiten ausserhalb des LLM.
