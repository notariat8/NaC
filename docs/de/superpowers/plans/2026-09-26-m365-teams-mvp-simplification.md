# Implementierungsplan: Teams-MVP-Ziel und gestufte Diagnose

Status: Plan zur Review; keine Umsetzung, Veröffentlichung oder Live-Freigabe

Datum: 26. September 2026

Führendes [Issue #620](https://github.com/notariat8/NaC/issues/620). Grundlage ist die freigegebene [DE-Spezifikation](../specs/2026-09-26-m365-teams-mvp-simplification-design.md); die englische Fassung ist der Sprachspiegel. Ausgangsbasis: `1503adf3d9392faad373e793bc5275394daff958`, Tree `f3765329c0cb568b2686d84a6db2bf88daa2d019`. Delivery Mode: Protected PR. Risk Gate: Human Approval.

## Ziel und prüfbare Grenze

Diese Runde vereinfacht die **Entscheidung zur Ursache** des Teams-403 und die dazugehörige Statuskommunikation. Sie repariert den Fehler noch nicht und behauptet keinen Microsoft-Lesezugriff. Der Teams-MVP ist ein synthetischer Test im `notary_team_01`; das öffentliche NaC-Referenzrepo liefert versionierte Muster, aber keine Tenant- oder Berufsfreigabe. Produktiver Notariatsbetrieb braucht seine eigene fachliche, rechtliche und betriebliche Abnahme. Für die Beobachtung vom 25. September gelten nur die zwei lokal geprüften Clientbeleg-Hashes `ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40` und `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`: SPFx-Subject vorhanden, UI `no_access`, Clientantwort 403; Ursprung und konkret betroffene Berechtigung bleiben `UNKNOWN`. Die Belegdateien bleiben repository-extern.

Die ursprünglichen [AC-620-01 bis AC-620-07](../specs/2026-07-13-m365-mvp-test-environment-design.md) und der [#620-Verification-Contract](../../../../workflows/contracts/m365-mvp-test-environment.verification.contract.json) bleiben unverändert maßgeblich. Ein Erfolg der folgenden sechs SIM-Kriterien schließt #620 nicht und ersetzt weder Vertretungs-/Denial-Tests noch den aktuellen zwölfstufigen Live-Abschluss.

## Lesende Bestandskarte (AC-620-SIM-01)

Diese Karte ordnet die Hauptbereiche nach ihrer Bedeutung **für den aktuellen Teams-MVP-Vorfall** ein; `zurückstellen` bedeutet keine Abschaffung des Bereichs.

| Hauptbereich | Zielbeitrag und Abhängigkeit | Entscheidung für diese Runde |
| --- | --- | --- |
| Notarielles Fachmodell, BPMN, Workflows, Usecases und lokale Knowledge Graphs | Definieren den synthetischen Vorgang und seine fachliche Wahrheit; nicht die unbelegte 403-Ursache. | Beibehalten; keine fachliche Änderung. |
| SPFx-Teams-Registerkarte und SharePoint-Site | Zeigen den Vorgang und erzeugten die zwei neutralen Clientbelege. | Beibehalten; nur den dokumentierten Bereitstellungs-/Belegstatus klären. |
| Azure-BFF, Entra-Prüfung und Graph-REST-Projektion | Erzwingen Identität, Zweck, Workspace und redigierte Daten; die 403-Ursprungsgrenze ist offen. | Sicherheitsgrenzen beibehalten; ohne Ursache keinen Code-Fix. |
| Revisionssichere Evidence, Privacy, Governance und Freigaben | Trennen Clientbeobachtung, Providerbeweis und Live-Autorisierung. | Beibehalten; keine Gate-Abschwächung. |
| #748-Read-Driver, historische Request-Log-Triage und #756-Diagnoseeintrag | Alternative Wege zur Ursachenklärung; #756 liegt auf einem getrennten, ungemergten Branch. | Reihenfolge vereinfachen: Telemetrie-Eignung offline prüfen; Read-Driver-Release und #756-Deployment zurückstellen. |
| #739-Provenienz und #632-Live-Aktivierung | Terminaler Altlauf beziehungsweise eigenständiger, schreibender Abschluss. | Unverändert getrennt; keine Quarantänefreigabe oder Aktivierung. |
| Andere Notariatsarbeitsplatz-, Plugin-, Legal-Graph-, On-Prem-AI- und archivierte OCI-Pfade | Für ihre eigenen Ziele relevant, aber kein Nachweis zum aktuellen Teams-403. | In diesem Vorfall zurückstellen; keine Dateiänderung oder globale Qualitätsbehauptung. |

## Exakter Änderungsumfang nach Planfreigabe

1. Die gepaarten DE/EN-[Current-State-Seiten](../../m365-current-state-access-diagnostic.md) erhalten einen **neuen datierten Abschnitt**, statt historische Aussagen umzuschreiben. Er verbindet den Merge von [PR #753](https://github.com/notariat8/NaC/pull/753) und die späteren Clientbelege mit der inzwischen sichtbaren HTTP-Belegfunktion, markiert den 403-Ursprung weiter als unbekannt und lässt die ältere Aussage über den damaligen Nicht-Deployment-Stand als datierte Historie stehen. Kein Providerstatus wird daraus abgeleitet. (AC-620-SIM-02/03/05)
2. [BUILD_NOW](../../../../roadmap/BUILD_NOW.md) bekommt bei `#620` einen knappen Verweis auf diesen aktuellen Diagnoseblocker, ohne den Live-Abschlussstatus, #632-Grenzen oder Meilensteine als erledigt umzubenennen. Falls dies nach der [Gantt-Regel](../../../../AGENTS.md) eine echte Board-/Meilensteinänderung wäre, wird vor einer Gantt-Dateiänderung der zusätzliche genaue Scope geprüft. (AC-620-SIM-05/06)
3. Dieser DE/EN-Plan und die DE/EN-Spezifikation tragen die wechselseitige [Spec-Traceability](../../../../workflows/contracts/spec-traceability.contract.json). In dieser Runde werden **keine** Validatoren, Verträge, Produktmodule, Agentenregeln, SPFx-Assets oder #756-Dateien editiert. Entsteht dafür ein nachgewiesener Bedarf, stoppt die Umsetzung vor dem betreffenden Edit und legt den exakten Zusatzscope vor. (AC-620-SIM-01/03/05)

## Gestufte Offline-Entscheidung

1. **Belege fixieren:** Nur neutrale Felder, Hashes und das geschlossene Beobachtungsfenster vergleichen. `spfx_subject_available=true` schließt allein den fehlenden Client-Subject-Zweig für diese Beobachtung aus. Ein 403 belegt weder Function-Ingress noch einen Python-BFF-Zweig. (AC-620-SIM-02)
2. **Telemetrie-Tauglichkeit lesen:** [Request-Log-Ressourcenvertrag](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json), historische [Triage-Spezifikation](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/de/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md), Ziel-/Query-/Korrelationsnachweise und zulässigen Authentifizierungskanal getrennt erfassen. Auf der Basis steht `projection_proven=false`; der #748-Produktionsport liefert `BLOCKED_NO_REFRESH_CAPABILITY` und der Lizenzkatalog ist `PENDING`. Deshalb ist nur eine lokale Eignungsprüfung geplant. Fehlende Bindung wird als genau benannter Blocker dokumentiert; null Logtreffer ist kein Negativbeweis. (AC-620-SIM-03/04)
3. **Nächste Kante bestimmen:** Sind alle Ziel-, Query-, Korrelations-, Datenschutz-, Kanal- und Owner-Bindungen später tatsächlich belegbar, kann **eine gesondert freizugebende** geschlossene Telemetrie-Triage vorbereitet werden. Eine solche Einzelabfrage ersetzt nie die formale #748-Zwei-Snapshot-Diagnose. Ist sie nicht aussagekräftig, wird der Informationsgewinn des [ungemergten #756-Eintrags](https://github.com/notariat8/NaC/blob/e80c1a6385ecfaddb9d09dfd4e6bf427b184737c/docs/de/superpowers/specs/2026-09-26-m365-bff-403-diagnostic-event-design.md) bewertet; kein automatisches Deployment oder Reproduzieren. (AC-620-SIM-03/04)
4. **Fix und Abnahme erst nach belegter Ursache:** Ein späterer Fix braucht eigenen Scope, Test-first-Prüfung und Freigabe. #620 bleibt bis zum positiven zugeordneten und Vertretungsfall, vollständigen Negativ-/Manipulationsfällen, BPMN-/Aufgaben-/Fristdarstellung, site-spezifischer Auslieferung, Graph-Write/Readback/Cleanup und redigierter UI-/BFF-Evidence offen. Die exakt gebundenen #632-Grenzen bleiben `Matter.Read`, Runtime-`Sites.Selected` und Site-Rolle `read`; fehlende Bindungen dürfen nur im eigenständig genehmigten Live-Lauf exakt angelegt oder identisch wiederverwendet werden, Drift blockiert. (AC-620-SIM-06)

In allen vier Schritten gelangen in Git, Statusseiten und öffentliche Logs ausschließlich redigierte Zustände, Hashes und Blockiercodes. Reale App-, Tenant- und Account-IDs, Rohkorrelationen, Query-/Quellnachweise, personenbezogene Werte und Credential-Inhalte bleiben im geschützten repository-externen Bereich; Credential-Inhalte werden für diese Offline-Planung gar nicht gelesen.

## AC-zu-Nachweis-Matrix

| Kriterium | Geplanter, ohne Providerzugriff prüfbarer Nachweis |
| --- | --- |
| AC-620-SIM-01 | Diese Bestandskarte mit Zielbeitrag, Abhängigkeit und Entscheidung sowie die Trennung von Test-MVP, öffentlichem Referenzrepo und Produktivbetrieb. |
| AC-620-SIM-02 | Datiertes DE/EN-Status-Addendum mit beiden Hashes, `CLIENT_403_ORIGIN_UNKNOWN` und unbekannter konkreter Berechtigung statt einer erfundenen BFF-Ursache. |
| AC-620-SIM-03 | Eine dokumentierte Reihenfolge für #748, historische Telemetrie-Triage und den bedingten #756-Folgeweg. |
| AC-620-SIM-04 | Explizite Stop-Bedingungen für fehlendes Ziel, Query, Korrelation, Datenschutz, Authentifizierung oder Owner-Bindung vor einem realen Read oder neuer Reproduktion. |
| AC-620-SIM-05 | Konsistente DE/EN-Statusseiten und `BUILD_NOW`; einmaliger finaler Strict-Doctor mit ausgewiesenen Vorprüfungen. |
| AC-620-SIM-06 | Verweis auf unveränderte AC-620-01..07 und den noch offenen zwölfstufigen Live-Abschluss, ohne Abschlussbehauptung. |

## Review, Validierung und Stopps

Vor einem späteren Edit wird der rote Prüfpunkt dokumentiert: Die datierten DE/EN-Statusseiten enthalten noch keinen Eintrag zu den zwei gepaarten Clientbelegen und `BUILD_NOW` benennt den konkreten 403-Diagnoseblocker nicht. Nach dem Edit muss ein datierter Abschnitt diese Lücke schließen, ohne die alte historische Aussage umzuschreiben oder den 403 als BFF-Ursache zu behaupten. Dies ist eine manuelle, überprüfbare Dokumentations-Regression; es wird kein neuer Testcode außerhalb des Scopes erfunden.

`plan -> review -> fix` prüft DE/EN-Parität, tatsächliche Diff-Grenze, zeitliche Aussagen, fachlichen #620-AC-Erhalt, Datenschutz und die Trennung von Clientantwort/Function-Ingress/Python-BFF. Die AC-620-SIM-01..06 werden gegen Bestandskarte, datierten Belegstand, Entscheidungsfolge, Stopps, DE/EN-Status und erhaltene #620-ACs einzeln abgehakt; der generische Traceability-Validator erzwingt diese Inhaltszuordnung derzeit nicht. Weil der Linkvalidator diese Plan-/Spec-Dateien nicht selbst scannt, werden ihre relativen Links zusätzlich lokal auf Existenz und Sprachpfad geprüft. Vor nichttrivialer Arbeit läuft `graft build`; gezielte Validatoren dienen als schnelle Vorprüfung. Auf dem finalen lokalen Stand läuft **ein** vollständiger `python scripts/nac.py doctor --profile strict`, der `graft check` und die genannten Einzelvalidatoren bereits enthält. Diese werden nicht als zusätzliche unabhängige Schlussgates gezählt. Ein geschützter PR und Remote-CI sind spätere Delivery-Schritte, keine Wirkung dieser Planfreigabe.

```text
graft build
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python scripts/nac.py doctor --profile strict
git status --short
git diff --check
git diff --check main...HEAD
git diff --name-status main...HEAD
git log --oneline main..HEAD
```

Vor einem späteren PR-Abschluss sind die vollständige Datei- und Commitliste `base...head` gegen den Zielbranch sowie die verpflichtenden Remote-Checks des finalen Heads zu prüfen; nur `HEAD` allein genügt nicht. Stop vor jedem Login, Token-Refresh, Credential- oder Providerzugriff, Deployment, neuem Teams-Request, #739-Freigabe, #632-Live-Lauf, Merge oder einer Änderung außerhalb des oben benannten Scopes. Ein nicht eindeutig beweisbarer 403-Ursprung bleibt `UNKNOWN`; es gibt keinen Retry aus einer blockierten Triage heraus.
