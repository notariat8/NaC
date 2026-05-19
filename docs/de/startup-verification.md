# Startup Verification

## Was geprüft wird

Der Startup-Check prüft lokal:

- benötigte Commands (`git`, `python`, `gh`)
- profilabhängige Commands (`node`, `npm`)
- empfohlene Commands (`pandoc`, `code`)
- Mindest-Python-Version
- Mindest-Node-Version für Plugin-Arbeit, sofern das Profil sie verlangt
- Pflichtdateien und Policies
- optional VS-Code-Copilot-Extensions
- optional Prozessvalidierung und Tests
- lokale Windows-/morris-/Treiber-Indikatoren für den Notariatsarbeitsplatz

## So führst du den Check aus

Base-Setup prüfen:

```bash
python scripts/startup_check.py --profile base --ide auto
```

Base-Setup plus Fach- und Testlauf:

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
```

Für VS Code strikt (inkl. Copilot Extensions):

```bash
python scripts/startup_check.py --profile base --ide vscode --run-tests
```

Für Plugin-Entwicklung:

```bash
python scripts/startup_check.py --profile plugin-dev --ide auto
```

Für Notariatsarbeitsplatz, Kartenleser, morris und XNP-Pfad:

```bash
python scripts/startup_check.py --profile notary-workstation --ide auto
python scripts/nac.py plugins card-readiness --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
python scripts/nac.py plugins xnp-reader-prompt --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
```

## Grenzen

- Der Check sieht nur lokal verfügbare Informationen.
- Er ersetzt keine GitHub-Servereinstellungen (z. B. Branch Protection).
- Er ersetzt keine echte Fachsystemfreigabe.
- Bei installierter Hardware sind echte lokale Kartenleser-, morris-, PC/SC-,
  SAK-/XNP- und XNP-Readiness-Tests möglich. Produktive Kartenläufe,
  Signaturen, PIN-Erfassung und Einreichungen bleiben gesondert freizugeben.
- Eine morris-Antwort wie `NoReader` oder `NaCard` reicht ohne eingelegte oder
  angeschlossene Karte für die technische Middleware-Anbindungsprüfung, aber
  nicht für einen produktiven Kartenlauf.
- Für Forks muss der Check ebenfalls übernommen und aktiv genutzt werden.
