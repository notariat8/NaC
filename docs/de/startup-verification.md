# Startup Verification

## Was geprueft wird

Der Startup-Check prueft lokal:

- benoetigte Commands (`git`, `python`, `gh`)
- empfohlene Commands (`pandoc`, `code`)
- Mindest-Python-Version
- Pflichtdateien und Policies
- optional VS-Code-Copilot-Extensions
- optional Prozessvalidierung und Tests

## So fuehrst du den Check aus

Nur Setup pruefen:

```bash
python scripts/startup_check.py --ide auto
```

Setup plus Fach- und Testlauf:

```bash
python scripts/startup_check.py --ide auto --run-tests
```

Fuer VS Code strikt (inkl. Copilot Extensions):

```bash
python scripts/startup_check.py --ide vscode --run-tests
```

## Grenzen

- Der Check sieht nur lokal verfuegbare Informationen.
- Er ersetzt keine GitHub-Servereinstellungen (z. B. Branch Protection).
- Fuer Forks muss der Check ebenfalls uebernommen und aktiv genutzt werden.
