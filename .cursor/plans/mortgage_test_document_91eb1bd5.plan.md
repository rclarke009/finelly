---
name: Mortgage test document
overview: Add a fake mortgage statement test file tuned to trigger obligation auto-track, plus quick steps to ingest it and verify it appears under obligations.
todos:
  - id: create-txt
    content: Add to-ingest-test-docs/sample-mortgage-statement.txt with obligation-friendly wording and July 1, 2026 due date
    status: completed
  - id: manual-verify
    content: Ingest via UI paste or ingest_file.py and confirm obligation appears on Home and Data → Obligations
    status: completed
isProject: false
---

# Fake mortgage statement for obligation testing

## Goal

Give you a ready-to-ingest fake mortgage statement that **should** create an obligation (not a position), so you can verify the obligations flow end-to-end.

## Why this design

Ingest tries **position** (maturity date) before **obligation** (due date). Real mortgage statements often include a loan payoff/maturity date, which can incorrectly land as a position and skip obligation extraction entirely.

The test doc is written to:
- Include clear **Payment due date** and **Amount due** labels (matches [`regex_extract_obligation`](app/ingest_structured.py))
- Use a due date **within 30 days** of today (July 1, 2026) so it shows on Home under "Bills & obligations due soon", not just Data → Obligations
- **Avoid** "maturity date", "matures on", "term end" wording so position extraction does not win

## File to add

**Path:** [`to-ingest-test-docs/sample-mortgage-statement.txt`](to-ingest-test-docs/sample-mortgage-statement.txt)

**Contents:**

```
First Horizon Home Lending
Monthly Mortgage Statement

Statement date: June 1, 2026
Loan number: ****8821

Borrower: Alex Sample
Property: 123 Maple Street, Anytown, ST 12345

Payment summary
────────────────────────────────────
Principal and interest    $1,842.00
Escrow (taxes/insurance)  $   405.00
Fees                      $     0.00
────────────────────────────────────
Total amount due          $2,247.00

Payment due date: July 1, 2026

Please pay by the due date to avoid late fees.

Loan details (for reference)
Outstanding principal balance: $312,450.00
Interest rate: 6.125%
Next statement: August 2026

Questions? Call (800) 555-0199.
```

Expected extraction:
- `due_date`: `2026-07-01`
- `amount_estimate`: `2247.0`
- `description`: filename/title (e.g. "sample-mortgage-statement")

## How to ingest (pick one)

### Option A — UI paste (easiest)

1. Open **Add document**
2. Expand **Or paste text instead**
3. Paste the full text above
4. Set **Title** to `Mortgage Statement - July 2026` (optional but helpful)
5. Submit

### Option B — CLI (after file is created)

```bash
source .venv/bin/activate
python ingest_file.py to-ingest-test-docs/sample-mortgage-statement.txt \
  --title "Mortgage Statement - July 2026"
```

## What to expect if obligations work

| Check | Expected |
|-------|----------|
| After ingest | Redirect to **Home** (due date found) |
| Home → Recently added | Mortgage obligation row |
| Home → Bills & obligations due soon | Due July 1, 2026 — ~$2,247 |
| Data → Obligations | Same entry in the table |
| Ask → "What bills are due soon?" | Mentions the mortgage payment |

If ingest stays on Add document with "Ready for Ask — no maturity or bill date found", extraction failed (check Ollama is running and `INGEST_STRUCTURED_ENABLED` is on in [`.env`](.env)).

## Optional second test doc (edge case)

If you also want to test the **position-steals-obligation** bug on real-world statements, we can add `sample-mortgage-with-maturity.txt` that includes both "Payment due date" and "Loan maturity date: January 1, 2051" — that one would likely **not** show under obligations today. Not needed for the basic happy-path test.

## Implementation scope

Single new file in `to-ingest-test-docs/`. No backend or UI changes.
