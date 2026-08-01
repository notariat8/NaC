# Generische NaC Workbench

## Entscheidung

Die generische Arbeitsoberfläche bleibt zunächst im Repository `notariat8/NaC`.
Sie wird nicht als getrenntes Produkt entwickelt und später wieder
zusammengeführt. Getrennte Quellgrenzen ermöglichen eine spätere Extraktion,
ohne heute zwei Release-, Governance- und Sicherheitsmodelle zu erzeugen.

```text
workbench/core   -> Verträge, Runtime-Parser, Selektoren
workbench/nac    -> NaC-BFF-Scope- und Producer-Bindung
workbench/react  -> host-unabhängige React-Ansicht
SPFx/Teams       -> Authentisierung, Transport und Host
NaC BFF          -> Rollen, Vertretung, Wahrheit, Redaktion und Lease
```

Der Kern importiert keine SPFx-, React-, Graph-, MCP-, BPMN- oder NaC-
Runtime-Abhängigkeit. Der React-Layer importiert nur den Kern. Der NaC-Adapter
akzeptiert ausschließlich den versionierten, redigierten BFF-Snapshot.

## Autoritätsgrenze

Aufgaben, Aufmerksamkeit, Entscheidungen, Nachweise und Capabilities werden
serverseitig projiziert. Der Browser leitet keine Entscheidung aus
`requiresApproval`, keine Dringlichkeit aus einer Frist und keine
Nachweisautorität aus BPMN ab. BPMN ist lediglich eine hashgebundene,
nicht-autoritative Modellreferenz.

Alle mutierenden Capabilities sind im Foundation-Slice `deny`. Ein späterer
Aktionspfad benötigt eine neue BFF-Autorisierung mit Akte, Zweck, Akteur,
Rolle, Decision-Version, Ablauf, Step-up/Vier-Augen-Regel, Idempotenz,
Correlation-ID und Readback. Der Snapshot enthält weder URL noch Callback oder
Executor.

Vor Ausgabe muss ein Redaktions-Port den kanonischen Inhalt mit Policy-,
Classifier-, Zeit- und SHA-256-Bindung als `verified` attestieren. Der BFF
prüft diese Bindung und verwirft Snapshots bei fehlender, abweichender oder
veralteter Attestierung. `sourceRef` und `sourceSystem` sind ausschließlich
opake technische Identifier; URLs, E-Mail-Adressen und bekannte
Token-/Secret-Formen werden an der Projektionsgrenze abgelehnt. Die
Attestierung ersetzt keine fachliche Datenminimierung, sondern macht deren
serverseitige Prüfung zur technischen Vorbedingung.

## Sichtbarkeit und Frische

`Heute` zeigt nur Aufmerksamkeit innerhalb der aktuell geöffneten, bereits
autorisierten Akte. Eine spätere aktenübergreifende Tagesansicht muss der BFF
serverseitig und zugriffsgefiltert aggregieren. Browserfilterung über mehrere
Akten ist ausgeschlossen.

Ein Snapshot und seine Access Decision sind maximal fünf Minuten gültig. Jede
Access Decision ist exakt an Akteur, Rolle, Workspace, Akte und Zweck gebunden.
Vertretungszugriff benötigt zusätzlich Decision-ID, Decision-Version, Grund,
Ausstellungszeit und Ablauf. Der wirksame Ablauf ist das Minimum aus
Projektions-Lease und Vertretungsende. Eine abweichende Bindung, `deny`,
ungültige Referenzen oder ein abgelaufener Snapshot liefern keine Datenansicht.
Der Python-Producer erzeugt kompaktes JSON in definierter Einfügereihenfolge.
Python-Producer und TypeScript-Consumer begrenzen exakt diese UTF-8-Wire-Bytes
identisch auf 128 KiB. Textgrenzen zählen in beiden Runtimes höchstens 256
UTF-16-Codeeinheiten; tokenartige Werte sind in allen externen IDs und
Anzeigetexten unzulässig.

## Repository- und Hostgrenze

SPFx/Teams ist der erste kompilierte Hostkandidat in der Microsoft-365-
Umgebung. Der Foundation-Slice wird im SPFx-Paket gebaut und getestet, ist aber
noch nicht in das produktive Webpart importiert. Deshalb verändert er weder
das ausgelieferte Webpart noch dessen Laufzeitdatenpfad. Die Live-Bindung folgt
erst, wenn der BFF den Snapshot-Vertrag `nac.workbench.snapshot/v1` ausliefert
und der Host die kurze Lease auch im laufenden Betrieb erneuert.
Die CI übergibt die kompilierten Workbench-Artefakte aus dem SPFx-Build an den
Strict-Gate-Job; dort werden sie byteweise gegen den visuellen Nachweis geprüft.

Office-Add-in und lokale On-prem-Shell sind spätere Hosts desselben Vertrags.
Eine Repo-Extraktion wird erst geprüft, wenn ein zweiter unabhängig
veröffentlichter Consumer existiert und der Vertrag stabil versioniert ist.

Vertrag: [generic-workbench.contract.json](../../../workflows/contracts/generic-workbench.contract.json)

Verification Contract: [generic-workbench.verification.json](../../../workflows/verification-contracts/generic-workbench.verification.json)
