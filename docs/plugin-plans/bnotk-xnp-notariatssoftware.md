# Plugin Plan: BNotK XNP Notariatssoftware Companion

Status: `draft`

## Kernentscheidung

XNP darf nicht aus der Cloud gesteuert werden.
Ein OaC-Plugin fuer XNP wird als lokaler Companion geplant, der im selben Arbeitsplatz- und Benutzerkontext laeuft wie XNP.

OaC SaaS oder Remote-Ausfuehrung bekommen nur:

- Workflow-Status,
- Policy-Entscheidungen,
- Hashes,
- nicht-sensitive Evidence,
- Freigabe- und Audit-Metadaten.

Direkte API-Calls bleiben deaktiviert, bis die offizielle BNotK-Schnittstellendefinition lokal vorliegt und fachlich freigegeben ist.

## Ziel

Der Companion soll OaC-Prozesse fuer notarielle Arbeitsablaeufe vorbereiten und lokal kontrolliert an XNP-nahe Funktionen anbinden.

Moegliche Zielbereiche laut BNotK-Onlinehilfe:

- Login-Anstoss mit Karte oder Nutzername in XNP.
- UVZ-Suche und UVZ-Eintragsabfrage.
- Ermittlung der naechsten freien UVZ-Nummer.
- Erstellen von UVZ-Eintraegen.
- Hinzufuegen von Dokumenten zu bestehenden UVZ-Eintraegen.
- VVZ-Suche, VVZ-Abfrage und Erstellen von Verwahrungsmassen.

## Nicht-Ziele

- Keine Cloud-Steuerung von XNP.
- Keine Uebertragung von XNP-API-Keys in OaC SaaS oder Git.
- Kein Zugriff ohne lokale XNP-Anmeldung und passende Amtstaetigkeit.
- Keine Umgehung der BNotK-Schnittstellendefinition.
- Keine produktiven API-Calls ohne ausdrueckliche lokale Freigabe.

## Day0

- XNP-Installationskontext lokal pruefen.
- Klaeren, ob die Notariatssoftware-Schnittstelle aktiv ist.
- Lokale Port-Konfiguration dokumentieren, ohne Secrets zu speichern.
- Offizielle Schnittstellendefinition beschaffen.
- Datenschutz-, Rollen- und AVV-Relevanz pruefen.
- OaC-Companion als lokale Komponente planen, nicht als Cloud-Service.

## Day1

- Lokalen Dry-run Companion bauen:
  - XNP-Verfuegbarkeit pruefen.
  - lokalen Port aus Konfiguration lesen oder per erlaubtem Discovery-Verfahren finden.
  - keine Login- oder API-Key-Daten speichern.
  - OaC-Intent in menschenlesbaren XNP-Plan uebersetzen.
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
- Drift zwischen OaC-Vorgang, XNP-Status und Evidence als Issue erfassen.
- Exit-Pfad dokumentieren: XNP bleibt auch ohne OaC manuell bedienbar.

## Sicherheitsmodell

- Laufzeit nur auf dem lokalen Arbeitsplatz.
- Kommunikation nur gegen `localhost`.
- Keine Remote-Portweiterleitung.
- Keine Secrets in Git.
- Keine zentrale Speicherung von API-Keys.
- Nutzer- und Amtstaetigkeitskontext wird lokal durch XNP validiert.
- OaC speichert nur nicht-sensitive Evidence.

## Quellenbewertung

| Quelle | Befund | OaC-Folge |
| --- | --- | --- |
| BNotK Onlinehilfe XNP-Integration | XNP bietet einen lokalen REST-Endpunkt auf `localhost` an | Companion muss lokal laufen |
| BNotK Onlinehilfe XNP-Integration | Standard-Portsuche beginnt bei 12774 und endet bei 12784 | Port nicht hart codieren |
| BNotK Onlinehilfe XNP-Integration | Login-Token und aktuelle Amtstaetigkeit werden fuer NSW-Aufrufe benoetigt | keine Cloud-Ausfuehrung |
| BNotK Onlinehilfe XNP-Integration | API-Key fuer Login-Funktion ist lokal konfiguriert und verschluesselt nicht installationsuebertragbar | keine Secret-Synchronisierung |

## Akzeptanzkriterien fuer Pilot

- Companion startet nur lokal.
- Dry-run ist Standard.
- XNP-Schnittstellendefinition ist dokumentiert.
- Jeder echte Aufruf erfordert lokale Nutzerbestaetigung.
- Keine Urkunden-, UVZ-, VVZ- oder API-Key-Inhalte im Repo.
- Evidence enthaelt Hash, Zeitstempel, Vorgangs-ID und lokalen Status.
- Manuelle XNP-Bedienung bleibt vollstaendig moeglich.

## Quellen

- BNotK Onlinehilfe: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk/integration-xnp-mit-notariatssoftware.html`
- BNotK Onlinehilfe XNP: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html`
- BNotK Onlinehilfe XNotar: `https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnotar.html`
