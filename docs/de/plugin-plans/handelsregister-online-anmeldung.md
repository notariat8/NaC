# Plugin Plan: Handelsregister Online-Anmeldung

Status: `proposed`

## Kernentscheidung

`nac-handelsregister` wird auf die Vorbereitung von Online-Handelsregisteranmeldungen ausgerichtet.

Korrektur der Entwicklungsreihenfolge: Für einen echten notariatsseitigen
Anmelde- oder Vollzugspfad ist zuerst die `Karte/SAK`
(`nac-cyberjack-rfid`)
erforderlich, weil XNP-Login-Tests ohne Karte/Kartenleser/SAK-lite bzw.
XNP-Kartenpfad und secureFramework nicht belastbar sind. Danach kommt
`nac-bnotk-xnp`; `nac-handelsregister` ist dann der fachliche Layer für
Registerspur, HRA-/HRB-Plausibilität und Paketbereitschaft.

Nur eine reine Bürger-/Mandanten-Vorprüfung für `online.notar.de` kann ohne
Notar-/XNP-Authentifizierung starten. Diese Vorprüfung darf keine Einreichung,
keine Notariatssoftware-Steuerung und keine notarielle Erklärung ausloesen.

Der Fokus ist HRA-first, weil der Nutzer konkrete HRA-Anmeldungen vorbereiten können soll. Das Plugin muss aber jede Eingabe zuerst gegen die Registerspur prüfen:

- HRA: typischerweise e.K., OHG, KG und verwandte Personengesellschaften.
- HRB: typischerweise GmbH, UG und AG.

Wenn ein Nutzer "HRA" sagt, aber eine GmbH oder UG nennt, muss das Plugin die wahrscheinliche HRB-Spur sichtbar machen und eine Klarstellung verlangen.

## Betriebsgrenze

Das Plugin ist kein Registerabruf- oder Scraping-Plugin.

Es darf:

- den Online-Anmeldefall strukturieren,
- HRA/HRB-Track, Rechtsform und fehlende Angaben prüfen,
- Voraussetzungen für das notarielle Online-Verfahren abfragen,
- bei notariatsseitigem Ziel auf `nac-cyberjack-rfid` und danach `nac-bnotk-xnp` als vorgelagerte Karten-/XNP-Prüfungen verweisen,
- ein Anmeldepaket als Planvorschau vorbereiten,
- Nachweis-Metadaten für Paketversion, Freigabe und spätere Einreichung erfassen.

Es darf nicht:

- Registerdaten abrufen,
- geschützte Portale automatisieren,
- notariell relevante Erklärungen abgeben,
- Unterschriften, Identifizierung oder Einreichung ersetzen,
- echte Ausweis-, PIN-, Zertifikats- oder Mandatsdaten im Repo speichern.

## Grundlage

Nach der IHK Muenchen können GmbHs und UGs seit 01.08.2022 online gegründet werden; zunächst Bargründungen, seit 01.08.2023 auch Sach- oder gemischte Gründungen. Ebenfalls ist die Beglaubigung von Handelsregister-Anmeldungen aller Rechtsformen mit Ausnahme von Vereinen seit 01.08.2022 online zulässig. Für das Verfahren werden die App der Bundesnotarkammer, ein amtlicher Ausweis mit eID-Funktion und ein gültiger amtlicher Lichtbildausweis benötigt.

## Day0

- Betriebsmodus klären: Bürger-/Mandanten-Vorprüfung oder Notariatsarbeitsplatz.
- Bei Notariatsarbeitsplatz zuerst `nac-cyberjack-rfid` abschließen: Karte, Kartenleser, PC/SC, SAK lite oder XNP-Kartenpfad und secureFramework.
- Danach `nac-bnotk-xnp` abschließen: lokale XNP-Anmeldung, Amtstätigkeitskontext, XNotar-Modul und Austauschordner.
- Registerspur klären: HRA, HRB oder anderes Register.
- Rechtsform klären.
- Firma, Sitz, Registergericht, Beteiligte und Vertretungsbefugnis erfassen.
- Notarroute klären: Online-Verfahren oder Praesenztermin.
- Bundesnotarkammer-App, eID-Funktion, PIN und Ausweisdokumente als Bereitschaft abfragen, ohne Werte zu speichern.
- Reviewer und Freigabeinhaber festlegen.

## Day1

Das Plugin erzeugt eine Planvorschau mit:

- Betriebsmodus, Karten-/SAK-Prüfstatus und Auth-/XNP-Prüfstatus,
- Registerspur und Plausibilitätswarnungen,
- fehlenden Pflichtangaben,
- Unterlagenliste für den Notar,
- Fragen an Antragsteller oder Rechtsberatung,
- Freigabepunkt vor notarieller Videokommunikation,
- Nachweis-Metadatenmodell für Hashes und Paketversionen.

## Day2

- Abgelehnte oder zurückgestellte Anmeldungen nachfassen.
- Fehlende Anlagen, Identifizierungsfehler, Signaturfehler und Notarhinweise dokumentieren.
- Paketversion und Nachweis-Metadaten aktualisieren.
- Wiederverwendbare Vorlagen nur ohne Echtdaten im Repo halten.

## Ausgabeform

Das Plugin gibt immer diese Abschnitte aus:

1. `Bereitschaft`
2. `Anmeldepaket`
3. `Freigabe Erforderlich`
4. `Nachweis`
5. `Day2-Nachfassen`

## Quellen

- IHK Muenchen: `https://www.ihk-muenchen.de/ratgeber/recht/gesellschaftsrecht/digitalisierung/`
- Bundesnotarkammer Online-Verfahren: `https://online.notar.de/`
