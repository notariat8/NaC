# NoC PKCS7-Zertifikatsnachweis

Installierbares lokales Codex-Plugin fuer metadatenbasierte PKCS#7/P7B/P7C-
Zertifikatsbuendel-Nachweise. Dieser Arbeitsstrang ist bewusst kein
Signaturprovider. Er laedt keine privaten Schluessel, importiert keine
PFX-/PKCS#12-Softwaretokens, fragt keine PINs ab, erzeugt keine Signaturen,
prueft keine Signaturen und ruft keine externen Dienste auf.

## Status

Lauffaehiges lokales MVP. Das Plugin kann nachweisen, dass eine lokale
Workstation einen unterstuetzten Parserpfad besitzt und ein lokales
PKCS#7-Zertifikatsbuendel ausschliesslich als Nachweis-Metadaten inspizieren
kann.

## Lauffaehiges MVP

Lokale Pruefung aus dem Repository-Root starten:

```powershell
python plugins\noc-pkcs7-certbundle\scripts\inspect_certbundle.py --json
```

Lokales Buendel inspizieren:

```powershell
python plugins\noc-pkcs7-certbundle\scripts\inspect_certbundle.py --input C:\path\to\bundle.p7b --json
```

`--strict` in Automatisierung nutzen, wenn ein fehlendes oder nicht parsbares
Buendel einen Exit-Code ungleich null liefern soll. Das erzeugte JSON folgt
`contracts/certbundle-evidence.schema.json` und speichert nur Metadaten wie
Dateigroesse, Erweiterung, Hashes, Parserverfuegbarkeit und
Zertifikatsanzahl-Signale, sofern der lokale Parser diese bereitstellt.

## Grenze

- Nur lokaler PKCS#7/P7B/P7C-Zertifikatsbuendel-Nachweis.
- Kein PFX-/PKCS#12-Import.
- Kein Private-Key-Zugriff.
- Keine PIN-Erfassung.
- Keine Speicherung von Zertifikatsmaterial in Git.
- Keine Signaturerzeugung und keine Signaturpruefung.
- Keine externen Netzwerkaufrufe.
- Kein Ersatz fuer BNotK-Karte, XNP, SAK-lite oder qualifizierte Signaturablaeufe.

## Day0

- Bestaetigen, ob das Quellartefakt ein PKCS#7/P7B/P7C-Zertifikatsbuendel und
  kein Softwaretoken ist.
- Lokale Parserverfuegbarkeit ueber Windows `certutil.exe` oder OpenSSL
  bestaetigen.
- Bestaetigen, dass der Nachweis-Ausgabepfad ausserhalb von Mandatsdatenordnern
  liegt, sofern nicht explizit freigegeben.

## Day1

- `scripts/inspect_certbundle.py` gegen das lokale Zertifikatsbuendel ausfuehren.
- Nur die fuer Review benoetigten Metadaten-Nachweise speichern.
- Softwaretoken-, PFX-, Private-Key- oder Signaturanforderungen in einen
  separaten freigegebenen Arbeitsstrang verweisen.

## Day2

- Nachweispruefung nach Zertifikatsketten-, Workstation- oder Parseraenderungen
  erneut ausfuehren.
- Buendel-Fingerprints und Parserstatus als Drift-Nachweis vergleichen.

## Erforderliche Konten und Freigaben

- lokale Workstation-Freigabe
- Freigabe der Zertifikatsbuendel-Quelle
- Sicherheitsreview vor jeder Erweiterung ueber reine Metadateninspektion hinaus
- separate Freigabe fuer jede kuenftige Softwaretoken-, Private-Key-,
  Remote-Signatur- oder qualifizierte-Signatur-Integration
