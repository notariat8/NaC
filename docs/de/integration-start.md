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
- sichere Upload- und Leselinks für mobile App-, Object-Store-,
  Datenbank-Blob- oder OneDrive-Pfade,
- Trockenlauf und Planvorschau vor produktiven Schreibaktionen,
- explizite menschliche Freigabe für sensible Schritte.

## Mobile App Und Sichere Dokumentlinks

Eine Integration darf auch eine mobile Mandanten- oder Beteiligten-App
vorsehen, etwa als Demo-App `n8-demonotariat` im iOS-App-Store. Die App erhält
keinen pauschalen Zugriff auf NaC. Sie bekommt nur akten- und zweckgebundene
Links, nachdem Identität, Rolle, Vorgangsbezug und Freigabestatus geprüft
wurden.

Zulässige Zielmuster sind:

- Upload-Link in einen Object Store,
- Upload-Link in einen Datenbank-Blob,
- Upload- oder Leselink in OneDrive,
- read-only Link auf aktuelle Akteninformationen, soweit der Vorgang dies
  zulässt.

Die Links müssen kurzlebig, widerrufbar, protokolliert, mandantengebunden und
auf konkrete Aktionen begrenzt sein. Das Produktrepo speichert keine geheimen
Links, Zugangstoken oder Dokumentrohdaten. NaC hält nur Nachweise wie Hash,
Speicherzielklasse, Aktenbezug, Ablaufzeit, ausstellende Rolle,
Freigabestatus, Malware-/Dateitypprüfung und Auditereignis.

## Was Ein Integrationspartner Liefern Sollte

1. Funktionsgrenzen und nicht automatisierbare Schritte.
2. Datenklassen und Speicherorte.
3. Fehler- und Supportmodell.
4. Versionierung und Kompatibilitätsfenster.
5. Testmodus mit synthetischen Daten.
6. Nachweis, welche Aktion lokal, extern oder manuell ausgeführt wird.
7. Sicherheitsmodell für mobile Links, Widerruf, Ablauf und Speicherziel.

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
