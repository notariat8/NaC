# Plugin Plan: Handelsregister Online-Anmeldung

Status: `proposed`

## Kernentscheidung

`oac-handelsregister` wird fuer den ersten produktionsnahen Stand auf die Vorbereitung von Online-Handelsregisteranmeldungen ausgerichtet.

Der Fokus ist HRA-first, weil der Nutzer konkrete HRA-Anmeldungen vorbereiten koennen soll. Das Plugin muss aber jede Eingabe zuerst gegen die Registerspur pruefen:

- HRA: typischerweise e.K., OHG, KG und verwandte Personengesellschaften.
- HRB: typischerweise GmbH, UG und AG.

Wenn ein Nutzer "HRA" sagt, aber eine GmbH oder UG nennt, muss das Plugin die wahrscheinliche HRB-Spur sichtbar machen und eine Klarstellung verlangen.

## Betriebsgrenze

Das Plugin ist kein Registerabruf- oder Scraping-Plugin.

Es darf:

- den Online-Anmeldefall strukturieren,
- HRA/HRB-Track, Rechtsform und fehlende Angaben pruefen,
- Voraussetzungen fuer das notarielle Online-Verfahren abfragen,
- ein Anmeldepaket als Plan Preview vorbereiten,
- Evidence-Metadaten fuer Paketversion, Freigabe und spaetere Einreichung erfassen.

Es darf nicht:

- Registerdaten abrufen,
- geschuetzte Portale automatisieren,
- notariell relevante Erklaerungen abgeben,
- Unterschriften, Identifizierung oder Einreichung ersetzen,
- echte Ausweis-, PIN-, Zertifikats- oder Mandatsdaten im Repo speichern.

## Grundlage

Nach der IHK Muenchen koennen GmbHs und UGs seit 01.08.2022 online gegruendet werden; zunaechst Bargruendungen, seit 01.08.2023 auch Sach- oder gemischte Gruendungen. Ebenfalls ist die Beglaubigung von Handelsregister-Anmeldungen aller Rechtsformen mit Ausnahme von Vereinen seit 01.08.2022 online zulaessig. Fuer das Verfahren werden die App der Bundesnotarkammer, ein amtlicher Ausweis mit eID-Funktion und ein gueltiger amtlicher Lichtbildausweis benoetigt.

## Day0

- Registerspur klaeren: HRA, HRB oder anderes Register.
- Rechtsform klaeren.
- Firma, Sitz, Registergericht, Beteiligte und Vertretungsbefugnis erfassen.
- Notarroute klaeren: Online-Verfahren oder Praesenztermin.
- Bundesnotarkammer-App, eID-Funktion, PIN und Ausweisdokumente als Bereitschaft abfragen, ohne Werte zu speichern.
- Reviewer und Freigabeinhaber festlegen.

## Day1

Das Plugin erzeugt eine Plan Preview mit:

- Registerspur und Plausibilitaetswarnungen,
- fehlenden Pflichtangaben,
- Unterlagenliste fuer den Notar,
- Fragen an Antragsteller oder Rechtsberatung,
- Approval-Checkpoint vor notarieller Videokommunikation,
- Evidence-Metadatenmodell fuer Hashes und Paketversionen.

## Day2

- Abgelehnte oder zurueckgestellte Anmeldungen nachfassen.
- Fehlende Anlagen, Identifizierungsfehler, Signaturfehler und Notarhinweise dokumentieren.
- Paketversion und Evidence-Metadaten aktualisieren.
- Wiederverwendbare Vorlagen nur ohne Echtdaten im Repo halten.

## Output Shape

Das Plugin gibt immer diese Abschnitte aus:

1. `Readiness`
2. `Application Package`
3. `Approval Needed`
4. `Evidence`
5. `Day2 Follow-up`

## Quellen

- IHK Muenchen: `https://www.ihk-muenchen.de/ratgeber/recht/gesellschaftsrecht/digitalisierung/`
- Bundesnotarkammer Online-Verfahren: `https://online.notar.de/`
