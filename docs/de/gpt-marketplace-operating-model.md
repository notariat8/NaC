# GPT Marketplace Operating Model

## Zweck

Dieses Dokument trennt die NoC-Plugin-Entwicklung von den moeglichen
OpenAI-Vertriebskanaelen. Das Repo nutzt weiterhin den Begriff `plugins/` fuer
installierbare Artefakte, aber ein Release muss vor Veroeffentlichung dem
konkreten OpenAI-Kanal zugeordnet werden.

## Vertriebskanaele

| Kanal | Ziel | Konsequenz fuer NoC |
| --- | --- | --- |
| Public GPT Store | Oeffentlich auffindbarer GPT fuer Notariate | Nur verwenden, wenn die aktuelle OpenAI-Pruefung, Builder-Profil, Policy-Anforderungen und Datenschutz-URLs erfuellt sind. |
| GPT mit Actions | GPT nutzt externe APIs ueber Actions | Jede Action braucht gueltige Datenschutz-/Nutzungslinks und eine gepruefte Datenverarbeitungsgrenze. |
| Workspace-/Enterprise-App | Interne oder kundenspezifische App-Installation | Nicht als oeffentlicher GPT-Store-Release behandeln; als Workspace- oder Enterprise-Pilot fuehren. |
| Lokales Codex-Plugin | Lokaler Entwicklungs- und Betriebscompanion | Bleibt repo-lokal und ist nicht automatisch ein GPT-Store-Artefakt. |

## OpenAI-Regelabgleich

Vor einem Release muss der aktuelle OpenAI-Stand geprueft werden:

- GPTs koennen privat, per Link, im Workspace oder im GPT Store geteilt werden.
- Eine oeffentliche GPT-Store-Veroeffentlichung kann an Plan, Workspace-Policy,
  Builder-Profil und Produkt-/Policy-Pruefung scheitern.
- GPTs mit Apps koennen nach OpenAI-Hilfeartikeln nicht fuer den oeffentlichen
  GPT Store geeignet sein und sind als Workspace-/Unternehmenspfad zu behandeln.
- GPTs mit Actions benoetigen eine gueltige Privacy Policy URL.

Aktuelle Quellen:

- [GPTs in ChatGPT](https://help.openai.com/en/articles/8798889-how-can-i-use-gpts)
- [Sharing and publishing GPTs](https://help.openai.com/en/articles/8793007-getting-your-gpt-featured)
- [Building and publishing a GPT](https://help.openai.com/en/articles/8798878-building-and-publishing-a-gpt)

## NoC-Regel

Jedes Plugin unter `plugins/` muss vor Publikation einem Kanal zugeordnet
werden. Die Zuordnung wird in `plugins/GANTT.md` und im jeweiligen Plugin-Plan
nachgefuehrt. Notariats-Usecases unter `usecases/` duerfen nicht direkt als
Plugin veroeffentlicht werden; sie binden Plugins und Workflows zu einem
fachlichen Paket zusammen.
