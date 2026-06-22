# Notarkammer-Demo: Immobilienkaufvertrag mit XNP/SNP und Vollzug

Stand: 2026-06-22

Diese Ablaufkarte macht den Immobilienkaufvertrag zum primären
Notarkammer-Demo-Fluss. Sie verbindet BPMN, XNP/SNP-Testzugang,
XNotar-/beN-Übergaben, Kartenleser, Grundbuch und Vollzug so, dass die
Vorführung fachlich konkret wird, ohne produktive XNP-Handlung, ohne
Mandatsdaten und ohne produktive Grundbuch- oder Registereinreichung.

Quellenbasis bleibt die
[XNP-Quellenmatrix](notarkammer-xnp-quellenmatrix.md). Diese Karte formuliert
daraus einen Demo- und Gesprächspfad: Was kann NaC heute sichtbar machen, und
welche XNP/SNP-Testzugänge oder API-Grenzen müssen BNotK oder Notarkammer für
einen ISV-Pilot klären?

## Demo-Ziel

Der Termin soll zeigen:

- NaC versteht den Immobilienkaufvertrag als notariellen Gesamtprozess, nicht
  als lineare Klickstrecke.
- XNP, XNotar, beN, Kartenleser, Grundbuch und Vollzug erscheinen wiederholt
  als fachliche Gates im BPMN-Modell.
- Dauerbänder, `parallelGroup` und `criticalPath` machen sichtbar, welche
  Arbeiten parallel laufen können und welcher Rücklauf als kritischer Pfad
  bestimmt.
- XNP/SNP-Testzugang ist die zentrale ISV-Frage: Welche Status-, Evidence-,
  Callback- oder Testdatenflächen dürfen später offiziell genutzt werden?

## Primärer BPMN-Fluss

| Phase | BPMN-Gate | Externe Grenze | Dauerband | Parallelität | Kritischer Pfad | ISV-Frage |
| --- | --- | --- | --- | --- | --- | --- |
| Aufnahme | Vorgang und Beteiligtenrollen synthetisch anlegen | Keine Fachsystemgrenze | `same_day_or_internal` | - | nein | Welche minimalen Rollen- und Vorgangsmetadaten darf ein ISV ohne Mandatsdaten modellieren? |
| Vorprüfung | Grundbuchstand und Unterlagen fachlich prüfen | Grundbuch als externer Zugriffspunkt | `standard_external` | `pre_notarization_due_diligence` | ja | Gibt es in einer Testumgebung redigierte Grundbuch-/Statusobjekte oder nur manuelle Evidence? |
| Lokale Bereitschaft | XNP, XNotar, Kartenleser und Signaturpfad prüfen | XNP/XNotar/Kartenleser lokal | `same_day_or_internal` | `pre_notarization_due_diligence` | nein | Darf ein lokaler Companion Readiness prüfen, ohne PINs, Tokens, Kartenwerte oder Dokumentinhalte zu lesen? |
| Entwurf | Urkundenentwurf, Vollzugshinweise und Finanzierungsbezug abstimmen | XNP/SNP-Testzugang als offene Grenze | `short_party_turnaround` | `pre_notarization_due_diligence` | ja | Welche XNP/SNP-Testdaten sind für Entwurfsstatus, Beteiligtenstatus und Nachweisstatus zulässig? |
| Beurkundung | Notarielle Freigabe, Signatur- und beN-Kontext bestätigen | Kartenleser, Signatur, beN | `same_day_or_internal` | - | ja | Welche Evidence-Felder darf NaC speichern: Zeit, Rolle, Hash, Status, Freigabe, Fehlklasse? |
| Auflassungsvormerkung | Grundbuchantrag über XNotar/beN vorbereiten | XNotar und Grundbuch | `standard_external` | `post_notarization_completion` | ja | Gibt es Status-Callback oder nur manuell bestätigten Versand-/Rücklaufstatus? |
| Vorkaufsrecht | Gemeinde-/Behördenrücklauf überwachen | Gemeinde/Behörde | `standard_external` | `post_notarization_completion` | ja | Welche Frist- und Rücklaufstatus dürfen in NaC als Evidence-Feld geführt werden? |
| Unbedenklichkeitsbescheinigung | Steuerlichen Rücklauf überwachen | Finanzverwaltung/Steuer | `extended_external` | `post_notarization_completion` | ja | Gibt es testbare Statusobjekte oder bleibt dies eine manuelle notarielle Nachweiskette? |
| Löschungsunterlagen | Gläubiger- und Löschungsunterlagen nachhalten | Banken/Gläubiger/Grundbuch | `standard_external` | `post_notarization_completion` | ja | Welche Nachweisform ist zulässig, ohne Dokumentinhalte oder Bankdaten zu speichern? |
| Kaufpreisfälligkeit | Fälligkeitsmitteilung erst nach Gates freigeben | Notariatliche Entscheidung | `short_party_turnaround` | `ownership_transfer` | ja | Welche Gate-Kombination ist für einen ISV prüfbar, bevor ein Status "fälligkeitsreif" angezeigt wird? |
| Eigentumsumschreibung | Eigentumsumschreibung vorbereiten und Rücklauf überwachen | XNotar, beN, Grundbuch | `extended_external` | `ownership_transfer` | ja | Welche XNP/SNP-Testumgebung bildet transfer of title, Status-Callback und Rücklaufklassen ab? |
| Abschluss | Nachweise, Fristen und Auditstatus schließen | Keine produktive Fachsystemaktion | `same_day_or_internal` | - | nein | Welche Audit-Metadaten erwartet BNotK/Notarkammer für einen Pilotbetrieb? |

