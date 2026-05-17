# Plugin Plan: BNotK XNP Notariatssoftware-Begleiter

Status: `proposed`

## Kernentscheidung

XNP darf nicht aus der Cloud gesteuert werden.
Ein NoC-Plugin fuer XNP wird als lokaler Begleiter geplant, der im selben Arbeitsplatz- und Benutzerkontext laeuft wie XNP.

NoC SaaS oder Remote-Ausfuehrung bekommen nur:

- Arbeitsablauf-Status,
- Policy-Entscheidungen,
- Hashes,
- nicht-sensitive Nachweise,
- Freigabe- und Audit-Metadaten.

Direkte API-Aufrufe bleiben deaktiviert, bis die offizielle BNotK-Schnittstellendefinition lokal vorliegt und fachlich freigegeben ist.

Der erste lauffaehige MVP liegt unter `plugins/noc-bnotk-xnp/scripts/reader_prompt.py`. Er erzeugt einen lokalen Trockenlauf-Leser-Prompt fuer den cyberJack-Reader-Pfad, ruft die `NoC Karten- und SAK-Pruefung` auf, prueft nur die XNP-Localhost-Erreichbarkeit im Portbereich `12774` bis `12784` und schreibt Nachweise nach `plugins/noc-bnotk-xnp/contracts/reader-prompt-evidence.schema.json`. Mit `--probe-morris-api` kann der Leser-Prompt die optionale morris-Loopback-/PCSC-Pruefung aus der Kartenpruefung durchreichen. Er fuehrt keinen XNP-Login aus, nutzt keinen XNP-API-Key und schreibt keine produktiven XNP-Daten.

## Reihenfolge fuer Handelsregister-Online-Anmeldungen

Dieser Plan ist der zweite technische Baustein, wenn NoC einen echten notariatsseitigen
Handelsregister- oder HRA-Arbeitsablauf vorbereiten soll.

Korrektur nach Karten-/Login-Abhaengigkeit: XNP selbst ist erst testbar, wenn der
lokale Kartenpfad steht. Daher ist `noc-cyberjack-rfid` als `NoC Karten- und SAK-Pruefung` dem
der `NoC XNP-Notariatspruefung` vorgelagert.

`noc-handelsregister` darf in diesem Zielbild erst nachgelagert fachliche Anmeldedaten,
Registerspur und Paketbereitschaft strukturieren. Der Startpunkt ist vorher:

1. BNotK Chip-/Signaturkarte klaeren.
2. Kartenleser Sicherheitsklasse 3, PC/SC, BNotK SAK lite oder XNP-Kartenpfad und secureFramework pruefen.
3. Ueber `noc-bnotk-xnp` einen lokalen Leser-Prompt fuer den cyberJack-Reader-Pfad als Trockenlauf-Nachweis erzeugen.
4. Notar-/Notariatsrolle klaeren.
5. Lokalen XNP-Arbeitsplatz und aktuelle Anmeldung bestaetigen.
6. Amtstaetigkeitskontext lokal bestaetigen.
7. XNotar-Handelsregistermodul bzw. Austauschordner-Pfad klaeren.
8. Nur danach HRA-/HRB-spezifische Paketlogik aktivieren.

Wenn NoC nur eine Buerger-/Mandanten-Vorpruefung fuer `online.notar.de` anbietet, kann
`noc-handelsregister` ohne XNP starten. Sobald aber ein Notariatsarbeitsplatz,
XNotar, Registervollzug oder Einreichungsnahe betroffen ist, blockiert dieser
XNP-/Notariats-Bereitschaftsschritt die weitere Entwicklung.

## Ziel

Der Begleiter soll NoC-Prozesse fuer notarielle Arbeitsablaeufe vorbereiten und lokal kontrolliert an XNP-nahe Funktionen anbinden.

Moegliche Zielbereiche laut BNotK-Onlinehilfe:

- Login-Anstoss mit Karte oder Nutzername in XNP.
- UVZ-Suche und UVZ-Eintragsabfrage.
- Ermittlung der naechsten freien UVZ-Nummer.
- Erstellen von UVZ-Eintraegen.
- Hinzufuegen von Dokumenten zu bestehenden UVZ-Eintraegen.
- VVZ-Suche, VVZ-Abfrage und Erstellen von Verwahrungsmassen.

## Nicht-Ziele

- Keine Cloud-Steuerung von XNP.
- Keine Uebertragung von XNP-API-Keys in NoC SaaS oder Git.
- Kein Zugriff ohne lokale XNP-Anmeldung und passende Amtstaetigkeit.
- Keine Umgehung der BNotK-Schnittstellendefinition.
- Keine produktiven API-Aufrufe ohne ausdrueckliche lokale Freigabe.

## Day0

