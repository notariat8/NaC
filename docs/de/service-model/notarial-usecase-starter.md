# Notarial Usecase Starter

## Zweck

Dieser Katalog ersetzt das frühere Branchenmodell. Er benennt nur notarielle
Starter-Usecases, die im NaC-Repository fachlich beschrieben sind.

Der kanonische Gesamtstand liegt in [usecases/README.md](../../../usecases/README.md).
Neue Beispiele dürfen nicht frei erfunden werden, sondern müssen als
notarielle Usecases mit KG, README und BPMN-Bezug angelegt oder auf bestehende
Usecases verweisen.

## Einheitliche Statuswerte

- `draft`
- `validated`
- `needs_review`
- `approved`
- `executed`
- `archived`

## Einheitliche Freigabepunkte

- `validated -> needs_review`: bei fachlicher, berufsrechtlicher,
  datenschutzrechtlicher oder technischer Relevanz
- `needs_review -> approved`: fachlicher Review durch zuständige Rolle
- `approved -> executed`: operative Freigabe, ggf. Vier-Augen-Prinzip

## Starterset: Immobilienkaufvertrag

Kanonischer Ordner:
[usecases/immobilienkaufvertrag/](../../../usecases/immobilienkaufvertrag)

Startfragen:

1. Welche Immobilie, Beteiligten und Registerdaten sind betroffen?
2. Welche Kaufpreis-, Finanzierungs- und Fälligkeitslogik gilt?
3. Welche Belastungen, Genehmigungen und Vollzugsgates sind offen?

## Starterset: Unterschriftsbeglaubigung

Kanonischer Ordner:
[usecases/unterschriftsbeglaubigung/](../../../usecases/unterschriftsbeglaubigung)

Startfragen:

1. Wer unterschreibt und wie wird die Identität geprüft?
2. Welches Dokument und welcher Zweck liegen vor?
3. Ist Vertretung, Registerbezug oder besondere Formprüfung betroffen?

## Starterset: Online-GmbH-Gründung

Kanonischer Ordner:
[usecases/online-gmbh-gruendung/](../../../usecases/online-gmbh-gruendung)

Startfragen:

1. Welche Gesellschaftsdaten, Gründer und Kapitalstruktur liegen vor?
2. Welche Geschäftsführerbestellung und Vertretungsregelung gilt?
3. Welche Registerroute, Signatur-Readiness und GwG-Prüfflaggen sind offen?

## Starterset: Handelsregisteranmeldung

Kanonischer Ordner:
[usecases/handelsregisteranmeldung/](../../../usecases/handelsregisteranmeldung)

Startfragen:

1. Welcher Rechtsträger und welcher Anmeldetyp sind betroffen?
2. Welche Beschlüsse, Anlagen und Unterzeichner sind erforderlich?
3. Welche XNP-Route und Einreichungsnachweise sind offen?

## Pilot-Hinweise

- Zuerst einen oder zwei notarielle Usecases produktiv pilotieren.
- Alle Prozessänderungen laufen über Branch, PR und Review, sofern kein
  ausdrücklich freigegebener Owner-Direct-Modus gilt.
- Release-Binding je Vorgangsstart ist verpflichtend.
- Abweichungen werden als Change Request dokumentiert.
