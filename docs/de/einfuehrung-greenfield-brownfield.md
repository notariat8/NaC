# Einführung: Greenfield und Brownfield

## Ziel

Dieses Dokument trennt die Einführungspfade für:

- `greenfield`: Unternehmen ohne stabilen Vorprozess im Zielbereich,
- `brownfield`: Unternehmen mit bereits gelebten Altprozessen.

## Greenfield-Pfad

### Einstieg

1. Unternehmens-Fork aus dem Referenzmodell anlegen.
2. Rollen, Freigaben und Policies aktivieren.
3. 1-2 Kernprozesse als Pilot auswählen.
4. Pilot auf aktuellem freigegebenem Release starten.

### Rollout

1. Pilot bewerten (fachlich, regulatorisch, operativ).
2. Verbesserungen als Change Requests in den Fork übernehmen.
3. Unternehmens-Release taggen.
4. Stufenweise Ausweitung auf weitere Teams/Standorte.

## Brownfield-Pfad

### Einstieg

1. Bestehende Ist-Prozesse als `legacy`-Version dokumentieren.
2. Risiko- und Lueckenanalyse gegen Referenzmodell durchführen.
3. Priorisierte Zielprozesse für Migration auswählen.
4. Pilotbereich mit klarer Begrenzung festlegen.

### Migration in Stufen

1. `legacy`-Ablauf revisionssicher weiterführen.
2. Zielablauf als neue Version im Fork aufbauen.
3. Neue Vorgänge auf neue Version starten.
4. Laufende Altfall-Vorgänge auf `legacy` abschließen.
5. Nach Ende der Altfälle `legacy` geordnet außer Betrieb nehmen.

## Entscheidungsregeln für beide Pfade

- Kein Vollausrollung ohne Pilotnachweis.
- Jede produktive Prozessversion braucht Release-Tag und Freigabe.
- Bei Compliance-Konflikten hat Nachweisfähigkeit Vorrang vor Geschwindigkeit.
- Mischbetrieb wird über Version-Binding je Vorgangsstart gesteuert.

## 90-Tage-Orientierung

### Greenfield

- Tage 1-15: Zielbild, Rollen, Kernprozesse.
- Tage 16-45: Pilot für Rechnung/Buchführung.
- Tage 46-75: Ausweitung auf zusätzliche Prozesse.
- Tage 76-90: Stabilisierung und Release `v1.0.0`.

### Brownfield

- Tage 1-20: Ist-Prozesse aufnehmen und `legacy` definieren.
- Tage 21-50: Zielprozess modellieren, Pilot aufsetzen.
- Tage 51-75: Alt-/Neu-Mischbetrieb mit Version-Binding.
- Tage 76-90: Migration bewerten, weitere Umstellungen planen.
