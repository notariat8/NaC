# Prompt-Vorlage Unternehmensgruendung

```text
Erstelle einen Gruendungsprozess.

Prozessklasse: formation
Vorhaben: <firma oder projektname>
Gesellschaftsform: <gmbh|ug|einzelunternehmen|...>
Sitz: <ort>
Gruendungsschritte:
- <schritt>
- <schritt>
Fristen:
- <datum>: <ereignis>
Verantwortliche:
- <rolle>: <name oder team>
Kommentar: <optional>
```

Erwartetes Ergebnis:

- eine JSON-Datei im Ordner `processes/formation/<jahr>/`
- Status `draft`
- eine Checkliste mit expliziten Zustaendigkeiten
