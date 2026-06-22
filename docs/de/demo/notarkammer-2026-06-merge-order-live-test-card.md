# Notarkammer-Demo 2026-06: Merge-Reihenfolge und Live-Test-Karte

Stand: 2026-06-22

Diese Karte bündelt die letzten Demo-Artefakte in eine vorführbare Reihenfolge.
Sie ist kein Release- oder Apply-Auftrag. Sie sagt nur, welche geprüften
Änderungsvorschläge zuerst landen sollten und wie danach der Live-Test sicher
geführt wird.

## Merge-Reihenfolge

1. **www-n8 Prozessmodell und öffentlicher XNP/SNP-Einstieg:** zuerst die
   öffentlichen Seiten mergen, damit Notarkammer, Immobilienkaufvertrag,
   Prozessmodell, XNP/SNP, XNotar, Vollzug und ISV-Fragen sichtbar sind.
2. **NaC Demo-Basis:** danach NaC-Runbooks für Venv, XNP/SNP-Fragen,
   1-Seiten-Talktrack und Smoke-Entscheidung mergen.
3. **NaC Diagnose und Evidence:** zuletzt Login-Diagnose und
   Evidence-Matrix mergen, damit der Live-Test klare Stop-Lines und
   Nachweise hat.

## Live-Test nach dem Merge

1. `https://notariat8.de` öffnen und die öffentliche Einstiegssicht zeigen.
2. `https://notariat8.de/prozessmodell.html?vorgang=immobilienkaufvertrag`
   öffnen und Immobilienkaufvertrag, Dauer, Parallelität, kritischen Pfad,
   XNP/SNP, XNotar, Kartenleser, Register, Grundbuch und Vollzug erklären.
3. `https://app.notariat8.de/healthz` nur als kurzen technischen Vorcheck
   öffnen.
4. `https://app.notariat8.de/login` nur mit freigegebenem Testnutzer starten.
5. `https://app.notariat8.de/workspace` als fail-closed- oder metadata-only
   Grenze zeigen, wenn Sitzung oder Rolle nicht grün sind.

## Sichere Demo-Entscheidung

- **Go:** Prozessmodell lädt, App-Health ist kurz und nicht-sensitiv, Login ist
  entweder grün oder sauber fail-closed, Workspace bleibt ohne gültige Sitzung
  geschlossen.
- **Warn-Go:** Login-Diagnose bleibt gelb oder rot, aber Prozessmodell,
  XNP/SNP-Grenzen und Evidence-Matrix sind erklärbar.
- **No-Go:** Nutzerflächen zeigen interne Anbieterwerte, Tokens, Claims,
  Callback-Werte, Secrets oder Mandatsdaten.

## Stop-Lines

- Keine produktive XNP-Aktion.
- Keine produktive XNotar-, Register- oder Grundbuchhandlung.
- Keine Mandatsdaten.
- Keine Secrets.
- Keine Live-Reparatur.
- Kein JSON-Endpunkt als Benutzeroberfläche.

## Demo-Aussage

NaC zeigt den Immobilienkaufvertrag als prüfbaren XNP/SNP-zentrierten
Workflow. Die Demo fragt gezielt nach Testzugang, ISV-Rolle, Evidence-Feldern,
Status-Callbacks und Zertifizierungsschritten. Sie behauptet keinen
produktiven Zugriff.
