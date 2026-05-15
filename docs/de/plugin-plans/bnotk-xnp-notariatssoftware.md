# Plugin Plan: BNotK XNP Notariatssoftware Companion

Status: `proposed`

## Kernentscheidung

XNP darf nicht aus der Cloud gesteuert werden.
Ein NoC-Plugin fuer XNP wird als lokaler Companion geplant, der im selben Arbeitsplatz- und Benutzerkontext laeuft wie XNP.

NoC SaaS oder Remote-Ausfuehrung bekommen nur:

- Workflow-Status,
- Policy-Entscheidungen,
- Hashes,
- nicht-sensitive Evidence,
- Freigabe- und Audit-Metadaten.

Direkte API-Calls bleiben deaktiviert, bis die offizielle BNotK-Schnittstellendefinition lokal vorliegt und fachlich freigegeben ist.

Der erste lauffaehige MVP liegt unter `plugins/noc-bnotk-xnp/scripts/reader_prompt.py`. Er erzeugt einen lokalen Dry-run Reader-Prompt fuer den cyberJack-Reader-Pfad, ruft das `noc-cyberjack-rfid` Card-Gate auf, prueft nur die XNP-Localhost-Erreichbarkeit im Portbereich `12774` bis `12784` und schreibt Evidence nach `plugins/noc-bnotk-xnp/contracts/reader-prompt-evidence.schema.json`. Mit `--probe-morris-api` kann der Reader-Prompt den optionalen morris-Loopback-/PCSC-Probe aus dem Card-Gate durchreichen. Er fuehrt keinen XNP-Login aus, nutzt keinen XNP-API-Key und schreibt keine produktiven XNP-Daten.

## Reihenfolge fuer Handelsregister-Online-Anmeldungen

Dieser Plan ist der zweite technische Baustein, wenn NoC einen echten notariatsseitigen
Handelsregister- oder HRA-Workflow vorbereiten soll.

Korrektur nach Karten-/Login-Abhaengigkeit: XNP selbst ist erst testbar, wenn der
lokale Kartenpfad steht. Daher ist `noc-cyberjack-rfid` als Card/SAK-Gate dem
XNP-Gate vorgelagert.

`noc-handelsregister` darf in diesem Zielbild erst nachgelagert fachliche Anmeldedaten,
Registerspur und Paket-Readiness strukturieren. Der Startpunkt ist vorher:

1. BNotK Chip-/Signaturkarte klaeren.
2. Kartenleser Sicherheitsklasse 3, PC/SC, BNotK SAK lite oder XNP-Kartenpfad und secureFramework pruefen.
3. Ueber `noc-bnotk-xnp` einen lokalen Reader-Prompt fuer den cyberJack-Reader-Pfad als Dry-run Evidence erzeugen.
4. Notar-/Notariatsrolle klaeren.
5. Lokalen XNP-Arbeitsplatz und aktuelle Anmeldung bestaetigen.
6. Amtstaetigkeitskontext lokal bestaetigen.
7. XNotar-Handelsregistermodul bzw. Austauschordner-Pfad klaeren.
8. Nur danach HRA-/HRB-spezifische Paketlogik aktivieren.

Wenn NoC nur einen Buerger-/Mandanten-Preflight fuer `online.notar.de` anbietet, kann
`noc-handelsregister` ohne XNP starten. Sobald aber ein Notariatsarbeitsplatz,
XNotar, Registervollzug oder Einreichungsnahe betroffen ist, blockiert dieser
XNP-/Notariats-Readiness-Schritt die weitere Entwicklung.

## Ziel

Der Companion soll NoC-Prozesse fuer notarielle Arbeitsablaeufe vorbereiten und lokal kontrolliert an XNP-nahe Funktionen anbinden.

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
- Keine produktiven API-Calls ohne ausdrueckliche lokale Freigabe.

## Day0

