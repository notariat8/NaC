# Karte/SAK

Installierbares lokales Codex-Plugin für notarielle Kartenbereitschaft vor
XNP-Login und Online-HRA-Arbeit. Es prüft Verfügbarkeit der
BNotK-Chip-/Signaturkarte, REINER-SCT-cyberJack-Leserbereitschaft,
Sicherheitsklasse-3-Leseranforderungen, PC/SC-Status, BNotK-SAK-lite- oder
XNP-Kartenpfad, secureFramework-Bereitschaft, XNP-Local-Interface-Voraussetzungen
und Nachweis-Metadaten ohne PIN-Erfassung, API-Key-Erfassung oder
Kartendatenextraktion.

## Status

Lauffähiges lokales MVP. Für notarielle Online-HRA steht dieses Plugin vor
`nac-bnotk-xnp`, weil XNP-Login erst getestet werden kann, wenn der lokale
Kartenpfad bereit ist. Externe Schreibadapter sind in dieser ersten Version
bewusst nicht aktiviert.

## Lauffähiges MVP

Lokale Bereitschaftsprüfung aus dem Repository-Root starten:

```powershell
python plugins\nac-cyberjack-rfid\scripts\check_readiness.py --json
```

Für eine durch Bedienpersonal bestätigte lokale Workstation-Prüfung:

```powershell
python plugins\nac-cyberjack-rfid\scripts\check_readiness.py --manual-card-present yes --manual-rfid-off yes --output out\cyberjack-bereitschaft.json
```

`--strict` in Automatisierung nutzen, wenn jeder nicht-bereite Zustand einen
Exit-Code ungleich null liefern soll. Das erzeugte JSON folgt
`contracts/readiness-evidence.schema.json` und speichert nur Metadaten: lokalen
Komponentenstatus, manuelle Bestätigungen, anonymisierte Leser-Fingerprints,
Erreichbarkeit von XNP-Localhost-Ports und Erreichbarkeit des AusweisApp-Status.

Um die lokale morris-Browser-Middleware und den PC/SC-Pfad aktiv zu prüfen,
ohne Kartendaten zu lesen:

```powershell
python plugins\nac-cyberjack-rfid\scripts\check_readiness.py --json --probe-morris-api
```

Das nutzt ausschließlich `http://127.0.0.1:8800`, führt `system::check`, einen
lokalen `system::auth`-Handshake, `system::list_provider`,
`pcsc::establishcontext` und `pcsc::listreaders` aus und speichert nur redigierte
Metadaten. Eine morris-Antwort wie `NoReader` oder `NaCard` gilt als erfolgreiche
Middleware-Bindung; physische cyberJack-Bereitschaft bleibt eine separate
Lesererkennungsprüfung.

Die Prüfung liest keine PINs, Kartenwerte, Zertifikate, XNP-API-Keys,
Portalsitzungen oder Mandatsinhalte. RFID-aus wird als manuelle Bestätigung
erfasst, bis eine geprüfte Hersteller- oder Betriebssystem-Schnittstelle dies
deterministisch bestätigen kann.

## Windows-DriverPackage-Erkennung

Unter Windows erkennt die Bereitschaftsprüfung den lokalen REINER-SCT-Stack am
Standardpfad:

```text
C:\Program Files\REINER SCT\DriverPackage
```

Geprüft werden DriverPackage-Control-Center, PC/SC-Bibliothek, Windows-10-x64-
Treiberdateien, CT-API-DLL und der von `pnputil` gemeldete installierte
REINER-SCT-SmartCardReader-Provider. Angeschlossene Leserhardware wird separat
geprüft. Ein erfolgreich installiertes DriverPackage beweist allein nicht, dass
aktuell ein cyberJack-Leser angeschlossen ist.

## morris Browser-Middleware

REINER SCT beschreibt morris als Middleware, mit der Browseranwendungen vom
lokalen Kunden-PC auf den Chipkartenleser zugreifen können. Wo morris
installiert ist, prüft die Bereitschaftsprüfung die lokale Middleware ohne
Kartenoperation:

- `C:\Program Files (x86)\REINER SCT\morris`
- Windows-Dienststatus `morris`
- Prozesse `morrisServer` und `morrisDispatcherService`
- lokale Named-Pipe-Endpunkte wie `net.pipe://localhost/morris`

Das kann für browsergeführte Bedienerprüfungen der einfachere Integrationsweg
sein, bleibt in NaC aber lokal und metadatenbasiert. Das Plugin darf morris
nicht nutzen, um PINs, Kartendaten, Zertifikate oder produktive Portalaktionen
anzufordern.

Mit `--probe-morris-api` prüft das Bereitschaftsskript zusätzlich die echte
morris-Localhost-API. Auf der aktuellen Workstation liefert die API `status=0`
für morris, Autorisierung, lizenzierte Provider und PC/SC-List-Readers; aktuell
wird kein REINER-SCT-/cyberJack-Leser von morris zurückgegeben.