- Zielrolle klaeren: Buerger-/Mandanten-Vorpruefung oder Notariatsarbeitsplatz.
- Bei Notariatsarbeitsplatz zuerst `NoC Karten- und SAK-Pruefung` abschliessen: Karte, Kartenleser, PC/SC, SAK lite oder XNP-Kartenpfad und secureFramework.
- XNP-Installationskontext lokal pruefen.
- Lokale XNP-Anmeldung, Nutzerrolle und Amtstaetigkeitskontext als Voraussetzung behandeln.
- Klaeren, ob die Notariatssoftware-Schnittstelle aktiv ist.
- Fuer Handelsregister-/HRA-Faelle XNotar-Modul und Datenaustauschverzeichnis klaeren.
- Lokale Port-Konfiguration dokumentieren, ohne Geheimnisse zu speichern.
- Offizielle Schnittstellendefinition beschaffen.
- Datenschutz-, Rollen- und AVV-Relevanz pruefen.
- NoC-Begleiter als lokale Komponente planen, nicht als Cloud-Service.

## Day1

- Lokalen Trockenlauf-Begleiter bauen:
  - lokalen Reader-Prompt fuer den cyberJack-Reader-Pfad erzeugen.
  - `noc-cyberjack-rfid`-Nachweis referenzieren.
  - XNP-Verfuegbarkeit pruefen.
  - lokale Anmeldung und Amtstaetigkeitskontext nur attestieren, nicht uebertragen.
  - lokalen Port aus Konfiguration lesen oder per erlaubtem Discovery-Verfahren finden.
  - keine Login- oder API-Key-Daten speichern.
  - NoC-Intent in menschenlesbaren XNP-Plan uebersetzen.
  - fuer Registerfaelle XNotar-Austauschordner und XJustiz-Paketstruktur validieren.
  - Nutzer bestaetigt lokal vor jedem echten Schritt.
- API-Aufrufe bleiben standardmaessig deaktiviert.
- Erst nach Freigabe:
  - einzelne UVZ/VVZ-Funktion im Testkontext.
  - Nachweis nur als Hash und Status.
  - keine Urkundeninhalte im Repo.

## Day2

- BNotK-Versionshinweise und XNP-Updates pruefen.
- Schnittstellenverhalten nach Wartungsupdates neu validieren.
- API-Key- und Port-Konfiguration lokal rezertifizieren.
- Begleiter-Protokolle lokal rotieren und minimieren.
- Drift zwischen NoC-Vorgang, XNP-Status und Nachweis als Issue erfassen.
- Exit-Pfad dokumentieren: XNP bleibt auch ohne NoC manuell bedienbar.

## Sicherheitsmodell

- Laufzeit nur auf dem lokalen Arbeitsplatz.
- Kommunikation nur gegen `localhost`.
- Leser-Prompt bleibt ein Trockenlauf und aktiviert keine produktive XNP-Aktion.
- Keine Remote-Portweiterleitung.
- Keine Geheimnisse in Git.
- Keine zentrale Speicherung von API-Keys.
- Nutzer- und Amtstaetigkeitskontext wird lokal durch XNP validiert.
- NoC speichert nur nicht-sensitive Nachweise.

## Quellenbewertung

| Quelle | Befund | NoC-Folge |
| --- | --- | --- |
| BNotK Onlinehilfe XNP-Integration | XNP bietet einen lokalen REST-Endpunkt auf `localhost` an | Begleiter muss lokal laufen |
| BNotK Onlinehilfe XNP-Integration | Standard-Portsuche beginnt bei 12774 und endet bei 12784 | Port nicht hart codieren |
| BNotK Onlinehilfe XNP-Integration | Login-Token und aktuelle Amtstaetigkeit werden fuer NSW-Aufrufe benoetigt | keine Cloud-Ausfuehrung |
| BNotK Onlinehilfe XNP-Integration | API-Key fuer Login-Funktion ist lokal konfiguriert und verschluesselt nicht installationsuebertragbar | keine Geheimnis-Synchronisierung |

## Akzeptanzkriterien fuer Pilot

- Begleiter startet nur lokal.
- Trockenlauf ist Standard.
- Leser-Prompt erzeugt Nachweise ohne PIN-, Karten-, API-Key- oder Login-Werte.
- XNP-Schnittstellendefinition ist dokumentiert.
- Jeder echte Aufruf erfordert lokale Nutzerbestaetigung.
- Keine Urkunden-, UVZ-, VVZ- oder API-Key-Inhalte im Repo.
- Nachweis enthaelt Hash, Zeitstempel, Vorgangs-ID und lokalen Status.
- Manuelle XNP-Bedienung bleibt vollstaendig moeglich.

## Quellen

- BNotK Onlinehilfe: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk/integration-xnp-mit-notariatssoftware.html`
- BNotK Onlinehilfe XNP: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html`
- BNotK Onlinehilfe XNotar: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnotar.html`
