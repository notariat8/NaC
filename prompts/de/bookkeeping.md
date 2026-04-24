# Prompt-Vorlage Buchfuehrung

```text
Erstelle einen Buchungsantrag.

Prozessklasse: bookkeeping
Belegtyp: <rechnung|zahlung|beleg>
Belegdatum: <yyyy-mm-dd>
Sollkonto: <konto>
Habenkonto: <konto>
Betrag: <wert>
Waehrung: EUR
Steuerschluessel: <optional>
Belegreferenz: <beleg-id>
Externe Referenz: <bank|shop|erp id>
Kommentar: <optional>
```

Erwartetes Ergebnis:

- eine JSON-Datei im Ordner `processes/bookkeeping/<jahr>/`
- Status `draft`
- ein `idempotency_key`, der Doppelbuchungen verhindert
