# Integrationsstart: Fachsysteme, Plugins Und Connectoren

Dieses Dokument richtet sich an Fachsystemanbieter, Integrationspartner und
technische Produktteams, die NaC mit bestehender Notariatssoftware, lokalen
Arbeitsplatzkomponenten oder Portalen verbinden wollen.

## Integrationsprinzip

NaC behandelt externe Systeme als getrennte Verantwortungs- und
Nachweisschichten. Das öffentliche Repository modelliert:

- welche Informationen und Gates ein Vorgang braucht,
- welche Plugin-Readiness vorliegt,
- welche Nachweise referenziert werden,
- welche Datenklassen nicht in Git gespeichert werden dürfen,
- welche Schreibpfade erst nach Review freigegeben werden.

## Erwartete Integrationsformen

- lokaler Readiness-Check für Arbeitsplatz, Middleware und Kartenpfade,
- Connector-Vertrag für strukturierte Eingaben und Ausgaben,
- Evidence-Metadaten statt echter Dokumentinhalte,
- Trockenlauf und Planvorschau vor produktiven Schreibaktionen,
- explizite menschliche Freigabe für sensible Schritte.

## Was Ein Integrationspartner Liefern Sollte

1. Funktionsgrenzen und nicht automatisierbare Schritte.
2. Datenklassen und Speicherorte.
3. Fehler- und Supportmodell.
4. Versionierung und Kompatibilitätsfenster.
5. Testmodus mit synthetischen Daten.
6. Nachweis, welche Aktion lokal, extern oder manuell ausgeführt wird.

## Relevante Repository-Bereiche

- [plugins/README.md](../../plugins/README.md)
- [workflows/README.md](../../workflows/README.md)
- [workflows/contracts/README.md](../../workflows/contracts/README.md)
- [ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [docs/de/plugin-plans/README.md](plugin-plans/README.md)
- [docs/de/plugin-operations/README.md](plugin-operations/README.md)
- [docs/de/sbom-for-ai.md](sbom-for-ai.md)

## Leitplanke

Eine Integration ist für NaC erst belastbar, wenn sie lokal prüfbar,
datenschutzseitig eingeordnet, versioniert, testbar und durch einen
menschlichen Freigabeprozess begrenzt ist.