- Zielrolle klaeren: Buerger-/Mandanten-Preflight oder Notariatsarbeitsplatz.
- Bei Notariatsarbeitsplatz zuerst Card/SAK-Gate abschliessen: Karte, Kartenleser, PC/SC, SAK lite oder XNP-Kartenpfad und secureFramework.
- XNP-Installationskontext lokal pruefen.
- Lokale XNP-Anmeldung, Nutzerrolle und Amtstaetigkeitskontext als Voraussetzung behandeln.
- Klaeren, ob die Notariatssoftware-Schnittstelle aktiv ist.
- Fuer Handelsregister-/HRA-Faelle XNotar-Modul und Datenaustauschverzeichnis klaeren.
- Lokale Port-Konfiguration dokumentieren, ohne Secrets zu speichern.
- Offizielle Schnittstellendefinition beschaffen.
- Datenschutz-, Rollen- und AVV-Relevanz pruefen.
- NoC-Companion als lokale Komponente planen, nicht als Cloud-Service.

## Day1

- Lokalen Dry-run Companion bauen:
  - lokalen Reader-Prompt fuer den cyberJack-Reader-Pfad erzeugen.
  - `noc-cyberjack-rfid` Evidence referenzieren.
  - XNP-Verfuegbarkeit pruefen.
  - lokale Anmeldung und Amtstaetigkeitskontext nur attestieren, nicht uebertragen.
  - lokalen Port aus Konfiguration lesen oder per erlaubtem Discovery-Verfahren finden.
  - keine Login- oder API-Key-Daten speichern.
  - NoC-Intent in menschenlesbaren XNP-Plan uebersetzen.
  - fuer Registerfaelle XNotar-Austauschordner und XJustiz-Paketstruktur validieren.
  - Nutzer bestaetigt lokal vor jedem echten Schritt.
- API-Calls bleiben standardmaessig deaktiviert.
- Erst nach Freigabe:
  - einzelne UVZ/VVZ-Funktion im Testkontext.
  - Evidence nur als Hash und Status.
  - keine Urkundeninhalte im Repo.

## Day2

- BNotK-Versionshinweise und XNP-Updates pruefen.
- Schnittstellenverhalten nach Wartungsupdates neu validieren.
- API-Key- und Port-Konfiguration lokal rezertifizieren.
- Companion-Logs lokal rotieren und minimieren.
- Drift zwischen NoC-Vorgang, XNP-Status und Evidence als Issue erfassen.
- Exit-Pfad dokumentieren: XNP bleibt auch ohne NoC manuell bedienbar.

## Sicherheitsmodell

- Laufzeit nur auf dem lokalen Arbeitsplatz.
- Kommunikation nur gegen `localhost`.
- Reader-Prompt bleibt ein Dry-run und aktiviert keine produktive XNP-Aktion.
- Keine Remote-Portweiterleitung.
- Keine Secrets in Git.
- Keine zentrale Speicherung von API-Keys.
- Nutzer- und Amtstaetigkeitskontext wird lokal durch XNP validiert.
- NoC speichert nur nicht-sensitive Evidence.

## Quellenbewertung

| Quelle | Befund | NoC-Folge |
| --- | --- | --- |
| BNotK Onlinehilfe XNP-Integration | XNP bietet einen lokalen REST-Endpunkt auf `localhost` an | Companion muss lokal laufen |
| BNotK Onlinehilfe XNP-Integration | Standard-Portsuche beginnt bei 12774 und endet bei 12784 | Port nicht hart codieren |
| BNotK Onlinehilfe XNP-Integration | Login-Token und aktuelle Amtstaetigkeit werden fuer NSW-Aufrufe benoetigt | keine Cloud-Ausfuehrung |
| BNotK Onlinehilfe XNP-Integration | API-Key fuer Login-Funktion ist lokal konfiguriert und verschluesselt nicht installationsuebertragbar | keine Secret-Synchronisierung |

## Akzeptanzkriterien fuer Pilot

- Companion startet nur lokal.
- Dry-run ist Standard.
- Reader-Prompt erzeugt Evidence ohne PIN-, Karten-, API-Key- oder Login-Werte.
- XNP-Schnittstellendefinition ist dokumentiert.
- Jeder echte Aufruf erfordert lokale Nutzerbestaetigung.
- Keine Urkunden-, UVZ-, VVZ- oder API-Key-Inhalte im Repo.
- Evidence enthaelt Hash, Zeitstempel, Vorgangs-ID und lokalen Status.
- Manuelle XNP-Bedienung bleibt vollstaendig moeglich.

## Quellen

- BNotK Onlinehilfe: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk/integration-xnp-mit-notariatssoftware.html`
- BNotK Onlinehilfe XNP: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html`
- BNotK Onlinehilfe XNotar: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnotar.html`
