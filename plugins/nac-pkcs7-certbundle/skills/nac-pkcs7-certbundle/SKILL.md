---
name: nac-pkcs7-certbundle
description: Lokale PKCS7-/P7B-/P7C-Zertifikatsbündel als metadatenbasierten Nachweis prüfen, ohne Signatur, Private-Key-Zugriff, PIN-Erfassung oder externe Aufrufe.
---

# PKCS7-Nachweis

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Inspect local PKCS#7, P7B or P7C certificate bundles as
metadata-only evidence. Do not request PFX/PKCS#12 files, PINs, passwords,
private keys, signing operations or external calls.

## Einsatzgrenze

Dieser Skill wird genutzt, wenn der Nutzer lokale PKCS#7-, P7B- oder
P7C-Zertifikatsbündel prüfen will und ausdrücklich keine Signatur- oder
Software-Token-Behandlung wünscht.

- PKCS#7-/P7B-/P7C-Dateien nur als Zertifikatsbündel-Evidence behandeln.
- Keine PFX-/PKCS#12-Software-Token-Dateien anfordern, importieren oder
  inspizieren.
- Keine PINs, Passwörter, privaten Schlüssel, Zertifikatswerte oder
  Client-Inhalte anfordern.
- Keine Signaturen erstellen oder prüfen.
- Kein Zertifikatsmaterial an externe Dienste senden.

## Ausführbare Prüfung

Vom Repository-Root:

```powershell
python plugins\nac-pkcs7-certbundle\scripts\inspect_certbundle.py --json
```

Mit lokalem Bündel:

```powershell
python plugins\nac-pkcs7-certbundle\scripts\inspect_certbundle.py --input C:\path\to\bundle.p7b --json
```

Die Ausgabe ist metadatenbasierte Evidence. Wenn der Nutzer Private-Key-, PFX-,
Signatur- oder qualifizierte-Signatur-Fähigkeiten verlangt, muss das in einen
separat freigegebenen Workstream geroutet werden.

## Rückgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Evidence`,
`Approval Needed` und `Day2 Follow-up`.

## Quellplan

- [docs/de/plugin-plans/local-codex-runtime.md](../../../../docs/de/plugin-plans/local-codex-runtime.md)
- [docs/en/plugin-plans/local-codex-runtime.md](../../../../docs/en/plugin-plans/local-codex-runtime.md)
