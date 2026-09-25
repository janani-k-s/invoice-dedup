# Invoice Dedup

A duplicate invoice detection system built with Django, PostgreSQL, AWS Textract, and fuzzy matching. Detects and flags duplicate or near-duplicate invoices on upload, with a human review workflow for uncertain matches.

## How it works

1. User uploads an invoice image (JPG/PNG)
2. Image is stored in AWS S3
3. AWS Textract (`AnalyzeExpense`) extracts structured fields: invoice number, vendor, client, date, total amount
4. The system compares extracted fields against previously stored invoices using fuzzy matching (`rapidfuzz`)
5. Based on similarity score:
   - **≥95%** — flagged as a likely duplicate; user is prompted to confirm before saving
   - **70–95%** — saved, but flagged for manual review in the Review Queue
   - **<70%** — saved as a new invoice

## Tech stack

- Django (backend, templates)
- PostgreSQL (database)
- AWS S3 (file storage)
- AWS Textract `AnalyzeExpense` (OCR/field extraction)
- rapidfuzz (fuzzy string matching)
- Tailwind CSS (UI, via Stitch-generated design)

## Known limitations

- **English-only invoices**: AWS Textract's `AnalyzeExpense` API only supports English for structured invoice/receipt field extraction. Invoices in other languages may extract poorly or fail to populate fields correctly. The Review Queue acts as a safety net for these cases.
- Matching is currently based primarily on invoice number and total amount; vendor name and date are extracted but not yet weighted into the similarity score.
- No automated test suite yet.

## Setup

(To be filled in — env vars needed, local setup steps, etc.)