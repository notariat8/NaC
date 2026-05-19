# Usecase-Gantt

Letzte Aktualisierung: 2026-05-19

```mermaid
gantt
    title Notarieller Usecase-Lieferplan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section Aufnahme
    GitHub-Repository-Scan                     :done,   u1, 2026-05-14, 1d
    Kanonischen Usecase-Root anlegen           :done,   u2, 2026-05-14, 1d

    section Prioritäts-Usecases
    Top-10 notarielle Usecase-Basis            :done,   u3, 2026-05-15, 1d
    Statische KG-Bindung für Top-10-Fälle    :done,   u4, 2026-05-15, 1d
    Nächste-10 notarielle Usecase-Basis       :done,   u5, 2026-05-15, 1d
    Statische KG-Bindung für nächste Fälle  :done,   u6, 2026-05-15, 1d
    Usecase-lokale KG-Ordner-Migration         :done,   u6a, 2026-05-15, 1d
    Deutsch führende Usecase-Indexregel       :done,   u6b, 2026-05-15, 1d
    No-code-KG-Editor-Bindung                  :done,   u6c, 2026-05-15, 1d
    Deutsch geführtes KG-Inhaltsgate          :done,   u6d, 2026-05-17, 1d
    Deutsche fachliche Usecase-Vorderseiten     :done,   u6e, 2026-05-17, 1d
    Deutsche Umlautpflicht für Usecases       :done,   u6f, 2026-05-18, 1d
    Usecase-BPMN-Basismodelle                  :done,   u6g, 2026-05-19, 1d
    Online-GmbH-Gründung                      :active, u7, 2026-05-14, 28d
    Aktive Aufnahme bereinigt                  :done,   u8, 2026-05-17, 1d
    Steuer-aaS-Steuer-Readiness                :active, u9, 2026-05-14, 28d
    Immobilienkaufvertrag und Grundschuld      :active, u10, 2026-05-15, 28d
    Register-, Vereins- und Gesellschaftsfälle :active, u11, 2026-05-15, 35d
    Familien-, Nachlass- und Vollmachtsfälle  :active, u12, 2026-05-15, 35d

    section Pilot-Readiness
    Usecases an Plugin-Abhängigkeiten binden  :        u13, 2026-06-15, 28d
    Usecases an Workflow-Verträge binden      :        u14, after u13, 28d
    KG-gestützte Workflow-Statusupdates       :        u15, after u14, 28d
    Pilotpaket-Review                          :        u16, after u15, 21d
```

## Status

