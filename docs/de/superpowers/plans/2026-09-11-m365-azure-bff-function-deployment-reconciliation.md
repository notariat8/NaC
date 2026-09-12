# Plan - Azure-BFF Schritt-7-Reconciliation

Status: `IMPLEMENTED_OFFLINE`

Datum: 11. September 2026
Spec: [Design](../specs/2026-09-11-m365-azure-bff-function-deployment-reconciliation-design.md)
Führendes Issue: [#739](https://github.com/notariat8/NaC/issues/739)
Delivery Mode: Owner Direct
Risk Gate: Human Approval

## Umsetzung

1. Exakte ARM-GET-Allowlist und redigierte `FUNCTION_DEPLOYMENT_NOT_APPLIED`-Projektion ergänzen.
2. Terminalen Schritt-7-State, Ledger, Evidence und Prepared-Artefakte bytegenau prüfen.
3. Owner-freie Doppel-Inspection und hashgebundenen #739-Kommentar erzeugen.
4. Owner-verifiziertes, crash-sicheres append-only Release der drei Lock-Journale implementieren.
5. Zentralen CLI-Befehl, Domain-/Verification-Verträge und DE/EN-Dokumentation ergänzen.
6. Negative Tests, Vertragsvalidatoren, volle Suite und Strict Doctor ausführen.
7. Commit und Push durchführen; danach read-only Live-Inspection, exakte #739-Freigabe und kontrolliertes Release ausführen.

## Guardrails

Der Fix schreibt nicht nach Azure, startet keinen Login und verlangt keine
erneute Key-Eingabe. Der anschließende neue Live-Lauf bleibt ein eigener
Owner-Gate-Schritt und verwendet die external-only Sandbox.
