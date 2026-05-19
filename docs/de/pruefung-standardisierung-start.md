# Prüfung Und Standardisierung: Nachvollziehbarkeit Von NaC

Dieses Dokument richtet sich an Stellen und Personen, die NaC aus Sicht von
Kontrolle, Standardisierung, Zertifizierung, Aufsichtnaehe oder fachlicher
Vergleichbarkeit bewerten. Es benennt keine konkrete Institution, sondern den
Prüfpfad im Repository.

## Was Bewertbar Ist

NaC macht nicht nur Prompts sichtbar, sondern auch:

- Rollen und Freigaben,
- technische und fachliche Gates,
- Datenschutz- und Datenklassenregeln,
- SBOM- und AI-SBOM-Bestandteile,
- Plugin-Grenzen und Integrationsannahmen,
- usecase-lokale Knowledge Graphs,
- Tests, Validatoren und Quality Gates.

## Was Nicht Bewertet Werden Sollte

- echte Mandatsdaten, weil sie nicht in dieses öffentliche Repository gehören,
- produktive Arbeitsplatzkonfigurationen einzelner Büros,
- externe Fachsysteminhalte, die nur referenziert werden,
- KI-Ausgaben als finale rechtliche Entscheidung.

## Prüfpfad

1. Sprach- und Rollenregeln lesen.
2. Datenschutz- und Speichergrenzen prüfen.
3. Usecase-KGs gegen fachliche Mindestanforderungen lesen.
4. Plugin-Grenzen und lokale Readiness-Checks prüfen.
5. Quality Gate lokal ausführen.
6. Version, Release, Fork- und Rückflussmodell bewerten.

## Relevante Dateien

- [docs/de/reifegrad.md](reifegrad.md)
- [docs/de/glossar.md](glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md)
- [policies/language-policy.yaml](../../policies/language-policy.yaml)
- [policies/data-protection-policy.yaml](../../policies/data-protection-policy.yaml)
- [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)
- [docs/de/security-and-dsgvo.md](security-and-dsgvo.md)
- [docs/de/sbom-for-ai.md](sbom-for-ai.md)
- [docs/de/quality-gate.md](quality-gate.md)
- [usecases/README.md](../../usecases/README.md)
- [roadmap/GANTT.md](../../roadmap/GANTT.md)

## Lokale Reproduzierbarkeit

```bash
python scripts/nac.py doctor --profile strict
python scripts/validate_language_parity.py
python scripts/validate_knowledge_graph.py
python scripts/nac.py plugins validate
```

## Standardisierungsfrage

NaC ist geeignet, wiederholbare fachliche Muster versioniert zu diskutieren:
Welche Vorgangsknoten sind erforderlich, welche Freigaben sind zwingend, welche
Nachweise dürfen nur referenziert werden, und welche Automatisierung bleibt
bewusst gesperrt?
