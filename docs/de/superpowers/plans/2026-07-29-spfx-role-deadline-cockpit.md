# Umsetzungsplan: SPFx Rollen- und Fristen-Cockpit

Status: `IMPLEMENTED_OFFLINE`

Datum: 29. Juli 2026
Führendes Issue: [#710](https://github.com/notariat8/NaC/issues/710)
Design: [SPFx Rollen- und Fristen-Cockpit](../specs/2026-07-29-spfx-role-deadline-cockpit-design.md)

## Ziel und Grenzen

Der Plan erweitert die bestehende read-only SPFx/BPMN-Arbeitsfläche für
`notary_team_01`. Er nutzt ausschließlich das strikt validierte synthetische
BFF-DTO und bestehende BPMN-Viewer-Verhalten. Es werden keine Graph-Browser-
Requests, Writes, Berechtigungsänderungen, App-Catalog-Deployments,
Site-Installationen oder Tenant-Aktionen ausgeführt.

Der initiale Referenzzeitpunkt wird am WebPart-Rand gebunden und als
`evaluationTimestamp` durchgereicht; die Komponente erneuert den sichtbaren
Fristenstand anschließend minütlich. Alle Filter- und Fristenableitungen
bleiben pure lokale ViewModel-Funktionen mit expliziter Zeit-Eingabe.
Current-Step bleibt read-only; Selected-Step ist ausschließlich lokale
Orientierung.

## AC-Zuordnung

| AC | Umsetzung | Nachweis |
| --- | --- | --- |
| `AC-710-01` | Filtermodell `all/open/deadline/notary`, Reihenfolge, Auswahlwechsel und ARIA | ViewModel- und Komponententests |
| `AC-710-02` | feste Referenzzeit, Grenzwerte und textredundante Fristenampel | ViewModel-Grenztests und visuelle Ampelprüfung |
| `AC-710-03` | `assigned/deputy`, Rollenrahmen, Notar-Badge und Freigabetext | Komponententests und Light/Dark-Screenshots |
| `AC-710-04` | getrennte Current-/Selected-Step-Marker und synchroner Detailbereich | Runtime-Vertrag und Komponententests |
| `AC-710-05` | Loading, Empty, Access-Denied, Fehler, Abort und genau ein Retry-Read | Komponententests und Fehler-Screenshot |
| `AC-710-06` | responsive/Dark, visueller Nachweis, Build und Repo-Gates | Evidence-Matrix und vollständige Validierung |

## Arbeitspakete

1. **Traceability und unveränderliche Grenze**
   - Issue #710, DE/EN-Specs, DE/EN-Pläne und `AC-710-01` bis
     `AC-710-06` binden.
   - Den bestehenden `Matter.Read`-BFF-Read, Exact-Shape-Parsing,
     Größenbegrenzung und BPMN-SHA-256-Verifikation unverändert erhalten.
   - Statisch prüfen, dass weder Graph-Client, Modeler, `saveXML` noch
     SharePoint-/Teams-Writepfade hinzukommen.

2. **ViewModel test-first ergänzen**
   - In `WorkspaceViewModel.test.ts` zuerst die vier stabilen Filter-IDs,
     DTO-Reihenfolge, `offen`/`open`-Normalisierung und leere Ergebnisse
     abdecken.
   - Den festen Testzeitpunkt `2026-08-25T16:00:00Z` verwenden und die
     Grenzen eine Millisekunde vor Referenzzeit, exakt an Referenzzeit, exakt
     sieben Tage sowie sieben Tage plus eine Millisekunde prüfen.
   - `none`, `overdue`, `urgent`, `scheduled` und ihre deutschen Textlabels
     sowie `assigned`/`deputy` testen.
   - In `WorkspaceViewModel.ts` erst danach die puren Ableitungen ohne
     impliziten Uhrzugriff implementieren.

3. **Referenzzeit und Rollenrahmen binden**
   - In `NacBpmnViewerWebPart.ts` einen initialen gültigen UTC-
     `evaluationTimestamp` pro Instanz binden und als Pflicht-Prop
     weiterreichen.
   - In `NacBpmnViewer.tsx` den sichtbaren Referenzstand alle 60 Sekunden sowie
     beim Retry erneuern und Vorgangs-/Aufgabenfristen ausschließlich gegen
     diesen expliziten Wert klassifizieren.
   - `accessMode`, Host-Anzeigename, Anzahl notarieller Freigaben, Notar-Badge
     und ausgeschriebenen Freigabestatus anzeigen, ohne daraus eine
     Berechtigungsentscheidung abzuleiten.

4. **Filter und Auswahl konsistent umsetzen**
   - Die Filter als Button-Gruppe mit sichtbarem Fokus, `aria-pressed` und
     stabilen Labels rendern; Treffer- und Gesamtzahl anzeigen.
   - Wenn ein Filter die Auswahl entfernt, die erste sichtbare Aufgabe in DTO-
     Reihenfolge auswählen. Bei null Treffern Detail und
     `nac-selected-step` entfernen.
   - Bei Aufgabenwahl Listenstatus, `data-nac-selected-step`, BPMN-Marker und
     Detailbereich atomar auf dieselbe `taskId`/`stepCode`-Bindung setzen.
   - `nac-current-step` niemals durch Filter oder Auswahl verändern. Fehlende,
     doppelte oder nicht kanonische BPMN-Tasks weiter fail-closed behandeln.

5. **Empty, Fehler und Retry absichern**
   - Loading, gefiltertes Empty, Access-Denied, BFF-Unverfügbarkeit,
     ungültiges BPMN und Renderfehler als getrennte Zustände testen.
   - Retry nur bei transienter Unverfügbarkeit, ungültigem Asset und
     Renderfehler anbieten; Access-Denied bleibt ohne Retry.
   - Beim Retry alten Viewer zerstören, laufenden Read abbrechen, Filter auf
     `all` zurücksetzen und genau einen neuen begrenzten BFF-Read starten.

6. **Responsive und Dark fertigstellen**
   - Breites Zwei-Spalten-Layout, Container-Ein-Spalten-Layout bis `760px` und
     gestapelte Zusammenfassung/Aufgaben bis `420px` prüfen.
   - Das BPMN auf schmalen Viewports scrollbar halten; Filter, lange
     UTC-Zeitstempel, Badges, Fokus und Retry ohne Überlauf oder Überdeckung
     darstellen.
   - Semantische Danger-/Warning-/Success-Tokens, Rollen-/Freigabestatus und
     getrennte Current-/Selected-Step-Marker in Light und Dark prüfen.

7. **Visuellen Nachweis erzeugen**
   - Einen eigenständigen synthetischen Offline-Visual-Contract mit
     Produktions-CSS, kanonischem BPMN und festem Anzeigenamen sowie
     `evaluationTimestamp=2026-08-25T16:00:00Z` verwenden; keine Tenant- oder
     Live-Verbindung öffnen und ihn nicht als React-/SPFx-E2E ausweisen.
   - `VIS-710-01` bis `VIS-710-06` aus der Spec exakt mit Viewport, Theme,
     Filter und Zustand aufnehmen.
   - Browser, Viewport, Containerbreite, Theme, Filter, Referenzzeit,
     vollständige SHA-256-Werte und Quellhashes im Manifest binden; der PR
     bindet dieses Manifest an den geprüften Head-Commit.
   - Vor Ablage auf echte Anzeigenamen, Mandatsdaten, Tenant-URLs, Tokens und
     Korrelationswerte prüfen.

8. **Validieren, reviewen und liefern**
   - Die folgenden Befehle aus dem Repository-Root ausführen:

     ```bash
     (cd spfx/nac-bpmn-viewer && npm run validate:current-step)
     (cd spfx/nac-bpmn-viewer && npm run build)
     python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
     python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
     python3 scripts/validate_spec_traceability.py
     python3 scripts/validate_language_parity.py
     python3 scripts/validate_doc_links.py
     git diff --check
     python3 scripts/nac.py doctor --profile strict
     ```

   - Vor PR-Freigabe die vollständige `origin/main...HEAD`-Diff, Dateiliste
     und Commitliste prüfen; fremde parallele Änderungen nicht revertieren.
   - `AC-710-01` bis `AC-710-06`, die sechs Evidence-IDs und die
     Befehlsausgaben im PR referenzieren.
   - Unabhängigen Review sowie grüne Remote-CI abwarten und ausschließlich
     über den geschützten PR gegen `main` liefern.

## Abnahmematrix

| Zustand | Automatisiert | Visuell |
| --- | --- | --- |
| vier Filter und Auswahlwechsel | ViewModel + Komponente | `VIS-710-01` bis `VIS-710-03` |
| Fristengrenzen und Textlabels | ViewModel | `VIS-710-01`, `VIS-710-03` |
| `assigned/deputy` und Notarfreigabe | ViewModel + Komponente | `VIS-710-01`, `VIS-710-03` |
| Current-/Selected-Step-Trennung | Runtime-Vertrag + Komponente | `VIS-710-01` |
| Empty und schmale Darstellung | Komponente | `VIS-710-02`, `VIS-710-04` |
| Fehler, Abort und Retry | Komponente | `VIS-710-05` |
| Read-only/BFF-Grenze | Python-Vertrag + statische Prüfung | Evidence-Datenprüfung |

## Done-Kriterien

- Alle sechs ACs sind mit automatisiertem oder visuellem Nachweis belegt.
- Der visuelle Nachweis deckt Desktop, schmal, Light, Dark, Empty und Retry ab.
- Build, fokussierte Tests, Spec-/Sprach-/Link-Validatoren,
  `git diff --check` und Strict Doctor bestehen.
- Die Oberfläche enthält nur synthetische Daten und bleibt innerhalb der
  bestehenden read-only BFF-Grenze.
- Die vollständige PR-Diff ist unabhängig geprüft; Remote-CI ist grün.
