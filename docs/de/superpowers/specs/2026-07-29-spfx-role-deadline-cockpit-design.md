# SPFx Rollen- und Fristen-Cockpit

Status: `IMPLEMENTED_OFFLINE`

Datum: 29. Juli 2026
Führendes Issue: [#710](https://github.com/notariat8/NaC/issues/710)
Scope: synthetische, read-only SPFx-Arbeitsfläche für `notary_team_01`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: spfx-role-deadline-cockpit
leading_issue: https://github.com/notariat8/NaC/issues/710
risk_gate: None
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-29-spfx-role-deadline-cockpit.md
review_gates:
  - Privacy
  - Human Approval
acceptance_ids:
  - AC-710-01
  - AC-710-02
  - AC-710-03
  - AC-710-04
  - AC-710-05
  - AC-710-06
validation_commands:
  - cd spfx/nac-bpmn-viewer && npm run validate:current-step
  - cd spfx/nac-bpmn-viewer && npm run build
  - python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
  - python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
  - python3 scripts/nac.py doctor --profile strict
```

## Ziel

Die bestehende SPFx/BPMN-Arbeitsfläche wird zu einem scanbaren Rollen-,
Fristen- und Aufgaben-Cockpit erweitert. Die Oberfläche bleibt eine
read-only Projektion des synthetischen BFF-DTOs. Sie hilft bei Auswahl und
Orientierung, verändert aber weder Aufgabenstatus noch Prozessinstanz,
Current-Step, Berechtigungen oder Tenant-Daten.

## Scope

Im Scope liegen:

- ausschließlich der synthetische Workspace `notary_team_01` und der
  synthetische Vorgang `NAC-SYN-MATTER-001`,
- lokale Filterung der bereits geladenen Aufgaben mit `all`, `open`,
  `deadline` und `notary`,
- deterministische Fristenklassifikation aus einem explizit gebundenen
  Referenzzeitpunkt,
- sichtbarer Zugriffsmodus `assigned` oder `deputy`, angemeldete Rolle und
  notarielle Freigabegrenze,
- konsistente Aufgabenauswahl in Liste, Detailbereich und BPMN-Markierung,
- Loading-, Empty-, Access-Denied-, Fehler- und Retry-Zustände,
- responsive Darstellung sowie Light- und Dark-Theme,
- fokussierte automatisierte Prüfungen und visueller Nachweis.

Nicht im Scope liegen:

- neue BFF-Endpunkte, neue Graph-Berechtigungen oder Browserzugriffe auf
  Microsoft Graph,
- Änderungen am BFF-DTO außerhalb der vorhandenen strikt validierten Felder,
- Schreiben von BPMN, Aufgaben, Vorgängen, SharePoint-Listen, Dokumenten,
  Teams-Einstellungen, Rollen oder Vertretungen,
- App-Catalog-Deployment, Site-Installation, Tenant-Aktion oder Live-Smoke,
- echte Mandatsdaten oder produktive Identitäten.

## Read-only- und BFF-Grenze

Der Browser lädt genau den vorhandenen, strikt geformten Workspace über den
delegierten NaC-BFF-Scope `Matter.Read`. Der `NacBffClient` begrenzt Größe und
Feldform und verifiziert das kanonische BPMN-XML per SHA-256. Die Oberfläche
verwendet ausschließlich `matter.accessMode`, `matter.deadline`,
`matter.tasks` und das verifizierte BPMN-Modell.

Filter, Fristenstatus und Auswahl sind reine in-memory ViewModel-Ableitungen.
Sie erzeugen keinen zweiten Datenpfad und keine Mutation. Retry wiederholt nur
denselben begrenzten BFF-Read, bricht einen noch laufenden Read ab und setzt den
lokalen Filter auf `all` zurück. `401` und `403` bleiben als Access-Denied
ohne Retry geschlossen. Kein UI-Label darf als eigene
Berechtigungsentscheidung interpretiert werden; maßgeblich bleibt die
serverseitige BFF-Entscheidung.

## Expliziter Referenzzeitpunkt

Der SPFx-WebPart bindet pro Viewer-Instanz einen initialen UTC-Zeitstempel als
`evaluationTimestamp`. Die Komponente übernimmt ihn explizit und erneuert ihren
sichtbaren Fristenstand anschließend alle 60 Sekunden aus der Browseruhr. Der
jeweils verwendete Stand bleibt im Cockpit sichtbar. Filterung, Auswahl und die
puren ViewModel-Funktionen greifen nie implizit auf die Uhr zu; jede Ableitung
erhält ihren Referenzzeitpunkt als Argument. Ein Retry setzt den Stand ebenfalls
auf einen aktuellen UTC-Zeitstempel.

`evaluationTimestamp` und `dueAt` werden als gültige ISO-8601-UTC-Zeitstempel
mit `Z` ausgewertet. Die automatisierten Grenztests und die synthetische
Visual-Evidence verwenden verbindlich `2026-08-25T16:00:00Z`. `dueAt=null`
wird als `none` behandelt. Ein ungültiger Referenz- oder Fristzeitstempel
verletzt dagegen den bereits validierten DTO-Vertrag und führt fail-closed in
den Render-Fehlerzustand.

## Filtervertrag

Die vier stabilen technischen IDs und ihre deutschen Anzeigenamen sind:

| ID | Anzeige | Prädikat |
| --- | --- | --- |
| `all` | Alle Aufgaben | alle Aufgaben in DTO-Reihenfolge |
| `open` | Offene Aufgaben | Status nach Trim und Kleinschreibung exakt `offen` oder `open` |
| `deadline` | Aufgaben mit Frist | `dueAt` ist nicht `null` |
| `notary` | Aufgaben mit Notarfreigabe | `requiresNotaryApproval` ist `true` |

Die Filter sind eine barrierearme Button-Gruppe mit sichtbarem Fokus und
`aria-pressed`. Ergebniszahl und Gesamtzahl bleiben sichtbar. Bleibt die
ausgewählte Aufgabe im Ergebnis, bleibt die Auswahl stabil. Andernfalls wird
deterministisch die erste sichtbare Aufgabe ausgewählt. Bei null Treffern
werden Aufgabendetail und Selected-Step-Markierung entfernt; der unveränderte
Current-Step bleibt sichtbar.

## Fristenampel

Die Ampel ist immer redundant durch Text bezeichnet und darf nicht nur über
Farbe kommunizieren:

| Status | Regel relativ zu `evaluationTimestamp` | Anzeige |
| --- | --- | --- |
| `none` | `dueAt` ist `null` | Keine Frist |
| `overdue` | `dueAt < evaluationTimestamp` | Frist überschritten |
| `urgent` | Restzeit von null bis einschließlich sieben Tagen | Frist innerhalb von sieben Tagen |
| `scheduled` | Restzeit größer als sieben Tage | Frist geplant |

`overdue`, `urgent` und `scheduled` verwenden semantische Danger-, Warning-
und Success-Tokens mit ausreichendem Kontrast in Light und Dark. Der
Vorgangstermin und jede Aufgabenfrist zeigen neben der lokal formatierten
Zeit weiterhin den gebundenen UTC-Wert, damit die Ableitung prüfbar bleibt.

## Rollen-, Vertretungs- und Freigabeanzeige

`accessMode=assigned` erscheint als `Zugeordnetes Team (assigned)`,
`accessMode=deputy` als `Aktive Vertretung (deputy)`. Der Rollenrahmen zeigt den vom
Host bereitgestellten Anzeigenamen und die Anzahl der Aufgaben mit notarieller
Freigabe. Jede betroffene Aufgabe trägt zusätzlich den Text-Badge `Notar`; im
Detailbereich steht ausgeschrieben, ob notarielle Freigabe erforderlich ist.

Die Anzeige erweitert keine Befugnis. Insbesondere führt eine Vertretungs- oder
Notaranzeige weder eine Rollenänderung noch eine Freigabe aus.

## Auswahl und BPMN-Konsistenz

Der erste DTO-Eintrag ist der read-only Current-Step. Seine
`nac-current-step`-Markierung wird einmal gesetzt und durch Filter oder Auswahl
nicht verschoben. Eine Aufgabenwahl setzt separat `nac-selected-step`,
aktualisiert `aria-pressed`, `data-nac-selected-step` und den Detailbereich auf
dieselbe `taskId`/`stepCode`-Bindung. Fehlende, doppelte oder nicht als
`bpmn:Task` validierbare Step-Codes führen fail-closed in den
Render-Fehlerzustand.

## Empty, Fehler und Retry

- Während des Reads wird ein eindeutiger Loading-Status angezeigt.
- Ein leerer Filter zeigt `Keine passenden Aufgaben` und lässt die Filter zur
  Korrektur bedienbar.
- Access-Denied zeigt keine technischen Details und keinen Retry.
- BFF-Unverfügbarkeit, ungültiges BPMN oder Renderfehler zeigen einen
  verständlichen Fehler und `Erneut laden`.
- Retry setzt lokale Filter- und Auswahlableitungen zurück, zerstört die alte
  Viewer-Instanz und startet genau einen neuen BFF-Read.
- Fehlertexte, Fokuszustände und Aktionen bleiben per Tastatur erreichbar.

## Responsive und Dark

Auf breiten WebPart-Containern stehen BPMN und Arbeitsvorrat nebeneinander.
Container Queries, nicht die Browserbreite, schalten bei maximal `760px` auf
eine Spalte; das BPMN bleibt horizontal scrollbar und wird nicht unlesbar
verkleinert. Bei maximal `420px` Containerbreite werden Zusammenfassung und
Aufgabenzeilen gestapelt. Filter, Badges, Zeitstempel und Retry dürfen weder
überlaufen noch andere Inhalte überdecken.

Dark-Theme wird ausschließlich aus dem SPFx-Hosttheme abgeleitet. Alle
Statusfarben, Focus-Ringe, Text- und Flächenkontraste sowie Current- und
Selected-Step müssen in beiden Themes unterscheidbar bleiben.

## Visueller Nachweis

Der reproduzierbare Playwright-Lauf rendert einen eigenständigen synthetischen
Offline-Visual-Contract. Er verwendet die exakte produktive Stylesheet-Quelle,
das kanonische BPMN und `bpmn-js`, aber nicht die gebündelte React-Komponente,
den BFF oder einen SPFx-/SharePoint-Host. Deshalb ist er ausdrücklich kein
Komponenten- oder Live-E2E-Test. React-Verhalten, ARIA-Zustände, Retry und
Uhrfortschreibung werden separat durch die 82 SPFx-Tests abgedeckt; ein echter
Host-E2E bleibt Teil eines späteren owner-gated Deployments.

Die PNGs sind Element-Crops innerhalb der angegebenen Viewports:

| Evidence-ID | Viewport/Container/Theme | Pflichtzustand |
| --- | --- | --- |
| `VIS-710-01` | `1440x1000`, voller Container, Light | `all`, Rollenrahmen, Ampel, getrennte Current-/Selected-Markierung und Detail |
| `VIS-710-02` | `390x844`, voller Container, Light | schmale einspaltige Ansicht mit `deadline` und horizontal nutzbarem BPMN |
| `VIS-710-03` | `1440x1000`, voller Container, Dark | `notary`, lesbare Rollen-/Freigabe- und Ampelzustände |
| `VIS-710-04` | `390x844`, voller Container, Dark | Empty-State und funktionale Rückkehr zu `all` ohne Überlauf oder Überdeckung |
| `VIS-710-05` | `390x320`, Light | transienter Fehler mit funktionalem Retry und Narrow-Container-Prüfung |
| `VIS-710-06` | `1440x1000`, `390px` WebPart-Container, Light | Container-Query bei breitem Browser ohne Überlauf oder Überdeckung |

Versionierte synthetische Evidence:

- [VIS-710-01 Desktop Light](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-01-desktop-light.png) (`26432468...83f6fe`)
- [VIS-710-02 Narrow Light](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-02-narrow-light.png) (`1293bf10...aaa86f`)
- [VIS-710-03 Desktop Dark](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-03-desktop-dark.png) (`dee4419c...84bb2d`)
- [VIS-710-04 Narrow Dark Empty](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-04-narrow-dark-empty.png) (`09584ea0...d521e8`)
- [VIS-710-05 Fehler/Retry](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-05-error-retry.png) (`279cea84...4eb559`)
- [VIS-710-06 Narrow Container](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-06-narrow-container-light.png) (`d0a67f9e...d2decc`)
- [Evidence-Manifest](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-manifest.json) (`nac.spfx-role-deadline-visual-evidence/v0.2`)

Das Manifest bindet Chromium-Version, Referenzzeitpunkt, Query, Viewport,
Containerbreite, vollständige Screenshot-Hashes und die Hashes aller
Visual-Contract-Quellen. Der lokale Lauf bestätigt ohne Tenant-Zugriff: keinen
Seitenüberlauf, keinen abgeschnittenen Text, 41 gerenderte BPMN-Elemente in
jedem Ready-Zustand, genau einen Current-Step, höchstens einen Selected-Step
sowie funktionale Empty- und Retry-Recovery. Der PR bindet das Manifest an den
geprüften Head-Commit.

Screenshots dürfen keine echten Anzeigenamen, Mandatsdaten, Tenant-URLs, Tokens
oder Korrelationswerte enthalten.

## Akzeptanzkriterien

- **AC-710-01:** `all`, `open`, `deadline` und `notary` filtern
  deterministisch in DTO-Reihenfolge, sind per Tastatur bedienbar und zeigen
  Auswahl sowie Trefferzahl konsistent.
- **AC-710-02:** Friststatus und Ampel werden ausschließlich aus dem explizit
  gebundenen Referenzzeitpunkt mit getesteten Grenzwerten abgeleitet und
  zusätzlich als Text ausgegeben.
- **AC-710-03:** Rollenrahmen, `assigned`/`deputy` und notarielle
  Freigabegrenze sind lesbar sichtbar, ohne Berechtigung oder Freigabe zu
  verändern.
- **AC-710-04:** Aufgabenwahl hält Liste, Detail und Selected-Step synchron,
  während Current-Step und sämtliche Serverdaten unverändert bleiben.
- **AC-710-05:** Loading, Empty, Access-Denied, Fehler und begrenzter Retry
  sind robust, barrierearm und ohne zusätzlichen Daten- oder Schreibpfad.
- **AC-710-06:** Desktop-, schmale, Light- und Dark-Ansichten bestehen den
  visuellen Nachweis; SPFx-Build, fokussierte Tests, Repo-Validatoren,
  `nac doctor --profile strict`, unabhängiger Review und geschützter PR sind
  grün.
