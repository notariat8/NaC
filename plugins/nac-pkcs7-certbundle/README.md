# PKCS7-Nachweis

Installierbares lokales Codex-Plugin für metadatenbasierte PKCS#7/P7B/P7C-
Zertifikatsbündel-Nachweise. Dieser Arbeitsstrang ist bewusst kein
Signaturprovider. Er laedt keine privaten Schlüssel, importiert keine
PFX-/PKCS#12-Softwaretokens, fragt keine PINs ab, erzeugt keine Signaturen,
prüft keine Signaturen und ruft keine externen Dienste auf.

## Status

Lauffähiges lokales MVP. Das Plugin kann nachweisen, dass eine lokale
Workstation einen unterstützten Parserpfad besitzt und ein lokales
PKCS#7-Zertifikatsbündel ausschließlich als Nachweis-Metadaten inspizieren
kann.

## Lauffähiges MVP

Lokale Prüfung aus dem Repository-Root starten:

```powershell
python plugins\nac-pkcs7-certbundle\scripts\inspect_certbundle.py --json
```

Lokales Bündel inspizieren:

```powershell
python plugins\nac-pkcs7-certbundle\scripts\inspect_certbundle.py --input C:\path\to\bundle.p7b --json
```

`--strict` in Automatisierung nutzen, wenn ein fehlendes oder nicht parsbares
Bündel einen Exit-Code ungleich null liefern soll. Das erzeugte JSON folgt
`contracts/certbundle-evidence.schema.json` und speichert nur Metadaten wie
Dateigroesse, Erweiterung, Hashes, Parserverfügbarkeit und
Zertifikatsanzahl-Signale, sofern der lokale Parser diese bereitstellt.

## Grenze

- Nur lokaler PKCS#7/P7B/P7C-Zertifikatsbündel-Nachweis.
- Kein PFX-/PKCS#12-Import.
- Kein Private-Key-Zugriff.
- Keine PIN-Erfassung.
- Keine Speicherung von Zertifikatsmaterial in Git.
- Keine Signaturerzeugung und keine Signaturprüfung.
- Keine externen Netzwerkaufrufe.
- Kein Ersatz für BNotK-Karte, XNP, SAK-lite oder qualifizierte Signaturabläufe.

## Day0

- Bestätigen, ob das Quellartefakt ein PKCS#7/P7B/P7C-Zertifikatsbündel und
  kein Softwaretoken ist.
- Lokale Parserverfügbarkeit über Windows `certutil.exe` oder OpenSSL
  bestätigen.
- Bestätigen, dass der Nachweis-Ausgabepfad außerhalb von Mandatsdatenordnern
  liegt, sofern nicht explizit freigegeben.

## Day1

- `scripts/inspect_certbundle.py` gegen das lokale Zertifikatsbündel ausführen.
- Nur die für Review benötigten Metadaten-Nachweise speichern.
- Softwaretoken-, PFX-, Private-Key- oder Signaturanforderungen in einen
  separaten freigegebenen Arbeitsstrang verweisen.

## Day2

- Nachweisprüfung nach Zertifikatsketten-, Workstation- oder Parseränderungen
  erneut ausführen.
- Bündel-Fingerprints und Parserstatus als Drift-Nachweis vergleichen.

## Erforderliche Konten und Freigaben

- lokale Workstation-Freigabe
- Freigabe der Zertifikatsbündel-Quelle
- Sicherheitsreview vor jeder Erweiterung über reine Metadateninspektion hinaus
- separate Freigabe für jede künftige Softwaretoken-, Private-Key-,
  Remote-Signatur- oder qualifizierte-Signatur-Integration
