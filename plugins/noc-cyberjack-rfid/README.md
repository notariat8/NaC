# NoC Karten- und SAK-Pruefung

Installierbares lokales Codex-Plugin fuer notarielle Kartenbereitschaft vor
XNP-Login und Online-HRA-Arbeit. Es prueft Verfuegbarkeit der
BNotK-Chip-/Signaturkarte, REINER-SCT-cyberJack-Leserbereitschaft,
Sicherheitsklasse-3-Leseranforderungen, PC/SC-Status, BNotK-SAK-lite- oder
XNP-Kartenpfad, secureFramework-Bereitschaft, XNP-Local-Interface-Voraussetzungen
und Nachweis-Metadaten ohne PIN-Erfassung, API-Key-Erfassung oder
Kartendatenextraktion.

## Status

Lauffaehiges lokales MVP. Fuer notarielle Online-HRA steht dieses Plugin vor
`noc-bnotk-xnp`, weil XNP-Login erst getestet werden kann, wenn der lokale
Kartenpfad bereit ist. Externe Schreibadapter sind in dieser ersten Version
bewusst nicht aktiviert.

## Lauffaehiges MVP

Lokale Bereitschaftspruefung aus dem Repository-Root starten:

```powershell
python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json
```

Fuer eine durch Bedienpersonal bestaetigte lokale Workstation-Pruefung:

```powershell
python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --manual-card-present yes --manual-rfid-off yes --output out\cyberjack-bereitschaft.json
```

`--strict` in Automatisierung nutzen, wenn jeder nicht-bereite Zustand einen
Exit-Code ungleich null liefern soll. Das erzeugte JSON folgt
`contracts/readiness-evidence.schema.json` und speichert nur Metadaten: lokalen
Komponentenstatus, manuelle Bestaetigungen, anonymisierte Leser-Fingerprints,
Erreichbarkeit von XNP-Localhost-Ports und Erreichbarkeit des AusweisApp-Status.

Um die lokale morris-Browser-Middleware und den PC/SC-Pfad aktiv zu pruefen,
ohne Kartendaten zu lesen:

```powershell
python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json --probe-morris-api
```

Das nutzt ausschliesslich `http://127.0.0.1:8800`, fuehrt `system::check`, einen
lokalen `system::auth`-Handshake, `system::list_provider`,
`pcsc::establishcontext` und `pcsc::listreaders` aus und speichert nur redigierte
Metadaten. Eine morris-Antwort wie `NoReader` oder `NoCard` gilt als erfolgreiche
Middleware-Bindung; physische cyberJack-Bereitschaft bleibt eine separate
Lesererkennungspruefung.

Die Pruefung liest keine PINs, Kartenwerte, Zertifikate, XNP-API-Keys,
Portalsitzungen oder Mandatsinhalte. RFID-aus wird als manuelle Bestaetigung
erfasst, bis eine gepruefte Hersteller- oder Betriebssystem-Schnittstelle dies
deterministisch bestaetigen kann.

## Windows-DriverPackage-Erkennung

Unter Windows erkennt die Bereitschaftspruefung den lokalen REINER-SCT-Stack am
Standardpfad:

```text
C:\Program Files\REINER SCT\DriverPackage
```

Geprueft werden DriverPackage-Control-Center, PC/SC-Bibliothek, Windows-10-x64-
Treiberdateien, CT-API-DLL und der von `pnputil` gemeldete installierte
REINER-SCT-SmartCardReader-Provider. Angeschlossene Leserhardware wird separat
geprueft. Ein erfolgreich installiertes DriverPackage beweist allein nicht, dass
aktuell ein cyberJack-Leser angeschlossen ist.

## morris Browser-Middleware

REINER SCT beschreibt morris als Middleware, mit der Browseranwendungen vom
lokalen Kunden-PC auf den Chipkartenleser zugreifen koennen. Wo morris
installiert ist, prueft die Bereitschaftspruefung die lokale Middleware ohne
Kartenoperation:

- `C:\Program Files (x86)\REINER SCT\morris`
- Windows-Dienststatus `morris`
- Prozesse `morrisServer` und `morrisDispatcherService`
- lokale Named-Pipe-Endpunkte wie `net.pipe://localhost/morris`

Das kann fuer browsergefuehrte Bedienerpruefungen der einfachere Integrationsweg
sein, bleibt in NoC aber lokal und metadatenbasiert. Das Plugin darf morris
nicht nutzen, um PINs, Kartendaten, Zertifikate oder produktive Portalaktionen
anzufordern.

Mit `--probe-morris-api` prueft das Bereitschaftsskript zusaetzlich die echte
morris-Localhost-API. Auf der aktuellen Workstation liefert die API `status=0`
fuer morris, Autorisierung, lizenzierte Provider und PC/SC-List-Readers; aktuell
wird kein REINER-SCT-/cyberJack-Leser von morris zurueckgegeben.

## Linux-Treiber und Omnistation-Labor

