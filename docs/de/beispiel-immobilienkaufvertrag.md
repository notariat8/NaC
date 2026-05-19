# Beispiel: Immobilienkaufvertrag Ohne Echte Mandatsdaten

Dieses Beispiel zeigt den NaC-Ablauf an einem Immobilienkaufvertrag. Es nutzt
keine echten Namen, keine Adresse, keinen Kaufpreis und keinen Grundbuchauszug.

## 1. Vorgang Auswählen

Der Usecase liegt unter
[usecases/immobilienkaufvertrag/](../../usecases/immobilienkaufvertrag). Die
fachliche Vorderseite steht in
[usecases/immobilienkaufvertrag/README.md](../../usecases/immobilienkaufvertrag/README.md).

## 2. Offene Fragen Sichtbar Machen

```bash
python scripts/nac.py kg case immobilienkaufvertrag
```

NaC zeigt zum Beispiel offene Knoten für Objekt, Verkäufer, Käufer,
Kaufpreis, Belastungen, Finanzierung, Besitzübergang und Genehmigungen.

## 3. Fachliche Eingabe Nicht In Git Speichern

Echte Daten werden nicht eingetragen. Der öffentliche KG-Stand merkt nur:

- welche Angaben benötigt werden,
- wer sie fachlich prüft,
- welche Dokumente oder Nachweise referenziert werden,
- welche Gates vor Entwurf, Beurkundung oder Vollzug blockieren.

## 4. Sichere Editor-Sicht Anzeigen

```bash
python scripts/nac.py kg editor-view immobilienkaufvertrag
```

Die Editor-Sicht zeigt Formular- und Checklistenfelder. `value`-Felder bleiben
gesperrt, damit niemand versehentlich echte Mandatsdaten in Git schreibt.

## 5. Menschliche Freigabe Bleibt Entscheidend

Die KI kann strukturieren und Vollständigkeit vorbereiten. Die notarielle
Prüfung, Entwurfsfreigabe, Beurkundungsentscheidung und Vollzugsfreigabe
bleiben menschliche Verantwortung.

## 6. Nachweis Statt Akteninhalt

NaC speichert im Muster nur Nachweis-Metadaten: Status, Referenz, Gate,
Freigabepunkt. Der eigentliche Grundbuchauszug, Ausweis, Vertrag oder
Zahlungsnachweis gehört in ein geprüftes Fachsystem, DMS oder einen
freigegebenen Nachweisspeicher.

## 7. Qualität Prüfen

```bash
python scripts/nac.py doctor --profile strict
```

Erst wenn das Gate gruen ist, gilt der technische Musterstand als konsistent.
Produktiver Betrieb beginnt trotzdem erst in einem privaten Fork mit lokalen
Rollen, Datenschutzklärung und Arbeitsplatzprüfung.
