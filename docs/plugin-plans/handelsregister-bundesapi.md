# Plugin Plan: Handelsregister bundesAPI Spike

Status: `deprecated`

Dieser Plan ist fuer den installierbaren `oac-handelsregister`-Pluginpfad ersetzt durch
`docs/plugin-plans/handelsregister-online-anmeldung.md`. Er bleibt nur als historischer
Recherche-/Abruf-Spike erhalten und ist nicht die Zielrichtung fuer den aktuellen MVP.

## Kernentscheidung

`bundesAPI/handelsregister` wird fuer OaC nur als technischer Spike behandelt.
Es wird nicht direkt produktiv in OaC uebernommen.

Gruende:

- Im Repository ist kein sichtbares `LICENSE`-File vorhanden.
- Das CLI wird im README als work in progress beschrieben.
- Im Code ist Rate-Limiting noch als TODO markiert.
- Das Registerportal erlaubt normale Nutzung nur als einzelne Abrufe und begrenzt Such- oder Rechtstraegeraufrufe auf 60 pro Stunde.
- Systematische Abrufe zum Aufbau oder zur Aktualisierung paralleler Register sind unzulaessig.

## Ziel

OaC soll Handelsregister-Recherchen fuer erlaubte Einzelfaelle nachvollziehbar vorbereiten, dokumentieren und evidenzfaehig machen.

Der Spike darf pruefen:

- welche Suchparameter fuer OaC-Prozesse relevant sind,
- wie ein menschenlesbarer Rechercheplan aussieht,
- welche Evidence nach einem manuellen oder zulässigen Abruf gespeichert werden darf,
- welche technische Schnittstelle spaeter rechtlich und betrieblich tragfaehig waere.

## Nicht-Ziele

- Kein produktiver Scraper.
- Keine Massenabfragen.
- Kein Aufbau eines parallelen Registers.
- Keine Umgehung von Sperren, Sessions, Captchas, Nutzungsordnung oder IP-Limits.
- Keine Speicherung personenbezogener Echtdaten im Repo.
- Keine direkte Uebernahme von Code ohne Lizenzklaerung.

## Day0

- Rechts- und Nutzungsrahmen dokumentieren.
- Lizenzlage des GitHub-Repositories klaeren.
- Registerportal-Nutzungsordnung als harte Betriebsgrenze uebernehmen.
- Spike-Branch getrennt vom produktiven Connector fuehren.
- Keine echten Suchdaten in Beispieldateien speichern.

## Day1

- Nur Dry-run Plan erzeugen:
  - Suchzweck.
  - Rechtsgrund oder fachlicher Anlass.
  - Suchparameter.
  - erwartete manuelle Pruefschritte.
  - Rate-Limit-Budget.
  - Evidence-Policy.
- Optional technische Recherche gegen Test-/Beispielbegriffe ausfuehren, sofern Nutzungsordnung eingehalten wird.
- Ergebnis nicht als amtliche Wahrheit behandeln; fachliche Pruefung bleibt menschlich.
- Plan Preview im PR dokumentieren.

## Day2

- Abrufzaehlung und Rate-Limit-Log fuehren, falls ein technischer Abruf ueberhaupt aktiviert wird.
- Quellen- und Nutzungsordnungs-Aenderungen regelmaessig pruefen.
- Lizenzentscheidung dokumentieren, bevor Code oder Abhaengigkeiten uebernommen werden.
- Bei Sperren, Fehlern oder Warnhinweisen sofort auf manuellen Einzelabruf zurueckfallen.
- Audit-Evidence nur als Hash, Zeitstempel, Zweck, Akten-/Vorgangsreferenz und nicht-sensitive Ergebniszusammenfassung speichern.

## Adapter-Grenzen

Der Spike darf:

- Recherche-Intent strukturieren.
- Suchparameter fuer einen menschlichen Abruf vorbereiten.
- technische Machbarkeit lokal testen.
- Compliance-Grenzen sichtbar machen.

Der Spike darf nicht:

- produktiv automatisiert abrufen.
- Rate-Limits ausreizen oder parallelisieren.
- Registerdaten dauerhaft im Repo ablegen.
- API- oder Scraper-Code ohne Lizenzfreigabe uebernehmen.
- die Registerportal-Nutzungsordnung umgehen.

## Quellenbewertung

| Quelle | Befund | OaC-Folge |
| --- | --- | --- |
| `bundesAPI/handelsregister` | Python-CLI, wenige Dateien, kein sichtbares LICENSE-File, kein Release | nur Spike, keine direkte Code-Uebernahme |
| Registerportal Nutzungsordnung | einzelne Abrufe erlaubt, systematische Abrufe unzulaessig, 60 Suchen/Aufrufe pro Stunde | hartes Rate-Limit und kein Massenbetrieb |
| HGB § 9 | Einsichtnahme zu Informationszwecken durch einzelne Abrufe | Intent und Zweck dokumentieren |
| HRV § 52 | automatisierter Abruf nur einzeln je Registerblatt und keine gezielte Personensuche | keine Bulk- oder Personensuche |
| HRV § 53 | Abrufe werden protokolliert | OaC-Audit nicht als Ersatz fuer amtliche Protokollierung behandeln |

## Akzeptanzkriterien fuer einen spaeteren produktiven Connector

- Lizenz und Wiederverwendung sind schriftlich geklaert.
- Offizielle oder belastbar erlaubte Schnittstelle ist dokumentiert.
- Rate-Limiting ist technisch zwingend und nicht optional.
- Dry-run ist Standard.
- Menschliche Freigabe vor jedem echten Abruf.
- Keine parallelen Registerkopien.
- Evidence speichert keine unnoetigen personenbezogenen Daten.

## Quellen

- GitHub: `https://github.com/bundesAPI/handelsregister`
- Registerportal Nutzungsordnung: `https://www.handelsregister.de/rp_web/information/welcome.xhtml`
- HGB § 9: `https://www.gesetze-im-internet.de/hgb/__9.html`
- HRV § 52: `https://www.gesetze-im-internet.de/hdlregvfg/__52.html`
- HRV § 53: `https://www.gesetze-im-internet.de/hdlregvfg/__53.html`
