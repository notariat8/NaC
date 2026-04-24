# Prompt Template: Company Formation

```text
Create a company formation process.

Process class: formation
Venture: <company or project name>
Legal form: <gmbh|ug|sole proprietorship|...>
Registered seat: <city>
Formation steps:
- <step>
- <step>
Deadlines:
- <date>: <event>
Responsible parties:
- <role>: <name or team>
Comment: <optional>
```

Expected result:

- a JSON file in `processes/formation/<year>/`
- status `draft`
- a checklist with explicit responsibilities
