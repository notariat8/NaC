# Notar-Start: NaC In 15 Minuten Einschaetzen

Dieses Dokument richtet sich an fachliche Entscheider im Notariat. Es erklärt,
was NaC ist, was es nicht ist und wie ein erster lokaler Prüflauf ohne echte
Mandatsdaten aussieht.

## Kurzbild

NaC ist ein Muster für AI-first-Betrieb im Notariat:

- KI strukturiert Eingaben und offene Fragen.
- Fachpersonal und Notar entscheiden.
- Git dokumentiert Versionen, Reviews und Freigaben.
- Python prüft Regeln und Vollständigkeit.
- Echte Mandatsdaten bleiben außerhalb dieses öffentlichen Repositories.

## Was Sie Damit Prüfen Können

1. Welche notariellen Vorgangsarten bereits modelliert sind.
2. Welche Informationen, Dokumente, Freigaben und technischen Gates je Vorgang
   benötigt werden.
3. Welche Plugin- und Arbeitsplatzvoraussetzungen für Karten-, Register-,
   Portal- oder Identitätspfade entstehen.
4. Ob das Modell zu Ihrem Bürobetrieb passt.
5. Welche Teile in einen privaten Fork übernommen werden sollen.

## Was Sie Nicht Tun Sollten

- keine echten Mandatsdaten in dieses Repository eintragen,
- keine Ausweisdaten, Registerauszüge, Preise, PINs oder Zertifikate committen,
- keine KI-Ausgabe als finale rechtliche Entscheidung behandeln,
- keinen Produktivbetrieb ohne privaten Fork, Rollenmodell, Datenschutzprüfung
  und lokale Freigaben starten.

## Erster Prüflauf

```bash
python scripts/nac.py status
python scripts/nac.py kg editor-view immobilienkaufvertrag
python scripts/nac.py doctor --profile strict
```

Wenn diese Befehle laufen, können Sie sehen, welche Usecases vorhanden sind,
welche offenen Knoten ein Vorgang hat und ob das Repository seine eigenen Gates
besteht.

## Entscheidungsfragen

- Welche drei Vorgangsarten sollen zuerst pilotiert werden?
- Wer ist fachlich verantwortlich für Freigaben?
- Wer betreibt den privaten Fork?
- Welche lokalen Fachsysteme und Arbeitsplätze müssen angebunden werden?
- Wo werden echte Mandatsdokumente und Nachweise außerhalb von Git gespeichert?

## Nächste Dokumente

- [docs/de/reifegrad.md](reifegrad.md)
- [cli.md](cli.md)
- [ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [docs/de/glossar.md](glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../../usecases/README.md)
- [docs/de/minimum-requirements.md](minimum-requirements.md)
- [docs/de/security-and-dsgvo.md](security-and-dsgvo.md)
- [docs/de/kg-editor-workstream.md](kg-editor-workstream.md)
- [docs/de/betriebsstart.md](betriebsstart.md)
