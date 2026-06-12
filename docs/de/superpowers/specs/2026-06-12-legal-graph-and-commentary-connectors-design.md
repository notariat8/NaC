# Legal-Graph- und Kommentar-Connector-Design

Datum: 2026-06-12

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: legal-graph-commentary-connectors
leading_issue: https://github.com/notariat8/NaC/issues/103
risk_gate: External Service
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
validation_commands:
  - env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests -p 'test_*.py'
  - GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

## Entscheidung

NaC bekommt einen domänenfähigen Rechtsgraphen nach dem Muster
`amtliche Quellen -> Normalisierung -> Legal Knowledge Graph -> Review und
Bedienkante`. Der erste lieferbare MVP ist Erbrecht. Familienrecht und
Gesellschaftsrecht folgen auf derselben Architektur.

Der Rechtsgraph besteht aus zwei bewusst getrennten Tracks:

1. **Primärquellen-Graph:** amtliche Normen, Rechtsprechung, Fundstellen,
   Fassungen, Inkrafttreten, NaC-Usecase-Bezüge, Prüfpunkte und Evidence.
2. **Kommentar-Connector-Track:** lizenzierte Fachkommentare und
   Verlagsdatenbanken werden nur über geprüfte MCP- oder API-Anbindungen
   angebunden. NaC speichert keine Kommentar-Volltexte im Produktrepo.

Kommentarhinweise dürfen nie als alleinige notarielle Wahrheit behandelt
werden. Sie sind externe Recherche- und Review-Signale mit Lizenz-, Quellen-,
Datenschutz-, Berufsgeheimnis- und Attributionsgrenzen.

## Quellenrahmen

Der Primärquellen-Track nutzt nur Quellen, deren Nutzung und Aktualisierung
geprüft werden können:

