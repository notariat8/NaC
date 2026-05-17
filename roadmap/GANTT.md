# NoC Globaler Gantt

Letzte Aktualisierung: 2026-05-17

Jedes Change-Set mit repo-relevanten Dateien muss diesen globalen Gantt
mitpflegen. Repo-relevant sind alle Aenderungen ausser generierten Artefakten
unter `out/` und Git-Interna. Aenderungen unter `plugins/`, `workflows/` oder
`usecases/` muessen zusaetzlich den passenden Themen-Gantt mitpflegen:

- `plugins/GANTT.md`
- `workflows/GANTT.md`
- `usecases/GANTT.md`

```mermaid
gantt
    title NoC globaler Lieferplan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section A: Plugins und Marketplace-Readiness
    Plugin-Inventar und Installierbarkeitsgate   :done,    a1, 2026-04-01, 2026-05-14
    GPT-Store-/Workspace-Paketierung trennen     :active,  a2, 2026-05-14, 21d
    IDaaS-Plugin-Migration                       :active,  a3, 2026-05-14, 14d
    Repository-Konsolidierungsledger             :active,  a4, 2026-05-14, 7d
    Lokaler PKCS7-Zertifikatsbuendel-Nachweis    :active,  a4a, 2026-05-15, 14d
    SBOM fuer AI-Governance-Basis                :active,  a4b, 2026-05-15, 21d
    Runtime-/HW-Mindestanforderungs-SBOM         :active,  a4c, 2026-05-15, 14d
    Deutsche Plugin-MD-Sprachfuehrung            :done,    a4d, 2026-05-17, 1d
    Deutsch gefuehrte Plugin-Skills              :done,    a4e, 2026-05-17, 1d
    Notariats-Pilot-Plugin-Readiness             :         a5, after a4, 35d
    Veroeffentlichung und Supportbetrieb         :         a6, after a5, 28d

    section B: Notarielle Workflows
    Workflow-Schichten trennen                   :active,  b1, 2026-05-14, 14d
    KG-Runtime-Status-CLI-MVP                    :done,    b1a, 2026-05-15, 1d
    Projektstimme und Aktivbau-Doku bereinigen   :done,    b1b, 2026-05-15, 1d
    START_HERE-Betriebseinstieg bereinigen       :done,    b1c, 2026-05-15, 1d
    Dokumentationsordner-Taxonomie bereinigen    :done,    b1d, 2026-05-15, 1d
    Regel fuer klickbare Dokumentationslinks     :done,    b1e, 2026-05-15, 1d
    PDF-Export im Aufbau nur manuell             :done,    b1f, 2026-05-15, 1d
    Fertigmeldung nach Main-Merge                :done,    b1g, 2026-05-15, 1d
    Repo-weite deutsch fuehrende Sprachregel     :done,    b1h, 2026-05-15, 1d
    Root-README-Sprachpaar-Links bereinigen      :done,    b1i, 2026-05-15, 1d
    Lokalisierte Doku-Uebersetzung bereinigen    :done,    b1j, 2026-05-15, 1d
    No-code-KG-Editor-Vertrag-MVP                :done,    b1k, 2026-05-15, 1d
    Deutsche Workflow-MD-Sprachfuehrung          :done,    b1l, 2026-05-17, 1d
    Skill-Sprachregel und EN-Summary             :done,    b1m, 2026-05-17, 1d
    Skill- und Python-Workflow-Vertraege         :active,  b2, 2026-05-15, 28d
    Deterministischer Workflow-Runner-MVP        :active,  b3, 2026-05-15, 35d
    Day2-Nachweis- und Driftbetrieb              :         b4, after b3, 28d

    section C: Notarielle Usecases
    GitHub-Usecase-Aufnahme                      :done,    c1, 2026-05-14, 1d
    Top-10 notarielle KG-Basis                   :done,    c2, 2026-05-15, 1d
    Naechste-10 notarielle KG-Basis              :done,    c3, 2026-05-15, 1d
    Usecase-lokale KG-Ordner-Migration           :done,    c3a, 2026-05-15, 1d
    Deutsch fuehrende Usecase-Sprachregel        :done,    c3b, 2026-05-15, 1d
    KG-Editor-Bindung fuer Usecase-KGs           :done,    c3c, 2026-05-15, 1d
    Deutscher KG-Inhalt und Sprachgate           :done,    c3d, 2026-05-17, 1d
    Deutsche Usecase-Vorderseiten                :done,    c3e, 2026-05-17, 1d
    GmbH-Gruendung kanonisieren                  :active,  c4, 2026-05-14, 21d
    Usecase-Katalog bereinigen                 :done,    c5, 2026-05-17, 1d
    Steuer-aaS-Usecase-Aufnahme                  :active,  c6, 2026-05-14, 21d
    Statisches KG-gestuetztes Workflow-Modell    :active,  c7, 2026-05-15, 28d
    Pilotfaehige Usecase-Pakete                  :         c8, after c7, 35d

    section D: Produktkommunikation und Adoption
    Zielgruppenpfade und Owner-Sichtbarkeit      :done,    d1, 2026-05-17, 1d
    Reifegrad Glossar und Beispielpfad           :done,    d1a, 2026-05-17, 1d
    CLI-first Ausfuehrungsmodell erklaeren       :done,    d1b, 2026-05-17, 1d
    Gantt-Regel praezisieren                     :done,    d1c, 2026-05-17, 1d
    Notariats-Startseite weiter schaerfen        :active,  d2, 2026-05-17, 14d
```

