# Einfuehrung: Greenfield und Brownfield

## Ziel

Dieses Dokument trennt die Einfuehrungspfade fuer:

- `greenfield`: Unternehmen ohne stabilen Vorprozess im Zielbereich,
- `brownfield`: Unternehmen mit bereits gelebten Altprozessen.

## Greenfield-Pfad

### Einstieg

1. Unternehmens-Fork aus dem Referenzmodell anlegen.
2. Rollen, Freigaben und Policies aktivieren.
3. 1-2 Kernprozesse als Pilot auswaehlen.
4. Pilot auf aktuellem freigegebenem Release starten.

### Rollout

1. Pilot bewerten (fachlich, regulatorisch, operativ).
2. Verbesserungen als Change Requests in den Fork uebernehmen.
3. Unternehmens-Release taggen.
4. Stufenweise Ausweitung auf weitere Teams/Standorte.

## Brownfield-Pfad

### Einstieg

1. Bestehende Ist-Prozesse als `legacy`-Version dokumentieren.
2. Risiko- und Lueckenanalyse gegen Referenzmodell durchfuehren.
3. Priorisierte Zielprozesse fuer Migration auswaehlen.
4. Pilotbereich mit klarer Begrenzung festlegen.

### Migration in Stufen

1. `legacy`-Ablauf revisionssicher weiterfuehren.
2. Zielablauf als neue Version im Fork aufbauen.
3. Neue Vorgaenge auf neue Version starten.
4. Laufende Altfall-Vorgaenge auf `legacy` abschliessen.
5. Nach Ende der Altfaelle `legacy` geordnet ausser Betrieb nehmen.

## Entscheidungsregeln fuer beide Pfade

- Kein Vollausrollung ohne Pilotnachweis.
- Jede produktive Prozessversion braucht Release-Tag und Freigabe.
- Bei Compliance-Konflikten hat Nachweisfaehigkeit Vorrang vor Geschwindigkeit.
- Mischbetrieb wird ueber Version-Binding je Vorgangsstart gesteuert.

## 90-Tage-Orientierung

### Greenfield

- Tage 1-15: Zielbild, Rollen, Kernprozesse.
- Tage 16-45: Pilot fuer Rechnung/Buchfuehrung.
- Tage 46-75: Ausweitung auf zusaetzliche Prozesse.
- Tage 76-90: Stabilisierung und Release `v1.0.0`.

### Brownfield

- Tage 1-20: Ist-Prozesse aufnehmen und `legacy` definieren.
- Tage 21-50: Zielprozess modellieren, Pilot aufsetzen.
- Tage 51-75: Alt-/Neu-Mischbetrieb mit Version-Binding.
- Tage 76-90: Migration bewerten, weitere Umstellungen planen.
