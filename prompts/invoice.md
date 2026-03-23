# Prompt-Vorlage Rechnung

Nutze diese Struktur fuer das LLM-Frontend:

```text
Erstelle einen Rechnungsantrag.

Prozessklasse: invoice
Kunde: <name>
Leistungsdatum: <yyyy-mm-dd>
Faelligkeit: <yyyy-mm-dd>
Waehrung: EUR
Positionen:
- <beschreibung>, menge=<wert>, einzelpreis=<wert>, konto=<konto>
Steuersatz: <wert>
Externe Referenz: <crm- oder ticket-id>
Kommentar: <optional>
```

Erwartetes Ergebnis:

- eine strukturierte JSON-Datei im Ordner `processes/invoices/<jahr>/`
- Status `draft`
- stabiler `idempotency_key`
