# Plugin Plan: BNotK XNP Notariatssoftware-Begleiter

Status: `proposed`

## Kernentscheidung

XNP darf nicht aus der Cloud gesteuert werden.
Ein NaC-Plugin für XNP wird als lokaler Begleiter geplant, der im selben Arbeitsplatz- und Benutzerkontext läuft wie XNP.

NaC SaaS oder Remote-Ausführung bekommen nur:

- Arbeitsablauf-Status,
- Policy-Entscheidungen,
- Hashes,
- nicht-sensitive Nachweise,
- Freigabe- und Audit-Metadaten.

Direkte API-Aufrufe bleiben deaktiviert, bis die offizielle BNotK-Schnittstellendefinition lokal vorliegt und fachlich freigegeben ist.

Der erste lauffähige MVP liegt unter `plugins/nac-bnotk-xnp/scripts/reader_prompt.py`. Er erzeugt einen lokalen Trockenlauf-Leser-Prompt für den cyberJack-Reader-Pfad, ruft die `Karte/SAK` auf, prüft nur die XNP-Localhost-Erreichbarkeit im Portbereich `12774` bis `12784` und schreibt Nachweise nach `plugins/nac-bnotk-xnp/contracts/reader-prompt-evidence.schema.json`. Mit `--probe-morris-api` kann der Leser-Prompt die optionale morris-Loopback-/PCSC-Prüfung aus der Kartenprüfung durchreichen. Er führt keinen XNP-Login aus, nutzt keinen XNP-API-Key und schreibt keine produktiven XNP-Daten.

## Reihenfolge für Handelsregister-Online-Anmeldungen

Dieser Plan ist der zweite technische Baustein, wenn NaC einen echten notariatsseitigen
Handelsregister- oder HRA-Arbeitsablauf vorbereiten soll.

Korrektur nach Karten-/Login-Abhängigkeit: XNP selbst ist erst testbar, wenn der
lokale Kartenpfad steht. Daher ist `nac-cyberjack-rfid` als `Karte/SAK`
der `XNP-Prüfung` vorgelagert.

`nac-handelsregister` darf in diesem Zielbild erst nachgelagert fachliche Anmeldedaten,
Registerspur und Paketbereitschaft strukturieren. Der Startpunkt ist vorher:

1. BNotK Chip-/Signaturkarte klären.
2. Kartenleser Sicherheitsklasse 3, PC/SC, BNotK SAK lite oder XNP-Kartenpfad und secureFramework prüfen.
3. Über `nac-bnotk-xnp` einen lokalen Leser-Prompt für den cyberJack-Reader-Pfad als Trockenlauf-Nachweis erzeugen.
4. Notar-/Notariatsrolle klären.
5. Lokalen XNP-Arbeitsplatz und aktuelle Anmeldung bestätigen.
6. Amtstätigkeitskontext lokal bestätigen.
7. XNotar-Handelsregistermodul bzw. Austauschordner-Pfad klären.
8. Nur danach HRA-/HRB-spezifische Paketlogik aktivieren.

Wenn NaC nur eine Bürger-/Mandanten-Vorprüfung für `online.notar.de` anbietet, kann
`nac-handelsregister` ohne XNP starten. Sobald aber ein Notariatsarbeitsplatz,
XNotar, Registervollzug oder Einreichungsnahe betroffen ist, blockiert dieser
XNP-/Notariats-Bereitschaftsschritt die weitere Entwicklung.

## Ziel

Der Begleiter soll NaC-Prozesse für notarielle Arbeitsabläufe vorbereiten und lokal kontrolliert an XNP-nahe Funktionen anbinden.

Mögliche Zielbereiche laut BNotK-Onlinehilfe:

- Login-Anstoss mit Karte oder Nutzername in XNP.
- UVZ-Suche und UVZ-Eintragsabfrage.
- Ermittlung der nächsten freien UVZ-Nummer.
- Erstellen von UVZ-Einträgen.
- Hinzufuegen von Dokumenten zu bestehenden UVZ-Einträgen.
- VVZ-Suche, VVZ-Abfrage und Erstellen von Verwahrungsmassen.

## Nicht-Ziele

- Keine Cloud-Steuerung von XNP.
- Keine Übertragung von XNP-API-Keys in NaC SaaS oder Git.
- Kein Zugriff ohne lokale XNP-Anmeldung und passende Amtstätigkeit.
- Keine Umgehung der BNotK-Schnittstellendefinition.
- Keine produktiven API-Aufrufe ohne ausdrückliche lokale Freigabe.

## Day0

