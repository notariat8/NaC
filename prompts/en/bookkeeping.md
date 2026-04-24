# Prompt Template: Bookkeeping

```text
Create a bookkeeping request.

Process class: bookkeeping
Document type: <invoice|payment|receipt>
Document date: <yyyy-mm-dd>
Debit account: <account>
Credit account: <account>
Amount: <value>
Currency: EUR
Tax key: <optional>
Document reference: <document-id>
External reference: <bank|shop|erp id>
Comment: <optional>
```

Expected result:

- a JSON file in `processes/bookkeeping/<year>/`
- status `draft`
- an `idempotency_key` that prevents duplicate postings
