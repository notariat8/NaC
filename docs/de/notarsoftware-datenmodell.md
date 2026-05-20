# Notarsoftware-Datenmodell für NaC

Status: Arbeitsmodell für Demo-Akten und spätere Datenrepo-Adapter

Diese Seite übersetzt beobachtbare Muster aus moderner Notariatssoftware in
das NaC-Datenmodell. Sie ersetzt keine Produktanalyse einzelner Anbieter und
kopiert keine proprietären Abläufe. Ziel ist ein eigener, offener
Modellvertrag, den Notare, Mitarbeitende, ISV und Prüfer verstehen können.

## Quellenbild

Die öffentlich sichtbaren Produktinformationen zeigen wiederkehrende
Bausteine:

| Quelle | Relevanter Hinweis für NaC |
| --- | --- |
| [NOAH Funktionen](https://noah-notariatssoftware.de/funktionen/) | Kontakte, Grundstücke, Zuständigkeiten, Vorgangsdaten, Word-Entwurf, Dokumentenmanagement, Posteingang, Status, Vollzug, Kostenrechnung und elektronische Schnittstellen gehören zusammen. |
| [LawX Produkt](https://www.lawx.de/product) und [LawX Übersicht](https://www.lawx.de/impulse/notarsoftware) | Der Vorgang ist das Zentrum; Eingangsdaten, Registerinformationen, Entwurf, Vollzug, Fristen und Abrechnung werden vorbereitet, der Mensch gibt frei. |
| [TriNotar](https://www.wolterskluwer.com/de-de/solutions/trinotar) und [TriNotar entdecken](https://www.wolterskluwer.com/de-de/solutions/trinotar/trinotar-entdecken) | E-Akte, digitale Nebenakte, Dokumentversionen, Posteingang, To-dos, OCR, Workflowunterstützung und Export-/Viewer-Pfade sind Kernanforderungen. |
| [CVC NOTRE Funktionsumfang](https://cvcit.de/it-funktionsumfang/) und [CVC Flyer](https://cvcit.de/wp-content/uploads/2025/03/Flyer.pdf) | Elektronische Akte, Dokumentversionen, Signieren, Scanner, Ausweisscanner, XNP-/UVZ-/Register-/DATEV-/Outlook-Pfade und Kostenregister müssen als Schnittstellen- und Nachweisebene modellierbar sein. |
| [§ 43 NotAktVV](https://www.gesetze-im-internet.de/notaktvv/__43.html) | Elektronische Nebenakten brauchen einen strukturierten Datensatz und müssen in ein vorgeschriebenes Dokumentformat überführbar sein. |

## Schlussfolgerung

NaC darf eine Akte nicht als flachen Ordner behandeln. Das offene Datenmodell
muss mindestens diese Schichten kennen:

| Schicht | NaC-Datei oder Pointer | Warum |
| --- | --- | --- |
| Aktenkern | `akten/<jahr>/<akten_id>/akte.json` | Aktenzeichen, Status, Usecase, Workflowbindung, Beteiligten- und Dokument-IDs. |
| Kontakte und Beteiligte | `personen/<person_id>.json`, `beteiligte.json` | Personen, Organisationen, Rollen, Vertreter und Dublettenprüfung bleiben getrennt vom Vorgang. |
| Grundstück/Register | `grundbuch.json` oder spätere Registerdateien | Registerdaten sind eigene fachliche Objekte, nicht nur PDF-Anhänge. |
| Eingang/Post | `eingang.json` | Scan, E-Mail, Fax, Portal oder Prompt-Vorschlag werden nachvollziehbar zugeordnet. |
| Dokumente und Versionen | `dokumente/<document_id>/metadata.json` plus Dateien | Originale, Vorschauen, Entwürfe, Versionen und Metadaten bleiben diffbar und exportierbar. |
| Aufgaben und Fristen | `aufgaben.json` | Posteingang und Vollzug brauchen Zuständigkeit, Status, nächste Aufgabe und Fristlogik. |
| Kosten | `kosten.json` | Kostenansätze, Kostenschuldner und Abrechnungsstatus gehören an die Akte. |
| Nachweise und Compliance | `nachweise.json` | GwG, Identität, Signatur, Register, Nebenakten-Export und QMS-Nachweise sind prüfbare Objekte. |
| Journal | `ereignisse.jsonl`, `journal/` | Jede Änderung bleibt chronologisch nachvollziehbar. |

## CLI Als Prüfbarer Kern

Die Webapp darf die Büroarbeit bequem machen. Der prüfbare Kern bleibt die
CLI:

```bash
nac tenant write-sample-akte --repo ../demo8notariat --akten-id UVZ-2026-0001
nac tenant list-akten --repo ../demo8notariat
nac tenant show-akte --repo ../demo8notariat --akten-id UVZ-2026-0001
```

Damit kann ein Notar oder Prüfer auch ohne Webapp sehen:

- welche Akten existieren,
- welcher nächste Schritt offen ist,
- welche Beteiligten, Dokumente, Aufgaben und Nachweise zur Akte gehören,
- ob die elektronische Nebenakte als Exportmodell vorbereitet ist.

## Grenze

Das aktuelle GitHub-Datenrepo bleibt ein Demo-Ziel. Produktive Daten brauchen
einen geprüften Sovereign-/DSGVO-Git-Anbieter oder eine gleichwertige lokale
Git-Infrastruktur. Das Modell soll beim Umzug gleich bleiben; nur Remote,
Berechtigungen, Verschlüsselung, Retention und Betrieb ändern sich.
