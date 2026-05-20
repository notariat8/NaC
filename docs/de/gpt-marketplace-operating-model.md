# GPT Marketplace Operating Model

## Zweck

Dieses Dokument trennt die NaC-Plugin-Entwicklung von den möglichen
OpenAI-Vertriebskanaelen. Das Repo nutzt weiterhin den Begriff `plugins/` für
installierbare Artefakte, aber ein Release muss vor Veröffentlichung dem
konkreten OpenAI-Kanal zugeordnet werden.

## Vertriebskanaele

| Kanal | Ziel | Konsequenz für NaC |
| --- | --- | --- |
| Public GPT Store | Öffentlich auffindbarer GPT für Notariate | Nur verwenden, wenn die aktuelle OpenAI-Prüfung, Builder-Profil, Policy-Anforderungen und Datenschutz-URLs erfüllt sind. |
| GPT mit Actions | GPT nutzt externe APIs über Actions | Jede Action braucht gültige Datenschutz-/Nutzungslinks und eine geprüfte Datenverarbeitungsgrenze. |
| Workspace-/Enterprise-App | Interne oder kundenspezifische App-Installation | Nicht als öffentlicher GPT-Store-Release behandeln; als Workspace- oder Enterprise-Pilot führen. |
| Lokales Codex-Plugin | Lokaler Entwicklungs- und Betriebscompanion | Bleibt repo-lokal und ist nicht automatisch ein GPT-Store-Artefakt. |

## OpenAI-Regelabgleich

Vor einem Release muss der aktuelle OpenAI-Stand geprüft werden:

- GPTs können privat, per Link, im Workspace oder im GPT Store geteilt werden.
- Eine öffentliche GPT-Store-Veröffentlichung kann an Plan, Workspace-Policy,
  Builder-Profil und Produkt-/Policy-Prüfung scheitern.
- GPTs mit Apps können nach OpenAI-Hilfeartikeln nicht für den öffentlichen
  GPT Store geeignet sein und sind als Workspace-/Unternehmenspfad zu behandeln.
- GPTs mit Actions benötigen eine gültige Privacy Policy URL.

Aktuelle Quellen:

- [GPTs in ChatGPT](https://help.openai.com/en/articles/8798889-how-can-i-use-gpts)
- [Sharing and publishing GPTs](https://help.openai.com/en/articles/8793007-getting-your-gpt-featured)
- [Building and publishing a GPT](https://help.openai.com/en/articles/8798878-building-and-publishing-a-gpt)

## NaC-Regel

Jedes Plugin unter `plugins/` muss vor Publikation einem Kanal zugeordnet
werden. Die Zuordnung wird in `plugins/GANTT.md` und im jeweiligen Plugin-Plan
nachgeführt. Notariats-Usecases unter `usecases/` dürfen nicht direkt als
Plugin veröffentlicht werden; sie binden Plugins und Workflows zu einem
fachlichen Paket zusammen.
