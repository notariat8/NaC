# Prompt Template: Invoice

Use this structure for the LLM frontend:

```text
Create an invoice request.

Process class: invoice
Customer: <name>
Service date: <yyyy-mm-dd>
Due date: <yyyy-mm-dd>
Currency: EUR
Items:
- <description>, quantity=<value>, unit_price=<value>, account=<account>
Tax rate: <value>
External reference: <crm or ticket id>
Comment: <optional>
```

Expected result:

- a structured JSON file in `processes/invoices/<year>/`
- status `draft`
- a stable `idempotency_key`
