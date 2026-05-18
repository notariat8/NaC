# Fachkonzept: Notariat as Code mit NaC

## Leitprinzip

Git wird als versioniertes Betriebssystem für Geschäftsprozesse verstanden. Nicht die Benutzeroberfläche, sondern der nachvollziehbare Zustandswechsel ist die fachliche Wahrheit. Ein Vorgang ist erst dann wirksam, wenn er:

1. als strukturierter Antrag vorliegt,
2. die fachliche Validierung besteht,
3. die erforderlichen Freigaben durchlaufen hat,
4. in den verbindlichen Hauptstand übernommen wurde.

## Positionierung

- `Notariat as Code` beschreibt das übergeordnete Zielmodell.
- `Enterprise GitOps` beschreibt den operativen Änderungsfluss.
- `NaC` ist die konkrete Betriebsumsetzung in diesem Repository.

Referenz: `docs/de/organization-as-code-positioning.md`

## Rollenmodell

- `requester`: startet einen Vorgang per Prompt.
- `operator`: pflegt Vorlagen, Schemas und Regelwerke.
- `reviewer`: gibt sensible Vorgange fachlich frei.
- `approver`: entscheidet über Zahlung, Rechnungsausgang oder Steuerabgabe.
- `auditor`: prüft Historie, Nachweise, Status und Abschlüsse.
- `automation`: GitHub Actions und Python-Engine führen deterministische Schritte aus.

Erweiterung für den operativen Betrieb:

- Ticket erstellen darf jede Rolle (`everyone_can_open_ticket=true`).
- Selbst loesen ist nur innerhalb der freigegebenen Kompetenz erlaubt.
- Fachkritische Schritte laufen über Review/Approval je Impact und Compliance.
- Fachliche Spezialfälle können Qualifikationspflichten erzwingen (z. B. RVG-Rechnung).

Details: `docs/de/role-model.md` und `policies/role-model-policy.yaml`

## Prozessdomänen

### Gründung

Die Gründung wird als Folge von kontrollierten Checkpoints geführt:

- Gesellschaftsform festlegen
- Gründungsdokumente erstellen
- Register- und Steueranmeldung vorbereiten
- Bankkonto, Rollen und Bevollmaechtigungen einrichten
- Laufende Compliance-Fristen anlegen

Typische Zustände:

- `draft`
- `validated`
- `needs_review`
- `approved`
- `executed`
- `archived`

### Rechnungsstellung

Rechnungen werden als versionierte Vorgangsobjekte modelliert. Die Engine vergibt oder validiert Nummernkreise, prüft Pflichtfelder und erzeugt exportfähige Artefakte.

Typische Zustände:

- `draft`
- `approved`
- `issued`
- `paid`
- `cancelled`

### Buchführung

Buchführung wird als wiederholbarer Transformationsprozess verstanden: Aus Eingangsereignissen wie Rechnung, Zahlung oder Beleg entsteht ein idempotenter Buchungssatz. Git führt Nachweis, Freigabe und Historie; Python führt die Kontierungslogik aus.

Typische Zustände:

- `draft`
- `validated`
- `posted`
- `closed`

### Steuer

Steuerfälle aggregieren periodische Daten, dokumentieren Entscheidungen und führen zur vorbereiteten Abgabe. Die Abgabe selbst kann je nach rechtlichem Umfeld in ein externes Fachsystem muenden; Git bleibt die kontrollierende Nachweisschicht.

Typische Zustände:

- `draft`
- `prepared`
- `approved`
- `submitted`
- `archived`

## Datenprinzipien

- Das LLM darf Eingaben strukturieren, aber keine fachliche Gültigkeit behaupten.
- Deterministische Python-Logik entscheidet über Statuswechsel.
- Personenbezogene Daten sollen minimiert oder referenziert werden.
- Jeder wirksame Geschäftsvorfall erhält einen stabilen `request_id`.
- Idempotenzschlüssel verhindern doppelte Ausführung.

## Git als Steuerungsschicht

- Ein Branch oder Pull Request repraesentiert Arbeit am Vorgang.
- Reviews repraesentieren Fachfreigaben.
- Merge nach `main` repraesentiert die verbindliche Übernahme.
- Tags repraesentieren Abschlüsse wie `close/2026-03`.
- Releases oder Artefakte repraesentieren exportierte Nachweise.

## Generisch vs. branchenspezifisch

Die Prozesswelt wird in zwei Schichten organisiert:

- `generisch`: für alle Unternehmen nutzbar
- `branche`: zusätzliche Fachlogik je Unternehmensart

Beispielstruktur:

- generisch: Rollen, Freigaben, Rechnung, Buchführung, Steuer, Fristen
- branche anwaltskanzlei: Mandat, Fristenkontrolle, Aktenlogik
- branche notariat: Urkundenprozess, Vollzug, Registerkommunikation
- branche steuerbüro: Mandantenzyklen, Deklarationsablauf, Rückfragenmanagement
- branche softwareunternehmen: Release, Incident, SLA und Lizenznachweise
- branche schreinerei: Aufmass, Werkstattablauf, Montage und Gewährleistung

Die Kombination aus generisch + branche bildet die operative Prozesslandkarte des jeweiligen Unternehmens.

## Variantenfähigkeit statt Einheitsprozess

Unterschiedliche Unternehmen brauchen unterschiedliche Ausprägungen. Deshalb werden Varianten explizit versioniert:

- welche Variante gilt,
- für welche Einheit sie gilt,
- ab wann sie gilt,
- wer sie freigegeben hat.

So bleiben Unterschiede erlaubt, aber transparent und prüfbar.

Für den Mischbetrieb gilt zusätzlich:

- Version wird je Vorgang beim Start gebunden,
- laufende Vorgänge bleiben auf ihrer gebundenen Version,
- neue Releases gelten nur für neu gestartete Vorgänge.

Details: `docs/de/operations/parallelbetrieb-version-binding.md`

## Change Request und Vererbung

Empfohlenes Modell:

1. Referenzprozess (z. B. Verband oder Musterunternehmen)
2. Unternehmens-Fork mit lokaler Anpassung
3. Change Request mit Begründung und Nachweis
4. Review und Freigabe
5. Versionierte Übernahme in den lokalen Standard
6. optional Rückführung in den Referenzprozess

Dieses Modell erlaubt gemeinsames Lernen ohne Verlust der lokalen Steuerbarkeit.

## Grenzen des Modells

- Git ist kein hochvolumiges Transaktionssystem.
- Git ist kein Ersatz für gesetzlich vorgeschriebene Portale oder Schnittstellen.
- Geheimnisse und besonders schutzbedürftige Dokumente gehören nicht unverschlüsselt ins Repository.
- Rechtliche Freigaben brauchen klar definierte Verantwortlichkeiten außerhalb des LLM.