- Zielrolle klären: Bürger-/Mandanten-Vorprüfung oder Notariatsarbeitsplatz.
- Bei Notariatsarbeitsplatz zuerst `Karte/SAK` abschließen: Karte, Kartenleser, PC/SC, SAK lite oder XNP-Kartenpfad und secureFramework.
- XNP-Installationskontext lokal prüfen.
- Lokale XNP-Anmeldung, Nutzerrolle und Amtstätigkeitskontext als Voraussetzung behandeln.
- Klären, ob die Notariatssoftware-Schnittstelle aktiv ist.
- Für Handelsregister-/HRA-Fälle XNotar-Modul und Datenaustauschverzeichnis klären.
- Lokale Port-Konfiguration dokumentieren, ohne Geheimnisse zu speichern.
- Offizielle Schnittstellendefinition beschaffen.
- Datenschutz-, Rollen- und AVV-Relevanz prüfen.
- NaC-Begleiter als lokale Komponente planen, nicht als Cloud-Service.

## Day1

- Lokalen Trockenlauf-Begleiter bauen:
  - lokalen Reader-Prompt für den cyberJack-Reader-Pfad erzeugen.
  - `nac-cyberjack-rfid`-Nachweis referenzieren.
  - XNP-Verfügbarkeit prüfen.
  - lokale Anmeldung und Amtstätigkeitskontext nur attestieren, nicht übertragen.
  - lokalen Port aus Konfiguration lesen oder per erlaubtem Discovery-Verfahren finden.
  - keine Login- oder API-Key-Daten speichern.
  - NaC-Intent in menschenlesbaren XNP-Plan übersetzen.
  - für Registerfälle XNotar-Austauschordner und XJustiz-Paketstruktur validieren.
  - Nutzer bestätigt lokal vor jedem echten Schritt.
- API-Aufrufe bleiben standardmäßig deaktiviert.
- Erst nach Freigabe:
  - einzelne UVZ/VVZ-Funktion im Testkontext.
  - Nachweis nur als Hash und Status.
  - keine Urkundeninhalte im Repo.

## Day2

- BNotK-Versionshinweise und XNP-Updates prüfen.
- Schnittstellenverhalten nach Wartungsupdates neu validieren.
- API-Key- und Port-Konfiguration lokal rezertifizieren.
- Begleiter-Protokolle lokal rotieren und minimieren.
- Drift zwischen NaC-Vorgang, XNP-Status und Nachweis als Issue erfassen.
- Exit-Pfad dokumentieren: XNP bleibt auch ohne NaC manuell bedienbar.

## Sicherheitsmodell

- Laufzeit nur auf dem lokalen Arbeitsplatz.
- Kommunikation nur gegen `localhost`.
- Leser-Prompt bleibt ein Trockenlauf und aktiviert keine produktive XNP-Aktion.
- Keine Remote-Portweiterleitung.
- Keine Geheimnisse in Git.
- Keine zentrale Speicherung von API-Keys.
- Nutzer- und Amtstätigkeitskontext wird lokal durch XNP validiert.
- NaC speichert nur nicht-sensitive Nachweise.

## Quellenbewertung

| Quelle | Befund | NaC-Folge |
| --- | --- | --- |
| BNotK Onlinehilfe XNP-Integration | XNP bietet einen lokalen REST-Endpunkt auf `localhost` an | Begleiter muss lokal laufen |
| BNotK Onlinehilfe XNP-Integration | Standard-Portsuche beginnt bei 12774 und endet bei 12784 | Port nicht hart codieren |
| BNotK Onlinehilfe XNP-Integration | Login-Token und aktuelle Amtstätigkeit werden für NSW-Aufrufe benötigt | keine Cloud-Ausführung |
| BNotK Onlinehilfe XNP-Integration | API-Key für Login-Funktion ist lokal konfiguriert und verschlüsselt nicht installationsübertragbar | keine Geheimnis-Synchronisierung |

## Akzeptanzkriterien für Pilot

- Begleiter startet nur lokal.
- Trockenlauf ist Standard.
- Leser-Prompt erzeugt Nachweise ohne PIN-, Karten-, API-Key- oder Login-Werte.
- XNP-Schnittstellendefinition ist dokumentiert.
- Jeder echte Aufruf erfordert lokale Nutzerbestätigung.
- Keine Urkunden-, UVZ-, VVZ- oder API-Key-Inhalte im Repo.
- Nachweis enthält Hash, Zeitstempel, Vorgangs-ID und lokalen Status.
- Manuelle XNP-Bedienung bleibt vollständig möglich.

## Quellen

- BNotK Onlinehilfe: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk/integration-xnp-mit-notariatssoftware.html`
- BNotK Onlinehilfe XNP: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html`
- BNotK Onlinehilfe XNotar: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnotar.html`
