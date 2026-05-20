# XNP-Prüfung

Installierbares lokales Codex-Plugin für Notariate und Notariatsarbeitsplätze.
Es schaltet Online-HRA und andere notarielle Registerabläufe erst frei,
nachdem `nac-cyberjack-rfid` lokalen Kartenleser, BNotK-SAK-lite- oder
XNP-Kartenpfad sowie secureFramework-Voraussetzungen bestätigt hat. Das Plugin
kann eine lokale XNP-Leser-Vorprüfung für den cyberJack-RFID-Leser erzeugen
und prüft danach lokale XNP-Bereitschaft, lokale Authentifizierung,
Amtstätigkeitskontext-Bestätigung, XNotar-/Registerpaket-Übergabe,
API-Key-Vorhandensein als Bestätigung und Nachweisfluss, ohne XNP-Zugangsdaten
in SaaS oder Git zu speichern.

## Status

Lauffähiges lokales MVP. Für notarielle Handelsregister- oder HRA-Abläufe
steht dieses Plugin im repo-lokalen Codex-Marktplatz nach `nac-cyberjack-rfid`
und vor `nac-handelsregister`. Externe Schreibadapter sind in dieser ersten
Version bewusst nicht aktiviert.

## Lauffähige Leser-Vorprüfung

Lokale XNP-Leser-Vorprüfung aus dem Repository-Root starten:

```powershell
python plugins\nac-bnotk-xnp\scripts\reader_prompt.py --json
```

Für eine durch Bedienpersonal bestätigte Workstation-Prüfung:

```powershell
python plugins\nac-bnotk-xnp\scripts\reader_prompt.py --manual-card-present yes --manual-rfid-off yes --output out\xnp-reader-prompt.json
```

Das führt keinen XNP-Login aus und ruft keinen produktiven XNP-Schreibendpunkt
auf. Es erzeugt einen lokalen Trockenlauf-Prompt für die freigegebene cyberJack-
Leserroute, ruft die `nac-cyberjack-rfid`-Bereitschaft-Prüfung auf, prüft nur die
XNP-Localhost-Ports `12774` bis `12784` und schreibt Nachweise gemaess
`contracts/reader-prompt-evidence.schema.json`.

Um die aktive morris-Browser-Middleware- und PC/SC-List-Readers-Prüfung aus dem
cyberJack-Prüfung einzubeziehen:

```powershell
python plugins\nac-bnotk-xnp\scripts\reader_prompt.py --json --probe-morris-api
```

Der Prompt dient der Prüfung lokaler Leserreaktion, nicht der Aktivierung
kontaktlosen RFID in einem BNotK-Chipkarten-Arbeitsablauf. Keine PINs, Kartenwerte,
Zertifikate, Passwörter oder XNP-API-Keys in Codex eingeben.

## Installationsgrenze

- Läuft als lokales Codex-Plugin aus diesem Repository.
- Ist über `.agents/plugins/marketplace.json` für den Notariats-/XNP-Prüfung-
  Usecase installierbar.
- Erfordert abgeschlossene `nac-cyberjack-rfid`-Karten-/SAK-Bereitschaft vor
  XNP-Login-Tests.
- Erzeugt über `scripts/reader_prompt.py` einen lokalen Trockenlauf-
Leser-Prompt zur Prüfung des cyberJack-Leserpfads vor XNP-Login-Tests.
- Hält Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte außerhalb von Git.
- Behandelt lokalen XNP-Login und Amtstätigkeitskontext als Prüfung vor
  Registerablauf-Automatisierung.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Verlangt menschliche Freigabe für regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- XNP-Installation im selben Workstation-/Nutzerkontext bestätigen.
- `nac-cyberjack-rfid`-Bereitschaft für Karte, Sicherheitsklasse-3-Leser,
  SAK-lite-/XNP-Kartenpfad und secureFramework bestätigen.
- Lokalen XNP-Login, Nutzerrolle und Amtstätigkeitskontext bestätigen, ohne
  Werte zu speichern.
- XNotar-Modul oder Austauschordner-Route für Registerabläufe bestätigen.
- Herstellersupport der Notariatssoftware und lokale Admin-Zuständigkeit
  bestätigen.

## Day1

- Lokalen Leser-Prompt-Nachweis, Authentifizierungsprüfung,
  XNotar-Übergabe-Bereitschaftsplan und Nachweisgerüst ohne Zugangswerte
  erstellen.

## Day2

- Lokalen Schnittstellenstatus nach XNP- oder Notariatssoftware-Updates erneut
  zertifizieren.

## Erforderliche Konten und Freigaben

- BNotK-/XNP-Zugang für das Notariat
- abgeschlossene `nac-cyberjack-rfid`-Karten-/SAK-Bereitschaft
- lokaler XNP-Login und aktiver Amtstätigkeitskontext
- XNotar-/Registermodul oder Austauschordner-Route
- Freigabe der Herstellerschnittstelle der Notariatssoftware
- lokale Workstation-Admin-Freigabe

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
