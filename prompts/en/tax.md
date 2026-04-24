# Prompt Template: Tax Case

```text
Create a tax process.

Process class: tax
Tax type: <vat_return|annual_return|payroll_tax|trade_tax>
Period: <yyyy-mm or yyyy>
Input sources:
- <source>
Approval required: <yes|no>
External reference: <case-id>
Comment: <optional>
```

Expected result:

- a JSON file in `processes/tax/<year>/`
- status `draft` or `prepared`
- documented sources for later review
