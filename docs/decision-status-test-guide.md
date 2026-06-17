# Decision status test guide

This guide explains how to test the **Decision status** ("Check status") feature in Ledgerly. The status is either **No action required** or **Actionable**, depending on your positions and obligations in the next 30 days.

## How it works

- **No action required**: No CDs (or other positions) maturing in the next 30 days, and no obligations due in the next 30 days.
- **Actionable**: At least one position maturing within 30 days and/or one obligation due within 30 days.

Positions and obligations are entered in **Data → Accounts**, **Data → Positions**, and **Data → Obligations**. Ingested documents are used for the **Ask** tab and can be linked to these entities; they do **not** create positions or obligations automatically.

Use **relative dates** below (e.g. "14 days from today") so this guide stays valid.

---

## Scenario A — No action required

1. **Data → Accounts**: Add an account (e.g. Name: "Savings – First National", Institution: "First National Bank").
2. **Data → Positions**: Add a position under that account:
   - Asset type: **CD**
   - Maturity date: **more than 30 days from today** (e.g. 60 days from today in `YYYY-MM-DD` format).
   - Optionally set Principal, Rate APR, Description.
3. Optionally **Data → Obligations**: Add an obligation with due date **more than 30 days from today** (or skip obligations).
4. Open the **Status** tab and click **Check status**.
5. **Expected**: "No action required" and a memo stating no CDs maturing soon and no obligations due in the next 30 days.

---

## Scenario B — Actionable (maturity)

1. Use the same account from Scenario A (or create one).
2. **Data → Positions**: Add a **new** position (or edit the existing one):
   - Asset type: **CD**
   - Maturity date: **within the next 30 days** (e.g. 14 days from today in `YYYY-MM-DD` format).
3. Open the **Status** tab and click **Check status**.
4. **Expected**: "Actionable", with a maturity trigger and a memo mentioning the CD maturing soon.

---

## Scenario C — Actionable (obligation)

1. **Data → Obligations**: Add an obligation:
   - Description: e.g. "Property tax – County" or "Test bill"
   - Due date: **within the next 30 days** (e.g. 7 days from today in `YYYY-MM-DD` format).
   - Optionally set Amount estimate and Priority.
2. Open the **Status** tab and click **Check status**.
3. **Expected**: "Actionable", with an obligation_due trigger and a memo mentioning the obligation due soon.

---

## Optional: curl for test data

Replace `YOUR_ACCOUNT_ID`, dates, and (for obligations) descriptions as needed. Base URL: `http://localhost:8000`.

**Create an account:**

```bash
curl -s -X POST "http://localhost:8000/accounts" \
  -H "Content-Type: application/json" \
  -d '{"name": "Savings – First National", "institution": "First National Bank"}'
```

Use the returned `id` as `YOUR_ACCOUNT_ID` below.

**Create a position (maturity in 30 days → actionable):**

```bash
# Use a date 14 days from today in YYYY-MM-DD
curl -s -X POST "http://localhost:8000/positions" \
  -H "Content-Type: application/json" \
  -d '{"account_id": "YOUR_ACCOUNT_ID", "asset_type": "CD", "maturity_date": "2025-03-29", "principal": 10000, "rate_apr": 4.5}'
```

**Create a position (maturity beyond 30 days → no action required):**

```bash
# Use a date 60 days from today in YYYY-MM-DD
curl -s -X POST "http://localhost:8000/positions" \
  -H "Content-Type: application/json" \
  -d '{"account_id": "YOUR_ACCOUNT_ID", "asset_type": "CD", "maturity_date": "2025-05-14", "principal": 10000, "rate_apr": 4.5}'
```

**Create an obligation (due in 30 days → actionable):**

```bash
# Use a date 7 days from today in YYYY-MM-DD
curl -s -X POST "http://localhost:8000/obligations" \
  -H "Content-Type: application/json" \
  -d '{"description": "Property tax – County", "due_date": "2025-03-22", "amount_estimate": 1200}'
```

---

## Using the sample documents

The folder also contains:

- **sample-cd-maturity-letter.md** — Ingest this (paste text or convert to PDF) to test the Ask tab with a CD letter. Add a matching position with maturity within 30 days to see "Actionable" and to link the document to the position.
- **sample-bill-reminder.md** — Ingest to test Ask with a bill. Add a matching obligation with due date within 30 days to see "Actionable" and to link the document.

These samples are not required for the status result but make the end-to-end flow (ingest → Data → Ask → Check status) realistic.