| Usecase | Ordner | Status | Quelle |
| --- | --- | --- | --- |
| Top-10 notarielle Usecase-Basis | `usecases/*/knowledge-graph.graph.json` | Fertig | Kanonische Usecase-Ordner und usecase-lokale KG-Knoten für die zehn wichtigsten notariellen Falltypen angelegt. |
| Nächste-10 notarielle Usecase-Basis | `usecases/*/knowledge-graph.graph.json` | Fertig | Kanonische Usecase-Ordner und usecase-lokale KG-Knoten für die nächsten zehn häufigen notariellen Falltypen angelegt. |
| Deutsch führende Usecase-Sprache | `usecases/README.md` | Fertig | Deutsch ist jetzt explizit als führende und rechtlich bindende Sprache für deutschrechtliche notarielle Usecases festgelegt. |
| No-code-KG-Editor-Bindung | `usecases/README.md` plus `src/notary_kg/editor.py` | Fertig | Fachpersonal bearbeitet Usecase-KGs über eine Formular-/Checklisten-Editor-View; rohes JSON und `value`-Felder bleiben gesperrt. |
| Deutsch geführtes KG-Inhaltsgate | `usecases/*/knowledge-graph.*` plus `scripts/validate_language_parity.py` | Fertig | KG-Markdown-Review-Sichten und fachliche JSON-Textfelder sind deutsch geführt; alte englische KG-Gerüsttexte werden vom Sprachvalidator abgelehnt. |
| Deutsche fachliche Usecase-Vorderseiten | `usecases/*/README.md` plus `scripts/validate_language_parity.py` | Fertig | Jeder Usecase hat eine kurze deutsche Vorderseite für Nicht-Technik-Leser; alte englische Usecase-README-Gerüsttexte werden vom Sprachvalidator abgelehnt. |
| Usecase-BPMN-Basismodelle | `bpmn/immobilienkaufvertrag.bpmn`, `bpmn/usecases/*.bpmn` plus `scripts/generate_usecase_bpmn.py` | Fertig | Alle usecase-lokalen KGs haben ein bpmn-js-taugliches BPMN-2.0-Basismodell mit Rolle, Ausführungskanal, Freigabe, Nachweis und KG-Referenz. |
| Online-GmbH-/UG-Gründung | `usecases/online-gmbh-gruendung/` | Aktiv | Aus dem leeren GitHub-Repo `ofunk/Online-GmbH-Gruendung` kanonisiert; jetzt Teil der Top-10-KG. |
| Bereinigte aktive Aufnahme | `usecases/` | Fertig | Ein nicht mehr gewünschter aktiver Aufnahme-Usecase wurde aus diesem Repository entfernt und ist nicht mehr Teil des NaC-Usecase-Katalogs. |
| Steuer-aaS-Steuer-Readiness | `usecases/steuer-aas/` | Aktiv | Aus dem leeren GitHub-Repo `ofunk/Steuer-aaS` kanonisiert. |
| Immobilienkaufvertrag | `usecases/immobilienkaufvertrag/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Grundschuld / Hypothekenbestellung | `usecases/grundschuld-hypothekenbestellung/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Handelsregisteranmeldung | `usecases/handelsregisteranmeldung/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Beglaubigung von Unterschriften | `usecases/unterschriftsbeglaubigung/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Testament / Erbvertrag | `usecases/testament-erbvertrag/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Erbscheinsantrag / Nachlass | `usecases/erbscheinsantrag-nachlass/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Vorsorgevollmacht und Patientenverfügung | `usecases/vorsorgevollmacht-patientenverfuegung/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Schenkungsvertrag / Übertragungsvertrag | `usecases/schenkungsvertrag-uebertragungsvertrag/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Ehevertrag / Scheidungsfolgenvereinbarung | `usecases/ehevertrag-scheidungsfolgenvereinbarung/` | KG-Basis | Neuer kanonischer Top-10-Usecase in diesem Repository. |
| Löschungsbewilligung / Grundbuchlöschung | `usecases/loeschungsbewilligung-grundbuchloeschung/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Teilungserklärung nach WEG | `usecases/teilungserklaerung-weg/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Bauträgervertrag | `usecases/bautraegervertrag/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Gesellschafterbeschluss GmbH/UG | `usecases/gesellschafterbeschluss-gmbh-ug/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Geschäftsanteilsübertragung GmbH | `usecases/geschaeftsanteilsuebertragung-gmbh/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Vereinsregisteranmeldung | `usecases/vereinsregisteranmeldung/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Erbausschlagung | `usecases/erbausschlagung/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Pflichtteilsverzicht / Erbverzicht | `usecases/pflichtteilsverzicht-erbverzicht/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Adoption / familienrechtliche Erklärungen | `usecases/adoption-familienrechtliche-erklaerungen/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |
| Vollmacht für Immobilien- oder Gesellschaftsgeschäfte | `usecases/vollmacht-immobilien-gesellschaftsgeschaefte/` | KG-Basis | Neuer kanonischer Nächste-10-Usecase in diesem Repository. |

## Plugin-klassifizierte Quellen

| Quelle | Entscheidung |
| --- | --- |
| `ofunk/IDaaS` | Als `plugins/nac-idaas/` migriert, nicht als Usecase. |

## KG-Regel

Jeder Usecase besitzt seine KG unter
`usecases/<slug>/knowledge-graph.graph.json` plus
`usecases/<slug>/knowledge-graph.md`. Das strikte Quality Gate lehnt einen
zentralen `knowledge-graph/`-Ordner und jeden Usecase-Ordner ohne lokale KG ab.
Jede KG-Änderung muss alle fallbezogenen `value`-Felder in Git leer halten und
bei Push diesen Gantt plus den globalen Gantt aktualisieren. Fachpersonalnahe
Änderungen laufen über die KG-Editor-View und den Patch-Workflow; direkte
Roh-JSON-Bearbeitung bleibt geprüfter Entwicklerwartung vorbehalten.