- [Rechtsprechung im Internet](https://www.rechtsprechung-im-internet.de/jportal/portal/page/bsjrsprod.psml):
  ausgewählte Entscheidungen ab 2010, anonymisiert, grundsätzlich ungekürzt,
  täglich aktualisiert und in angebotenen Formaten frei nutzbar.
- [Gesetze im Internet](https://www.gesetze-im-internet.de/): nahezu das
  gesamte aktuelle Bundesrecht.
- [digitalservicebund/ris-search](https://github.com/digitalservicebund/ris-search):
  öffentlicher NeuRIS-/RIS-Suchdienst-Stack für Normen und Rechtsprechung als
  zukünftiger Integrations- und Beobachtungskandidat.
- [TaxGraph](https://tax-graph.com/) als Produktreferenz für den Architekturtyp:
  Primärquellen werden normalisiert, graphbasiert verknüpft und über
  MCP/A2A-fähige KI-Umgebungen nutzbar gemacht.

Der Kommentar-Connector-Track dokumentiert Kandidaten wie beck-online, juris,
Wolters Kluwer oder andere Fachquellen erst als Kandidaten. Aktivierung braucht
vorher mindestens Lizenzprüfung, API-/MCP-Vertrag, Credential-Grenze,
AVV-/DPA-Prüfung bei personenbezogenen Daten, Berufsgeheimnisprüfung,
AI-SBOM-Entscheidung, Quellenattribution und menschliches Review-Gate.

## Architektur

1. **Source Watcher** liest amtliche Feeds, API-, XML- oder Suchquellen und
   speichert Abrufmetadaten, URL, Zeitstempel und Hash.
2. **Normalizer** extrahiert Normgliederung, Fundstelle, Fassung,
   Inkrafttreten, Gericht, Datum, Aktenzeichen, Normzitate und Quellenhash.
3. **Legal Graph Builder** erzeugt Knoten und Kanten für Normen,
   Entscheidungen, Rechtsgebiete, notarielle Usecases, Prüfpunkte, Evidence
   und Reviewstatus.
4. **Graph Patch Pipeline** erzeugt strukturierte Änderungsvorschläge:
   neue Knoten, geänderte Fassungen, neue Zitatkanten, betroffene Usecases und
   Risiko-/Reviewhinweise.
5. **Validatoren** prüfen Schema, Quellenstatus, Hashes, verbotene Daten,
   Kommentar-Volltextfreiheit, Credential-Freiheit und Reviewpflicht.
6. **Bedienkanten** sind `nac legal-graph status`,
   `nac legal-graph review`, eine Operator-Lesefläche und später MCP/A2A
   für KI-Umgebungen.

Die fachliche Wahrheit entsteht erst durch validierten Patch, Diff,
menschliches Review und Merge. Ein automatischer Quellenlauf darf keine
ungeprüfte fachliche Änderung direkt in den freigegebenen Graphen mergen.

## Graph-Modell

Der MVP nutzt folgende Knoten:

- `legal_domain`: Erbrecht, später Familienrecht und Gesellschaftsrecht.
- `source_document`: amtliche Quelle mit URL, Abrufzeit, Format, Hash und
  Nutzungsstatus.
- `norm`: Gesetz, Paragraph, Absatz, Satz, Fassung, Fundstelle,
  Inkrafttreten und Außerkrafttreten.
- `decision`: Gericht, Datum, Aktenzeichen, Entscheidungsart, Normbezüge,
  Fundstelle, URL und Hash.
- `notarial_usecase`: NaC-Usecase wie Testament/Erbvertrag,
  Erbscheinsantrag, Erbausschlagung oder Pflichtteilsverzicht.
- `review_point`: Form, Geschäftsfähigkeit, Beteiligte, Frist,
  Registerbezug, Belehrung, Evidence oder anderes Human-Gate.
- `commentary_connector`: Anbieter, Lizenzstatus, MCP-/API-Modus,
  erlaubte Nutzung, verbotene Speicherung und Reviewpflicht.
- `graph_patch`: vorgeschlagene Änderung mit Quelle, betroffenen Knoten,
  Risiko, Reviewstatus und PR-Referenz.

Wichtige Kanten sind `cites`, `amends`, `valid_from`, `valid_until`,
`affects_usecase`, `supports_review_point`, `needs_commentary_review` und
`approved_by`.

## Erbrechts-MVP

Der erste MVP umfasst:

- relevante BGB-Erbrechtsnormen als strukturierte Normknoten,
- NaC-Usecases Testament/Erbvertrag, Erbscheinsantrag, Erbausschlagung und
  Pflichtteilsverzicht/Erbverzicht,
- ausgewählte amtliche Entscheidungen mit Normbezug,
- Reviewpunkte für Form, Geschäftsfähigkeit, Beteiligte, Fristen,
  Nachlassbezug, Belehrung und Evidence,
- `nac legal-graph status` als CLI-Status,
- `nac legal-graph review` oder gleichwertige Review-JSON-Ausgabe,
- Validatoren für Schema, Quellen, Patches und Connectorgrenzen.

Der MVP liefert keine Rechtsberatung, keine automatisierte finale
Notarentscheidung und keine Kommentarinhaltsspeicherung.

## Kommentar-Connector-Grenzen

Für Kommentare und Fachquellen gelten harte Grenzen:

- MCP/API statt Scraping oder Volltextimport.
- Keine Credentials, Tokens, Cookies oder Lizenzgeheimnisse im Repo.
- Keine Speicherung von Kommentar-Volltexten im Produktrepo.
- Nur Fundstellen, Antwortmetadaten, Lizenzstatus, Nutzungsstatus,
  Quellenattribution und Reviewnotizen dürfen gespeichert werden.
- Jede Aktivierung braucht Vertrag, Lizenzbasis, Datenklassenentscheidung,
  AVV-/DPA-Prüfung soweit relevant, AI-SBOM-Entscheidung und
  menschliche Freigabe.
- Kommentarhinweise sind externe Recherchehinweise und brauchen
  notarielle Bewertung.

## Aktualisierung Und Fehlerbehandlung

Die Aktualisierung läuft als kontrollierte Pipeline:

1. Quelle abrufen.
2. Inhalte normalisieren.
3. Hash- und Struktur-Diff bilden.
4. Graph-Patch vorschlagen.
5. Validatoren ausführen.
6. Diff und Risiko anzeigen.
7. Fachreview einholen.
8. Per PR oder Owner-Direct-Modus mergen.

Fehlerfälle:

- Quelle nicht erreichbar: letzter geprüfter Graph bleibt gültig, Update wird
  als Blocker protokolliert.
- Parser unsicher: Patchstatus `needs_human_mapping`, kein Auto-Merge.
- Widersprüchliche Fassungen: Review-Gate verlangt Fundstellenvergleich und
  Inkrafttretensprüfung.
- Kommentar-Connector ohne gültige Lizenz/API: Status `blocked_contract`.
- Mandatsdaten in Query oder Antwort: Verarbeitung abbrechen und
  Datenschutzfinding erzeugen.

## Tests Und Validierung

Akzeptanzkriterien:

- AC-001: Schema-Test für Legal-Graph-Dateien und Graph-Patches.
- AC-002: Golden-Fixture-Test: bekannte Erbrechtsnormen ergeben stabile Knoten und
  Kanten.
- AC-003: Diff-Test: eine Quellenänderung erzeugt einen Patch, aber keinen
  ungeprüften Graph-Merge.
- Connector-Policy-Test: kein Credential, kein Kommentar-Volltext,
  Lizenzstatus Pflicht.
- CLI-Test für `nac legal-graph status` und `nac legal-graph review`.
- Strict Quality Gate bleibt grün.

## Lieferbare Roadmap

1. **M1 Vertrag:** Legal-Graph- und Commentary-Connector-Verträge,
   Datenklassen, Roadmap-Eintrag und Validator-Schnittstellen.
2. **M2 Erbrecht-MVP:** Norm-/Usecase-Knoten, Validator, CLI-Status und
   Review-JSON.
3. **M3 Update-Lauf:** Quellen-Diff, Patch-Vorschläge und PR-fähige
   Review-Artefakte.
4. **M4 Ausbau:** Familienrecht, Gesellschaftsrecht und lizenzierte
   Kommentar-MCP/API-Piloten.

## Nichtziele

- Keine autonome Rechtsberatung.
- Kein produktiver Kommentarzugriff ohne Lizenz-/API-Vertrag.
- Keine Speicherung echter Mandatsdaten im Produktrepo.
- Keine Verlagsvolltexte im Produktrepo.
- Keine ungeprüften automatischen Änderungen an freigegebenen NaC-Usecases.