## Linux-Treiber und Omnistation-Labor

REINER SCT dokumentiert Linux-Unterstützung für cyberJack-Leser und weist
darauf hin, dass viele Linux-Distributionen cyberJack-Treiber bereits in ihren
Standardpaketquellen bereitstellen. Unter Linux prüft die
Bereitschaftsprüfung auch den lokalen Treiberstack:

- `cyberjack`-Paket, sofern Debian/Ubuntu- oder RPM-Paketdatenbanken verfügbar sind
- Signale für `pcscd`, `pcsc-tools` und `libccid`/PCSC-Pakete, sofern verfügbar
- USB-Sichtbarkeit über `lsusb`
- PC/SC-Lesersichtbarkeit über `pcsc_scan -n`

Auf der Ziel-Linux-Maschine ausführen:

```bash
python3 plugins/nac-cyberjack-rfid/scripts/check_readiness.py --json
```

Omnistation ist hier nur als kontrolliertes Hardwarelabor sinnvoll, wenn der
cyberJack-USB-Leser in den Omnistation-Desktop durchgereicht wird. Ein
Cloud-Desktop ohne USB-Passthrough kann den physischen Leser nicht verifizieren.
Die Repository-Policy sagt aktuell, dass Omnistation kein NaC-Ausführungs-
Workspace ist; die Nutzung für dieses Hardwarelabor braucht daher vor der
Treiberinstallation eine dokumentierte Policy-Ausnahme oder ein Policy-Update.

## Installationsgrenze

- Läuft als lokales Codex-Plugin aus diesem Repository.
- Ist über `.agents/plugins/marketplace.json` vor `nac-bnotk-xnp` installierbar.
- Hält Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte außerhalb von Git.
- Behandelt BNotK-Chip-/Signaturkartenverfügbarkeit, kompatiblen
  Sicherheitsklasse-3-Leser, SAK-lite/XNP, secureFramework und
  XNP-Local-Interface-Bereitschaft als Prüfung vor XNP-Login-Tests.
- Behandelt RFID als Leserfähigkeit, nicht als notariellen Kartenarbeitsablauf. Hat
  der Leser eine RFID-Funktion, lautet die BNotK-Leitlinie, sie für
  Chipkartenabläufe deaktiviert zu lassen, sofern kein konkreter kontaktloser
  Einsatz explizit benötigt wird.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Erzeugt lokales Bereitschafts-Nachweis-JSON über `scripts/check_readiness.py`.
- Verlangt menschliche Freigabe für regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- Verfügbarkeit der BNotK-Chip-/Signaturkarte bestätigen, ohne Kartenwerte zu lesen.
- Sicherheitsklasse-3-Lesermodell, Treiberquelle, PC/SC-Dienst und lokalen
  Admin-Pfad bestätigen.
- Unter Windows REINER-SCT-DriverPackage-Pfad, Treiberdateien und installierten
  SmartCardReader-Provider bestätigen.
- Unter Windows morris-Browser-Middleware-Installation und laufenden lokalen
  Dienst bestätigen, sofern verfügbar.
- Unter Linux cyberJack-Treiberpaket-Verfügbarkeit oder Installation,
  PC/SC-Daemon-Status und USB-/PCSC-Lesersichtbarkeit bestätigen.
- Klären, ob der Leser eine RFID-Funktion hat und ob sie für den
  BNotK-Chipkarten-Arbeitsablauf deaktiviert ist.
- BNotK-SAK-lite- oder XNP-Kartenpfad und secureFramework-Bereitschaft bestätigen.
- XNP-Local-Webservice-Interface nur als Metadaten bestätigen: aktiv/inaktiv,
  localhost-only-Bindung, konfigurierte Portspanne und ob API-Key-Setup
  erforderlich ist. API-Key nicht speichern.

## Day1

- `scripts/check_readiness.py` für Kartenleser, RFID-aus, SAK-lite-/XNP-
  Kartenpfad, secureFramework und XNP-Local-Interface-Bereitschaft vor
  XNP-Login-Tests ausführen.

## Day2

- Kartenleser, Treiber, Firmware, PC/SC-Dienst, SAK-lite-/XNP-Kartenpfad und
  secureFramework-Bereitschaft erneut zertifizieren.

## Erforderliche Konten und Freigaben

- freigegebene Hardwarebeschaffung
- BNotK-Chip-/Signaturkartenverfügbarkeit
- Sicherheitsklasse-3-Kartenleser
- RFID-Funktion deaktiviert, sofern vorhanden und nicht explizit benötigt
- BNotK-SAK-lite- oder XNP-Kartenpfad
- secureFramework-Kommunikationspfad
- XNP-Local-Interface-Konfiguration ohne Speicherung von API-Keys geprüft
- lokale Workstation-Admin-Freigabe
- Treiber-/Herstellersupportkanal

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
