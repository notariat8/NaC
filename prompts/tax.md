# Prompt-Vorlage Steuerfall

```text
Erstelle einen Steuerprozess.

Prozessklasse: tax
Steuerart: <ustva|jahreserklaerung|lohnsteuer|gewerbesteuer>
Periode: <yyyy-mm oder yyyy>
Eingangsquellen:
- <quelle>
Freigabepflicht: <ja|nein>
Externe Referenz: <fall-id>
Kommentar: <optional>
```

Erwartetes Ergebnis:

- eine JSON-Datei im Ordner `processes/tax/<jahr>/`
- Status `draft` oder `prepared`
- dokumentierte Quellen fuer spaetere Pruefung
