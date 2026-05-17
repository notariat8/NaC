# Beispiel: Immobilienkaufvertrag Ohne Echte Mandatsdaten

Dieses Beispiel zeigt den NoC-Ablauf an einem Immobilienkaufvertrag. Es nutzt
keine echten Namen, keine Adresse, keinen Kaufpreis und keinen Grundbuchauszug.

## 1. Vorgang Auswaehlen

Der Usecase liegt unter
[usecases/immobilienkaufvertrag/](../../usecases/immobilienkaufvertrag). Die
fachliche Vorderseite steht in
[usecases/immobilienkaufvertrag/README.md](../../usecases/immobilienkaufvertrag/README.md).

## 2. Offene Fragen Sichtbar Machen

```bash
python scripts/notary_kg.py --repo-root . case immobilienkaufvertrag
```

NoC zeigt zum Beispiel offene Knoten fuer Objekt, Verkaeufer, Kaeufer,
Kaufpreis, Belastungen, Finanzierung, Besitzuebergang und Genehmigungen.

## 3. Fachliche Eingabe Nicht In Git Speichern

Echte Daten werden nicht eingetragen. Der oeffentliche KG-Stand merkt nur:

- welche Angaben benoetigt werden,
- wer sie fachlich prueft,
- welche Dokumente oder Nachweise referenziert werden,
- welche Gates vor Entwurf, Beurkundung oder Vollzug blockieren.

## 4. Sichere Editor-Sicht Anzeigen

```bash
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
```

Die Editor-Sicht zeigt Formular- und Checklistenfelder. `value`-Felder bleiben
gesperrt, damit niemand versehentlich echte Mandatsdaten in Git schreibt.

## 5. Menschliche Freigabe Bleibt Entscheidend

Die KI kann strukturieren und Vollstaendigkeit vorbereiten. Die notarielle
Pruefung, Entwurfsfreigabe, Beurkundungsentscheidung und Vollzugsfreigabe
bleiben menschliche Verantwortung.

## 6. Nachweis Statt Akteninhalt

NoC speichert im Muster nur Nachweis-Metadaten: Status, Referenz, Gate,
Freigabepunkt. Der eigentliche Grundbuchauszug, Ausweis, Vertrag oder
Zahlungsnachweis gehoert in ein geprueftes Fachsystem, DMS oder einen
freigegebenen Nachweisspeicher.

## 7. Qualitaet Pruefen

```bash
python scripts/quality_gate.py --profile strict
```

Erst wenn das Gate gruen ist, gilt der technische Musterstand als konsistent.
Produktiver Betrieb beginnt trotzdem erst in einem privaten Fork mit lokalen
Rollen, Datenschutzklaerung und Arbeitsplatzpruefung.
