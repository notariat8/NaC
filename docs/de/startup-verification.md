# Startup Verification

## Was geprueft wird

Der Startup-Check prueft lokal:

- benoetigte Commands (`git`, `python`, `gh`)
- profilabhaengige Commands (`node`, `npm`)
- empfohlene Commands (`pandoc`, `code`)
- Mindest-Python-Version
- Mindest-Node-Version fuer Plugin-Arbeit, sofern das Profil sie verlangt
- Pflichtdateien und Policies
- optional VS-Code-Copilot-Extensions
- optional Prozessvalidierung und Tests
- lokale Windows-/morris-/Treiber-Indikatoren fuer den Notariatsarbeitsplatz

## So fuehrst du den Check aus

Base-Setup pruefen:

```bash
python scripts/startup_check.py --profile base --ide auto
```

Base-Setup plus Fach- und Testlauf:

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
```

Fuer VS Code strikt (inkl. Copilot Extensions):

```bash
python scripts/startup_check.py --profile base --ide vscode --run-tests
```

Fuer Plugin-Entwicklung:

```bash
python scripts/startup_check.py --profile plugin-dev --ide auto
```

Fuer Notariatsarbeitsplatz, Kartenleser, morris und XNP-Pfad:

```bash
python scripts/startup_check.py --profile notary-workstation --ide auto
```

## Grenzen

- Der Check sieht nur lokal verfuegbare Informationen.
- Er ersetzt keine GitHub-Servereinstellungen (z. B. Branch Protection).
- Er ersetzt keine echte Fachsystemfreigabe und keine Kartenaktion.
- Eine morris-Antwort wie `NoReader` oder `NoCard` reicht fuer die technische
  Middleware-Anbindungspruefung, aber nicht fuer einen produktiven Kartenlauf.
- Fuer Forks muss der Check ebenfalls uebernommen und aktiv genutzt werden.
