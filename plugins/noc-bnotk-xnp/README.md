# NoC XNP-Notariatspruefung

Installierbares lokales Codex-Plugin fuer Notariate und Notariatsarbeitsplaetze.
Es schaltet Online-HRA und andere notarielle Registerablaeufe erst frei,
nachdem `noc-cyberjack-rfid` lokalen Kartenleser, BNotK-SAK-lite- oder
XNP-Kartenpfad sowie secureFramework-Voraussetzungen bestaetigt hat. Das Plugin
kann eine lokale XNP-Leser-Vorpruefung fuer den cyberJack-RFID-Leser erzeugen
und prueft danach lokale XNP-Bereitschaft, lokale Authentifizierung,
Amtstaetigkeitskontext-Bestaetigung, XNotar-/Registerpaket-Uebergabe,
API-Key-Vorhandensein als Bestaetigung und Nachweisfluss, ohne XNP-Zugangsdaten
in SaaS oder Git zu speichern.

## Status

Lauffaehiges lokales MVP. Fuer notarielle Handelsregister- oder HRA-Ablaeufe
steht dieses Plugin im repo-lokalen Codex-Marktplatz nach `noc-cyberjack-rfid`
und vor `noc-handelsregister`. Externe Schreibadapter sind in dieser ersten
Version bewusst nicht aktiviert.

## Lauffaehige Leser-Vorpruefung

Lokale XNP-Leser-Vorpruefung aus dem Repository-Root starten:

```powershell
python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --json
```

Fuer eine durch Bedienpersonal bestaetigte Workstation-Pruefung:

```powershell
python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --manual-card-present yes --manual-rfid-off yes --output out\xnp-reader-prompt.json
```

Das fuehrt keinen XNP-Login aus und ruft keinen produktiven XNP-Schreibendpunkt
auf. Es erzeugt einen lokalen Trockenlauf-Prompt fuer die freigegebene cyberJack-
Leserroute, ruft die `noc-cyberjack-rfid`-Bereitschaft-Pruefung auf, prueft nur die
XNP-Localhost-Ports `12774` bis `12784` und schreibt Nachweise gemaess
`contracts/reader-prompt-evidence.schema.json`.

Um die aktive morris-Browser-Middleware- und PC/SC-List-Readers-Pruefung aus dem
cyberJack-Pruefung einzubeziehen:

```powershell
python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --json --probe-morris-api
```

Der Prompt dient der Pruefung lokaler Leserreaktion, nicht der Aktivierung
kontaktlosen RFID in einem BNotK-Chipkarten-Arbeitsablauf. Keine PINs, Kartenwerte,
Zertifikate, Passwoerter oder XNP-API-Keys in Codex eingeben.

## Installationsgrenze

- Laeuft als lokales Codex-Plugin aus diesem Repository.
- Ist ueber `.agents/plugins/marketplace.json` fuer den Notariats-/XNP-Pruefung-
  Usecase installierbar.
- Erfordert abgeschlossene `noc-cyberjack-rfid`-Karten-/SAK-Bereitschaft vor
  XNP-Login-Tests.
- Erzeugt ueber `scripts/reader_prompt.py` einen lokalen Trockenlauf-
Leser-Prompt zur Pruefung des cyberJack-Leserpfads vor XNP-Login-Tests.
- Haelt Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte ausserhalb von Git.
- Behandelt lokalen XNP-Login und Amtstaetigkeitskontext als Pruefung vor
  Registerablauf-Automatisierung.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Verlangt menschliche Freigabe fuer regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- XNP-Installation im selben Workstation-/Nutzerkontext bestaetigen.
- `noc-cyberjack-rfid`-Bereitschaft fuer Karte, Sicherheitsklasse-3-Leser,
  SAK-lite-/XNP-Kartenpfad und secureFramework bestaetigen.
- Lokalen XNP-Login, Nutzerrolle und Amtstaetigkeitskontext bestaetigen, ohne
  Werte zu speichern.
- XNotar-Modul oder Austauschordner-Route fuer Registerablaeufe bestaetigen.
- Herstellersupport der Notariatssoftware und lokale Admin-Zustaendigkeit
  bestaetigen.

## Day1

- Lokalen Leser-Prompt-Nachweis, Authentifizierungspruefung,
  XNotar-Uebergabe-Bereitschaftsplan und Nachweisgeruest ohne Zugangswerte
  erstellen.

## Day2

- Lokalen Schnittstellenstatus nach XNP- oder Notariatssoftware-Updates erneut
  zertifizieren.

## Erforderliche Konten und Freigaben

- BNotK-/XNP-Zugang fuer das Notariat
- abgeschlossene `noc-cyberjack-rfid`-Karten-/SAK-Bereitschaft
- lokaler XNP-Login und aktiver Amtstaetigkeitskontext
- XNotar-/Registermodul oder Austauschordner-Route
- Freigabe der Herstellerschnittstelle der Notariatssoftware
- lokale Workstation-Admin-Freigabe

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
