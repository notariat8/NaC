# Plugin Plan: Handelsregister bundesAPI Spike

Status: `deprecated`

Dieser Plan ist für den installierbaren `nac-handelsregister`-Pluginpfad ersetzt durch
`docs/de/plugin-plans/handelsregister-online-anmeldung.md`. Er bleibt nur als historischer
Recherche-/Abruf-Spike erhalten und ist nicht die Zielrichtung für den aktuellen MVP.

## Kernentscheidung

`bundesAPI/handelsregister` wird für NaC nur als technischer Spike behandelt.
Es wird nicht direkt produktiv in NaC übernommen.

Gründe:

- Im Repository ist kein sichtbares `LICENSE`-File vorhanden.
- Das CLI wird im README als work in progress beschrieben.
- Im Code ist Rate-Limiting noch als TODO markiert.
- Das Registerportal erlaubt normale Nutzung nur als einzelne Abrufe und begrenzt Such- oder Rechtsträgeraufrufe auf 60 pro Stunde.
- Systematische Abrufe zum Aufbau oder zur Aktualisierung paralleler Register sind unzulässig.

## Ziel

NaC soll Handelsregister-Recherchen für erlaubte Einzelfälle nachvollziehbar vorbereiten, dokumentieren und evidenzfähig machen.

Der Spike darf prüfen:

- welche Suchparameter für NaC-Prozesse relevant sind,
- wie ein menschenlesbarer Rechercheplan aussieht,
- welche Evidence nach einem manuellen oder zulässigen Abruf gespeichert werden darf,
- welche technische Schnittstelle später rechtlich und betrieblich tragfähig wäre.

## Nicht-Ziele

- Kein produktiver Scraper.
- Keine Massenabfragen.
- Kein Aufbau eines parallelen Registers.
- Keine Umgehung von Sperren, Sessions, Captchas, Nutzungsordnung oder IP-Limits.
- Keine Speicherung personenbezogener Echtdaten im Repo.
- Keine direkte Übernahme von Code ohne Lizenzklärung.

## Day0

- Rechts- und Nutzungsrahmen dokumentieren.
- Lizenzlage des GitHub-Repositories klären.
- Registerportal-Nutzungsordnung als harte Betriebsgrenze übernehmen.
- Spike-Branch getrennt vom produktiven Connector führen.
- Keine echten Suchdaten in Beispieldateien speichern.

## Day1

- Nur Dry-run Plan erzeugen:
  - Suchzweck.
  - Rechtsgrund oder fachlicher Anlass.
  - Suchparameter.
  - erwartete manuelle Prüfschritte.
  - Rate-Limit-Budget.
  - Evidence-Policy.
- Optional technische Recherche gegen Test-/Beispielbegriffe ausführen, sofern Nutzungsordnung eingehalten wird.
- Ergebnis nicht als amtliche Wahrheit behandeln; fachliche Prüfung bleibt menschlich.
- Plan Preview im PR dokumentieren.

## Day2

- Abrufzählung und Rate-Limit-Log führen, falls ein technischer Abruf überhaupt aktiviert wird.
- Quellen- und Nutzungsordnungs-Änderungen regelmäßig prüfen.
- Lizenzentscheidung dokumentieren, bevor Code oder Abhängigkeiten übernommen werden.
- Bei Sperren, Fehlern oder Warnhinweisen sofort auf manuellen Einzelabruf zurückfallen.
- Audit-Evidence nur als Hash, Zeitstempel, Zweck, Akten-/Vorgangsreferenz und nicht-sensitive Ergebniszusammenfassung speichern.

## Adapter-Grenzen

Der Spike darf:

- Recherche-Intent strukturieren.
- Suchparameter für einen menschlichen Abruf vorbereiten.
- technische Machbarkeit lokal testen.
- Compliance-Grenzen sichtbar machen.

Der Spike darf nicht:

- produktiv automatisiert abrufen.
- Rate-Limits ausreizen oder parallelisieren.
- Registerdaten dauerhaft im Repo ablegen.
- API- oder Scraper-Code ohne Lizenzfreigabe übernehmen.
- die Registerportal-Nutzungsordnung umgehen.

## Quellenbewertung

| Quelle | Befund | NaC-Folge |
| --- | --- | --- |
| `bundesAPI/handelsregister` | Python-CLI, wenige Dateien, kein sichtbares LICENSE-File, kein Release | nur Spike, keine direkte Code-Übernahme |
| Registerportal Nutzungsordnung | einzelne Abrufe erlaubt, systematische Abrufe unzulässig, 60 Suchen/Aufrufe pro Stunde | hartes Rate-Limit und kein Massenbetrieb |
| HGB § 9 | Einsichtnahme zu Informationszwecken durch einzelne Abrufe | Intent und Zweck dokumentieren |
| HRV § 52 | automatisierter Abruf nur einzeln je Registerblatt und keine gezielte Personensuche | keine Bulk- oder Personensuche |
| HRV § 53 | Abrufe werden protokolliert | NaC-Audit nicht als Ersatz für amtliche Protokollierung behandeln |

## Akzeptanzkriterien für einen späteren produktiven Connector

- Lizenz und Wiederverwendung sind schriftlich geklärt.
- Offizielle oder belastbar erlaubte Schnittstelle ist dokumentiert.
- Rate-Limiting ist technisch zwingend und nicht optional.
- Dry-run ist Standard.
- Menschliche Freigabe vor jedem echten Abruf.
- Keine parallelen Registerkopien.
- Evidence speichert keine unnötigen personenbezogenen Daten.

## Quellen

- GitHub: `https://github.com/bundesAPI/handelsregister`
- Registerportal Nutzungsordnung: `https://www.handelsregister.de/rp_web/information/welcome.xhtml`
- HGB § 9: `https://www.gesetze-im-internet.de/hgb/__9.html`
- HRV § 52: `https://www.gesetze-im-internet.de/hdlregvfg/__52.html`
- HRV § 53: `https://www.gesetze-im-internet.de/hdlregvfg/__53.html`