REINER SCT dokumentiert Linux-Unterstuetzung fuer cyberJack-Leser und weist
darauf hin, dass viele Linux-Distributionen cyberJack-Treiber bereits in ihren
Standardpaketquellen bereitstellen. Unter Linux prueft die
Bereitschaftspruefung auch den lokalen Treiberstack:

- `cyberjack`-Paket, sofern Debian/Ubuntu- oder RPM-Paketdatenbanken verfuegbar sind
- Signale fuer `pcscd`, `pcsc-tools` und `libccid`/PCSC-Pakete, sofern verfuegbar
- USB-Sichtbarkeit ueber `lsusb`
- PC/SC-Lesersichtbarkeit ueber `pcsc_scan -n`

Auf der Ziel-Linux-Maschine ausfuehren:

```bash
python3 plugins/noc-cyberjack-rfid/scripts/check_readiness.py --json
```

Omnistation ist hier nur als kontrolliertes Hardwarelabor sinnvoll, wenn der
cyberJack-USB-Leser in den Omnistation-Desktop durchgereicht wird. Ein
Cloud-Desktop ohne USB-Passthrough kann den physischen Leser nicht verifizieren.
Die Repository-Policy sagt aktuell, dass Omnistation kein NoC-Ausfuehrungs-
Workspace ist; die Nutzung fuer dieses Hardwarelabor braucht daher vor der
Treiberinstallation eine dokumentierte Policy-Ausnahme oder ein Policy-Update.

## Installationsgrenze

- Laeuft als lokales Codex-Plugin aus diesem Repository.
- Ist ueber `.agents/plugins/marketplace.json` vor `noc-bnotk-xnp` installierbar.
- Haelt Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte ausserhalb von Git.
- Behandelt BNotK-Chip-/Signaturkartenverfuegbarkeit, kompatiblen
  Sicherheitsklasse-3-Leser, SAK-lite/XNP, secureFramework und
  XNP-Local-Interface-Bereitschaft als Pruefung vor XNP-Login-Tests.
- Behandelt RFID als Leserfaehigkeit, nicht als notariellen Kartenarbeitsablauf. Hat
  der Leser eine RFID-Funktion, lautet die BNotK-Leitlinie, sie fuer
  Chipkartenablaeufe deaktiviert zu lassen, sofern kein konkreter kontaktloser
  Einsatz explizit benoetigt wird.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Erzeugt lokales Bereitschafts-Nachweis-JSON ueber `scripts/check_readiness.py`.
- Verlangt menschliche Freigabe fuer regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- Verfuegbarkeit der BNotK-Chip-/Signaturkarte bestaetigen, ohne Kartenwerte zu lesen.
- Sicherheitsklasse-3-Lesermodell, Treiberquelle, PC/SC-Dienst und lokalen
  Admin-Pfad bestaetigen.
- Unter Windows REINER-SCT-DriverPackage-Pfad, Treiberdateien und installierten
  SmartCardReader-Provider bestaetigen.
- Unter Windows morris-Browser-Middleware-Installation und laufenden lokalen
  Dienst bestaetigen, sofern verfuegbar.
- Unter Linux cyberJack-Treiberpaket-Verfuegbarkeit oder Installation,
  PC/SC-Daemon-Status und USB-/PCSC-Lesersichtbarkeit bestaetigen.
- Klaeren, ob der Leser eine RFID-Funktion hat und ob sie fuer den
  BNotK-Chipkarten-Arbeitsablauf deaktiviert ist.
- BNotK-SAK-lite- oder XNP-Kartenpfad und secureFramework-Bereitschaft bestaetigen.
- XNP-Local-Webservice-Interface nur als Metadaten bestaetigen: aktiv/inaktiv,
  localhost-only-Bindung, konfigurierte Portspanne und ob API-Key-Setup
  erforderlich ist. API-Key nicht speichern.

## Day1

- `scripts/check_readiness.py` fuer Kartenleser, RFID-aus, SAK-lite-/XNP-
  Kartenpfad, secureFramework und XNP-Local-Interface-Bereitschaft vor
  XNP-Login-Tests ausfuehren.

## Day2

- Kartenleser, Treiber, Firmware, PC/SC-Dienst, SAK-lite-/XNP-Kartenpfad und
  secureFramework-Bereitschaft erneut zertifizieren.

## Erforderliche Konten und Freigaben

- freigegebene Hardwarebeschaffung
- BNotK-Chip-/Signaturkartenverfuegbarkeit
- Sicherheitsklasse-3-Kartenleser
- RFID-Funktion deaktiviert, sofern vorhanden und nicht explizit benoetigt
- BNotK-SAK-lite- oder XNP-Kartenpfad
- secureFramework-Kommunikationspfad
- XNP-Local-Interface-Konfiguration ohne Speicherung von API-Keys geprueft
- lokale Workstation-Admin-Freigabe
- Treiber-/Herstellersupportkanal

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
