# Ausführungsmodell: Bürooberfläche Vorne, Prüfbarer Kern Dahinter

NaC wird als ausführbare Software für das Notariat entwickelt. Die sichtbare
Bedienung soll für fachliche Nutzer verständlich sein: lokale Bürooberfläche,
Codex-Plugins, Checklisten, Ablaufansichten, BPMN-Bearbeitung und geführte
Prüfungen.

Dahinter liegt eine technische Ausführungsschicht. Sie heißt `nac` und sorgt
davor, dass dieselben Vorgänge lokal, nachvollziehbar, automatisierbar und im
Quality Gate prüfbar bleiben.

## Drei Schichten

| Schicht | Aufgabe | Wer Sie Typisch Nutzt |
| --- | --- | --- |
| Sichtbare Bedienung | Vorgänge auswählen, Abläufe ansehen, Checklisten bearbeiten, lokale Tests starten. | Notar, Sachbearbeitung, Büroorganisation. |
| Technische Ausführung | Dieselben Aktionen als eindeutige, wiederholbare NaC-Aufträge ausführen. | lokale Installation, Codex-Plugin, CI, Maintainer. |
| Governance und Nachweis | Regeln, Validierungen, Review, Lizenz, Audit und Merge nachvollziehbar halten. | Owner, technische Dienstleister, Prüfer, externe Bewertung. |

## Was Bedeutet CLI?

CLI steht für "Command Line Interface", also Kommandozeilen-Schnittstelle. In
NaC ist das nicht als Alltagsoberfläche für Notare gemeint.

Eine CLI ist ein eindeutig benannter Auftrag an die Software. Derselbe Auftrag
kann von einer Schaltfläche, einem Plugin, einer Automation oder direkt im
Terminal gestartet werden. Beispiel:

```bash
python scripts/nac.py status
```

Der fachliche Nutzer soll nicht Befehle auswendig lernen müssen. Der Wert der
CLI liegt darin, dass ein sichtbarer Klick und ein automatisierter Prüflauf am
Ende dieselbe geprüfte NaC-Runtime verwenden.

## Heutiges Produktbild

```mermaid
flowchart TD
    Office["Mensch im Notariat"] --> UI["lokale Bürooberfläche"]
    Office --> Codex["Codex-Plugin oder Chat"]
    UI --> Runtime["NaC-Runtime"]
    Codex --> Runtime
    Admin["Installation, CI oder Maintainer"] --> CLI["nac-CLI"]
    CLI --> Runtime
    Runtime --> BPMN["BPMN-Abläufe"]
    Runtime --> KG["usecase-lokale Wissensgraphen"]
    Runtime --> Plugins["freigegebene lokale Prüfungen"]
    Runtime --> Gate["Quality Gate und Review"]
    Gate --> Git["Git / Pull Request / main"]
```

## Warum Das Elegant Ist

| Grund | Bedeutung |
| --- | --- |
| Verständliche Bedienung | Die Bürooberfläche kann fachlich formulieren, was passiert, ohne technische Details in den Vordergrund zu stellen. |
| Wiederholbare Ausführung | Dieselbe Aktion bleibt lokal, im Plugin und in CI technisch gleich prüfbar. |
| Einfach einzuführen | Python und Git laufen auf vielen Arbeitsplätzen und Servern; eine zentrale Cloud-App ist nicht Voraussetzung. |
| Gut für sensible Daten | NaC kann lokal am Arbeitsplatz laufen; PINs, Kartendaten und Mandatsgeheimnisse gehören nicht in Git. |
| Automatisierbar | GitHub Actions, Codex-Plugins, lokale Schaltflächen und spätere Apps können dieselbe Runtime aufrufen. |
| UI-fähig ohne Lock-in | Die Oberfläche darf wachsen, ohne dass die fachliche Logik in einer einzelnen Maske verschwindet. |
| Auditierbar | Auftrag, Eingabe, Ergebnis, Review und Merge lassen sich versioniert nachvollziehen. |

## Warum Trotzdem Eine Technische Kante?

Eine reine Oberfläche wirkt zunächst einfacher, kann aber die fachliche Logik in
Klickwegen verstecken. NaC muss auch erklären und beweisen können:

1. Welche Vorgangstypen gibt es?
2. Welche offenen Angaben, Dokumente, Entscheidungen und Freigaben sind nötig?
3. Welche Daten dürfen nicht in Git oder externe Dienste?
4. Welche lokalen Prüfungen sind freigegeben?
5. Welche menschliche Freigabe bleibt erforderlich?

Die sichtbare Oberfläche führt durch diese Fragen. `nac` macht die Ausführung
dahinter eindeutig prüfbar.

## Heute, Pilot, Später

| Ebene | Stand | Rolle |
| --- | --- | --- |
| Lokale Operator-Webapp | Heute nutzbar | Startet als Bürooberfläche über `python scripts/nac.py operator --open` und zeigt Vorgänge, Checklisten, BPMN, KG-Ansichten und Arbeitsplatztests. |
| Zentrale `nac`-CLI und Python-Runtime | Heute nutzbar | Prüft KG, BPMN, Konfiguration, Status, Editor-View, Plugins und Quality Gates. |
| Codex-Plugins | Pilotfähig | Führen lokale Readiness-, Plan- und Nachweisprüfungen geführt aus. |
| GitHub Actions | Heute nutzbar | Führen Gates und Validierungen reproduzierbar aus. |
| BPMN-js Business Layer | Erstes Profil vorhanden | Visuelle BPMN-Bearbeitung für fachliche Abläufe; Python prüft das Modell vor Merge. |
| Lokaler Webserver | Heute nutzbar | Zeigt BPMN- und KG-Ansichten lokal im Browser, ohne Cloud und ohne echte Mandatsdaten. |
| Sidecar-Editor | Geplant | Grafische Bedienung für KG-Formulare und Checklisten. |
| ChatGPT-App oder Workspace-App | Geplant | Komfortable Bedienoberfläche für berechtigte Nutzer auf Basis einer geprüften `nac-mcp`-Werkzeugschicht; Custom-GPT-Actions mit Tunnel bleiben ein Demo-Pfad für synthetische Daten. |
| Eigenständige NaC-Web-App | Möglich | Sinnvoll, sobald Runtime, Rollen, Rechte und Gates stabil genug für breitere Nutzung sind. |

## Merksatz

NaC ist keine reine Dokumentation und kein Terminalprodukt. NaC ist eine lokale,
ausführbare Bürosoftware mit sichtbarer Bedienung und einem prüfbaren Kern.

Neue NaC-Funktionalität braucht deshalb zwei Dinge: eine verständliche
Bedienung für den fachlichen Kontext und eine eindeutige Ausführung über `nac`
oder die NaC-Runtime. Alte Skriptnamen können intern oder kompatibel bleiben;
die Produktdokumentation soll den verständlichen NaC-Weg zeigen.

## Nächste Dokumente

- [docs/de/notar-start.md](notar-start.md)
- [docs/de/cli.md](cli.md)
- [docs/de/betriebsstart.md](betriebsstart.md)
- [docs/de/integration-start.md](integration-start.md)
- [docs/de/kg-editor-workstream.md](kg-editor-workstream.md)
- [docs/de/bpmn-js-business-layer.md](bpmn-js-business-layer.md)
- [docs/de/lokaler-webserver.md](lokaler-webserver.md)
- [workflows/python/README.md](../../workflows/python/README.md)