## Kritischer Pfad in der Demo

Der kritische Pfad ist nicht die Bedienzeit in NaC. In der Demo ist er der
letzte fachlich notwendige externe Rücklauf, der den Vollzug blockiert. Beim
Immobilienkaufvertrag kann das insbesondere sein:

- Auflassungsvormerkung oder sonstiger Grundbuchrücklauf,
- Vorkaufsrecht oder gemeindlicher Rücklauf,
- Unbedenklichkeitsbescheinigung,
- Löschungsunterlagen,
- Kaufpreis- und Finanzierungsfreigabe,
- Eigentumsumschreibung.

Für die Vorführung wird das Modellfenster `2-8 Wochen` als erzählerische
Planungsgröße genutzt. Das ist keine SLA-Aussage und keine Rechtsberatung.

## Was auf der Demo sichtbar sein darf

- Prozessphase, Gate-Name, Dauerband, `parallelGroup`, `criticalPath`.
- Redigierte Evidence-Klasse: vorhanden, fehlt, blockiert, manuell geprüft.
- XNP, XNotar, beN, Kartenleser und Grundbuch als externe oder lokale Grenzen.
- ISV-Frage je Gate: Testumgebung, Status-Callback, Evidence-Feld, Freigabe.

## Was nicht sichtbar sein darf

- keine Mandatsdaten,
- keine produktive XNP-Handlung,
- keine produktive XNotar- oder beN-Einreichung,
- keine Grundbuch-, Register-, Grundstücks-, Steuer-, Bank- oder
  Personendaten,
- keine PINs, Tokens, Kartenwerte, Zugangsdaten oder Anbieterbetriebsdetails.

## Gesprächsfrage an BNotK/Notarkammer

> Wir können den Immobilienkaufvertrag als BPMN-, Evidence- und
> Vollzugspfad zeigen. Für einen echten ISV-Pilot brauchen wir den
> freigegebenen XNP/SNP-Testzugang: Welche Testumgebung, API-Flächen,
> Status-Callbacks, Evidence-Felder, Rollen und Zertifizierungsanforderungen
> sind für diesen Vollzugspfad vorgesehen?
