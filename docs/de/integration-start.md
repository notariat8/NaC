# Integrationsstart: Fachsysteme, Plugins Und Connectoren

Dieses Dokument richtet sich an Fachsystemanbieter, Integrationspartner und
technische Produktteams, die NoC mit bestehender Notariatssoftware, lokalen
Arbeitsplatzkomponenten oder Portalen verbinden wollen.

## Integrationsprinzip

NoC behandelt externe Systeme als getrennte Verantwortungs- und
Nachweisschichten. Das oeffentliche Repository modelliert:

- welche Informationen und Gates ein Vorgang braucht,
- welche Plugin-Readiness vorliegt,
- welche Nachweise referenziert werden,
- welche Datenklassen nicht in Git gespeichert werden duerfen,
- welche Schreibpfade erst nach Review freigegeben werden.

## Erwartete Integrationsformen

- lokaler Readiness-Check fuer Arbeitsplatz, Middleware und Kartenpfade,
- Connector-Vertrag fuer strukturierte Eingaben und Ausgaben,
- Evidence-Metadaten statt echter Dokumentinhalte,
- Trockenlauf und Planvorschau vor produktiven Schreibaktionen,
- explizite menschliche Freigabe fuer sensible Schritte.

## Was Ein Integrationspartner Liefern Sollte

1. Funktionsgrenzen und nicht automatisierbare Schritte.
2. Datenklassen und Speicherorte.
3. Fehler- und Supportmodell.
4. Versionierung und Kompatibilitaetsfenster.
5. Testmodus mit synthetischen Daten.
6. Nachweis, welche Aktion lokal, extern oder manuell ausgefuehrt wird.

## Relevante Repository-Bereiche

- [plugins/README.md](../../plugins/README.md)
- [workflows/README.md](../../workflows/README.md)
- [workflows/contracts/README.md](../../workflows/contracts/README.md)
- [docs/de/plugin-plans/README.md](plugin-plans/README.md)
- [docs/de/plugin-operations/README.md](plugin-operations/README.md)
- [docs/de/sbom-for-ai.md](sbom-for-ai.md)

## Leitplanke

Eine Integration ist fuer NoC erst belastbar, wenn sie lokal pruefbar,
datenschutzseitig eingeordnet, versioniert, testbar und durch einen
menschlichen Freigabeprozess begrenzt ist.
