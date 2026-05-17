# Notar-Start: NoC In 15 Minuten Einschaetzen

Dieses Dokument richtet sich an fachliche Entscheider im Notariat. Es erklaert,
was NoC ist, was es nicht ist und wie ein erster lokaler Prueflauf ohne echte
Mandatsdaten aussieht.

## Kurzbild

NoC ist ein Muster fuer AI-first-Betrieb im Notariat:

- KI strukturiert Eingaben und offene Fragen.
- Fachpersonal und Notar entscheiden.
- Git dokumentiert Versionen, Reviews und Freigaben.
- Python prueft Regeln und Vollstaendigkeit.
- Echte Mandatsdaten bleiben ausserhalb dieses oeffentlichen Repositories.

## Was Sie Damit Pruefen Koennen

1. Welche notariellen Vorgangsarten bereits modelliert sind.
2. Welche Informationen, Dokumente, Freigaben und technischen Gates je Vorgang
   benoetigt werden.
3. Welche Plugin- und Arbeitsplatzvoraussetzungen fuer Karten-, Register-,
   Portal- oder Identitaetspfade entstehen.
4. Ob das Modell zu Ihrem Buerobetrieb passt.
5. Welche Teile in einen privaten Fork uebernommen werden sollen.

## Was Sie Nicht Tun Sollten

- keine echten Mandatsdaten in dieses Repository eintragen,
- keine Ausweisdaten, Registerauszuege, Preise, PINs oder Zertifikate committen,
- keine KI-Ausgabe als finale rechtliche Entscheidung behandeln,
- keinen Produktivbetrieb ohne privaten Fork, Rollenmodell, Datenschutzpruefung
  und lokale Freigaben starten.

## Erster Prueflauf

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
python scripts/quality_gate.py --profile strict
```

Wenn diese Befehle laufen, koennen Sie sehen, welche Usecases vorhanden sind,
welche offenen Knoten ein Vorgang hat und ob das Repository seine eigenen Gates
besteht.

## Entscheidungsfragen

- Welche drei Vorgangsarten sollen zuerst pilotiert werden?
- Wer ist fachlich verantwortlich fuer Freigaben?
- Wer betreibt den privaten Fork?
- Welche lokalen Fachsysteme und Arbeitsplaetze muessen angebunden werden?
- Wo werden echte Mandatsdokumente und Nachweise ausserhalb von Git gespeichert?

## Naechste Dokumente

- [docs/de/reifegrad.md](reifegrad.md)
- [docs/de/glossar.md](glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../../usecases/README.md)
- [docs/de/minimum-requirements.md](minimum-requirements.md)
- [docs/de/security-and-dsgvo.md](security-and-dsgvo.md)
- [docs/de/kg-editor-workstream.md](kg-editor-workstream.md)
- [docs/de/betriebsstart.md](betriebsstart.md)