## Fortschrittsbild

| Track | Umfang | Status | Fortschritt | Aktuelles Gate |
| --- | --- | --- | --- | --- |
| A | Installierbare Plugins fuer Notariate | Aktiv | 69% | `noc-cyberjack-rfid` erkennt lokal REINER-SCT-DriverPackage, morris-Browser-Middleware und den optionalen morris-Loopback-API-/PCSC-Pfad; `noc-pkcs7-certbundle` fuehrt einen getrennten lokalen Zertifikatsbuendel-Nachweistrack ohne Signatur; OpenAI-gestuetzte Verarbeitung hat einen AVV/DPA-Governance-Abschnitt; die AI-SBOM hat eine repo-weite Basis, Mindestanforderungsinventar, strikten Validator, deutsche Plugin-MD-Fuehrung und deutsch gefuehrte Skill-Anweisungen mit englischer Summary. |
| B | Installierbare Skills und deterministische Python-Workflows | Aktiv | 42% | Das erste ausfuehrbare KG-Runtime-Paket und die CLI sind mit Unit-Tests implementiert; `START_HERE` ist der operative Einstieg getrennt vom README-Ueberblick; Startpruefungen haben Profile fuer Basis-, Plugin-Dev- und Notariats-Workstation-Setups; README-/Index-Referenzen haben klickbare-Link-Validierung; PDF-Export bleibt im aktiven Aufbau manuell; `fertig` bedeutet Merge nach `main` plus sauberer lokaler `main`; Sprachparitaet blockiert kopierte lokalisierte Markdown-/Textspiegel und prueft SKILL.md-Sprachmarker; der KG-Editor stellt sichere No-code-Formular-/Checklisten-Sichten plus Patch-Vertrag bereit; Workflow-MD ist jetzt deutsch gefuehrt. |
| C | Notarielle Usecases fuer Immobilien, Register, Gesellschaften, Vereine, Nachlass, Familie und Vollmachten | Aktiv | 60% | Jeder aktive Usecase besitzt eine usecase-lokale statische KG; Deutsch ist explizit die fuehrende und rechtlich bindende Sprache fuer deutschrechtliche notarielle Usecases; KG-JSON-Reviewtexte, Markdown-Review-Sichten und kurze Usecase-Vorderseiten sind deutsch gefuehrt und durch den Sprachvalidator abgedeckt; ein nicht mehr gewuenschter aktiver Aufnahme-Usecase wurde aus NoC entfernt und ist nicht mehr Teil des Katalogs. |
| D | Produktkommunikation, Adoption und externe Bewertung | Aktiv | 31% | Root-README fuehrt jetzt mit Nutzen, Grenzen, Owner-Sichtbarkeit und vier Zielgruppenpfaden plus Maintainer-Pfad; separate Startseiten erklaeren Notariatsentscheidung, Betrieb, Integration sowie Pruefung und Standardisierung; Reifegrad, Glossar, CLI-first-Ausfuehrungsmodell, praezisierte Gantt-Regel und ein durchgehender Immobilienkaufvertrag-Pfad machen den Stand fuer Nicht-Technik-Leser greifbarer. |

## Regel

Das strikte Quality Gate umfasst `scripts/validate_gantt_progress.py` und setzt
diese Regel technisch durch:

1. Sobald ein Change-Set repo-relevante Dateien aendert, muss
   `roadmap/GANTT.md` Teil desselben Change-Sets sein.
2. Aenderungen unter `plugins/`, `workflows/` oder `usecases/` muessen
   zusaetzlich das jeweilige `GANTT.md` im selben Root mitpflegen.
3. Reine Aenderungen am jeweiligen Themen-Gantt zaehlen bereits als
   Themen-Gantt-Pflege.
4. Generierte Quality-Artefakte unter `out/` und Git-Interna werden ignoriert.
