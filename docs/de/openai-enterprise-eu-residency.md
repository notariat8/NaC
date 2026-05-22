# OpenAI Enterprise, EU-Datenresidenz und Codex-Kosten

## Zweck

Dieses Dokument hält den Beschaffungs- und Freigabepfad für ChatGPT
Enterprise, OpenAI API mit EU-Datenresidenz und Codex-Nutzung im NaC-Kontext
fest. Es ist eine operative Governance-Notiz und ersetzt keine Rechtsberatung,
keine Datenschutzprüfung und kein verbindliches Angebot von OpenAI.

NaC-Grundsatz: Echte notarielle Vorgänge, personenbezogene Daten,
Berufsgeheimnisse, Urkundendaten und Dokumentinhalte dürfen erst nach
dokumentierter AVV/DPA-, Datenresidenz-, Rollen-, Retention- und
Tool-Freigabe verarbeitet werden.

## Quellenstand

Geprüft am 2026-05-22:

- [OpenAI ChatGPT Pricing](https://openai.com/business/chatgpt-pricing/)
- [OpenAI Help: How can I contact sales?](https://help.openai.com/en/articles/9047878-how-can-i-contact-sales)
- [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
- [OpenAI Help: Data residency and inference residency for ChatGPT](https://help.openai.com/en/articles/9903489-eu-data-residency)
- [OpenAI Help: Codex rate card](https://help.openai.com/en/articles/20001106-codex-rate-card)

Preise, Regionen, Modellabdeckung und Zusatzbedingungen sind vor Abschluss
erneut auf den offiziellen OpenAI-Seiten und im konkreten Order Form zu prüfen.

## Kurzentscheidung

| Frage | NaC-Antwort |
| --- | --- |
| Genügt ein Team- oder Business-Abo für echte NaC-/Notariatsdaten? | Nein. Business kann für Demos, Doku, Code und synthetische Daten nützlich sein, ist aber allein kein ausreichender Nachweis für EU-Datenresidenz und notarielle Verarbeitung. |
| Kann `eu.api.openai.com` im Team-/Business-Abo genutzt werden? | Nicht als bloße Abo-Annahme. Für API-Datenresidenz braucht es eine berechtigte API-Organisation, projektweise Regionenkonfiguration, Domain-Präfix und zusätzliche Freigaben wie Modified Abuse Monitoring oder Zero Data Retention. |
| Wie kommt man zu Enterprise? | Über das OpenAI-Sales-Kontaktformular mit Arbeits-E-Mail, Firma, Land/Region, Sitzanzahl, Zeitplan, Rechnungsanforderungen und Compliance-Anforderungen. |
| Was kosten Enterprise und Codex? | Enterprise ist Custom Pricing. Business ChatGPT & Codex ist öffentlich mit Listenpreis ausgewiesen. Codex wird laut Rate Card durchschnittlich mit etwa 100 bis 200 USD pro Entwickler und Monat beschrieben, variiert aber nach Modell, Instanzen, Automationen und Fast Mode. |
| Was ist der sichere Zielpfad für NaC? | Enterprise- oder API-Vertrag mit AVV/DPA, EU-Datenresidenz im Order Form bzw. Projekt, geklärter Retention, Subprocessor-/TIA-Prüfung, Tool-Grenzen und NaC-Review-Gate. |

## Beschaffungsweg

1. Anforderungen vorbereiten:
   Sitzanzahl, Zielnutzer, Notariats-/Mandatsdaten-Ausschlüsse, EU-Region,
   Inference-Residency-Wunsch, API-Verbrauch, Codex-Nutzung,
   Rechnungs-/PO-Anforderungen und AVV/DPA-Bedarf dokumentieren.
2. OpenAI Sales kontaktieren:
   Das offizielle Sales-Kontaktformular ist der öffentliche Einstieg für
   ChatGPT Enterprise und API-Enterprise-Bedarf.
3. Vertraglich klären:
   Enterprise- oder API-Vertrag, AVV/DPA, EU-Datenresidenz, Inference
   Residency, Retention, Zero Data Retention oder Modified Abuse Monitoring,
   Subprocessor, Support/SLA, Rechnungsweg und Codex-Kostenmodell.
4. Technisch konfigurieren:
   Für API-Nutzung ein getrenntes Projekt mit Region Europe (EEA +
   Switzerland) anlegen, die korrekte regionale API-Domain verwenden und
   Projekt-/Organisationsrechte beschränken.
5. In NaC freigeben:
   Die Freigabe wird als Issue, PR-Kommentar oder externer Nachweisverweis
   dokumentiert. Vertragsdokumente, Account-IDs, API-Keys und echte
   Mandatsdaten werden nicht im Produktrepo gespeichert.

## EU-Datenresidenz und API

Für API-Nutzung ist EU-Verarbeitung kein reines Client-Thema. Der NaC-Pfad
verlangt mindestens:

- berechtigte OpenAI API-Organisation mit Datenresidenz-Funktion
- projektweise Regionenkonfiguration auf Europe (EEA + Switzerland)
- Nutzung von `https://eu.api.openai.com` für passende API-Requests
- Freigabe für Modified Abuse Monitoring oder Zero Data Retention, soweit für
  Nicht-US-Regionen erforderlich
- Prüfung der unterstützten Endpunkte, Modelle, Tools und Einschränkungen
- Verbot echter Mandatsdaten in Remote-MCP-, Web-Search- oder
  Drittanbieter-Tools ohne gesonderte Freigabe

Systemdaten, Metadaten, Abrechnung, Supportdaten und Drittanbieterpfade können
außerhalb der gewählten Region liegen. Diese Grenze muss im
Datenschutzreview ausdrücklich berücksichtigt werden.

## ChatGPT Enterprise

ChatGPT Enterprise ist der Zielkanal, wenn echte angemeldete Benutzer,
Workspace-Steuerung, SSO/SCIM, rollenbasierte Verwaltung, Custom Legal Terms,
Support/SLA, Datenresidenz oder strengere Datenschutzbedingungen benötigt
werden. Für NaC ist Enterprise kein Freifahrtschein: Die konkrete
Workspace-Konfiguration, Apps, MCP-Connectoren, Web Search, Retention,
Freigaben und Protokollierung bleiben freigabepflichtig.

Für ChatGPT-Datenresidenz gilt zusätzlich:

- Workspace muss mit Datenresidenz in der gewünschten Region provisioniert
  werden.
- Inference Residency ist nur für berechtigte Enterprise-/Edu-Kunden und
  unterstützte Regionen verfügbar.
- Nicht alle Daten fallen in den Residency-Scope; insbesondere Account-,
  Billing-, Login-, Nutzungs- und andere Systemdaten bleiben getrennt zu
  bewerten.
- Externe Integrationen wie Apps, MCP und Web Search haben eigene
  Datenpfade und dürfen nicht pauschal als EU-resident betrachtet werden.

## Codex Workspace und Kosten

Ein Codex Workspace ist im NaC-Verständnis kein Ersatz für das lokale
Notariatsarbeitsplatz-Profil. Er ist eine Entwicklungs- und
Automationsumgebung mit Admin-, Sicherheits-, Worktree- und Agentenfunktionen,
die Code, Doku, Tests und synthetische Demos bearbeiten kann.

Für echte notarielle Verarbeitung gilt:

- Codex darf im Produktrepo keine realen Urkundendaten, Secrets, API-Keys,
  Kartenwerte, PINs, privaten Schlüssel oder Mandatsdokumente speichern.
- Lokale Kartenleser-, XNP-, eID- und morris-Pfade bleiben über das lokale
  Profil `notary-workstation` zu prüfen.
- Für gehostete Codex- oder API-Funktionen gelten dieselben AVV/DPA-,
  Datenresidenz-, Retention- und Tool-Gates wie für andere externe
  KI-Verarbeitung.
- Das Codex-Kostenmodell muss im Vertrag bzw. in der Rate Card gegen den
  geplanten Nutzungsfall geprüft werden; Durchschnittswerte ersetzen keine
  Budgetfreigabe.

## Mindestfreigabe für NaC-Piloten

Vor Verarbeitung echter personenbezogener oder notarieller Daten müssen
mindestens vorliegen:

- wirksam akzeptierte AVV/DPA oder gleichwertige Vertragsgrundlage
- Order Form oder Admin-Nachweis für EU-Datenresidenz, soweit genutzt
- dokumentierte Entscheidung zu Inference Residency oder Rest-Risiko
- OpenAI-Produkt-/Lizenzzuordnung: Business, Enterprise, API oder Codex
- Projekt-/Workspace-Konfiguration mit Retention, Training/Data-Sharing,
  Rollen, SSO/MFA und Zugriffspfaden
- Entscheidung zu Modified Abuse Monitoring oder Zero Data Retention
- Subprocessor-, Transfer-, TIA- und SCC-Prüfung, soweit erforderlich
- Tool-Grenze für Apps, MCP, Web Search, Datei-Uploads und Connectoren
- NaC-Review durch Datenschutz, fachlichen Owner und technischen Owner
- Verweis auf [docs/de/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md)

## Entscheidungsmatrix

| Kanal | Geeignet für | Nicht geeignet für | NaC-Status |
| --- | --- | --- | --- |
| ChatGPT Business bzw. frühere Team-Ebene | Doku, Code, synthetische Demos, nicht-sensitive Planung | Echte Mandatsdaten ohne zusätzliche AVV/DPA-, Residency- und Tool-Freigabe | Nur eingeschränkt |
| ChatGPT Enterprise | angemeldete Benutzer, SSO, Admin-Kontrollen, vertragliche Enterprise-Grenzen | pauschale Verarbeitung ohne konkrete Workspace- und Tool-Prüfung | Zielpfad für ChatGPT-Oberfläche |
| OpenAI API Europe | serverseitige NaC-Funktionen mit regionalem Projekt und `eu.api.openai.com` | Nutzung ohne berechtigte API-Organisation, ZDR/MAM-Entscheidung und Endpunktprüfung | Zielpfad für API-Integration |
| Codex | Entwicklung, Reviews, Tests, synthetische Vorgänge, Repo-Automation | Speicherung echter Mandatsdaten oder Secrets im Repo/Workspace | Entwicklungs- und Operationspfad |
| Lokale NaC-Workstation | XNP, eID, Kartenleser, morris, lokale Gates | externe KI-Verarbeitung ohne Freigabe | Standardpfad für sensible Gates |
