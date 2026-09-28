# Invoice Dedup

A duplicate invoice detection system for teams. Upload an invoice image and the system reads it, checks it against every invoice already on file, and flags exact and near-duplicates before they get processed twice.

**Live demo:** https://invoice-dedup.onrender.com/upload/
*(Hosted on a free tier. The first visit after a period of inactivity can take 30-60 seconds to wake up.)*

## How it works

1. A logged-in user uploads an invoice image (JPG or PNG)
2. AWS Textract (`AnalyzeExpense`) extracts the invoice number, seller, client, date and total
3. The extracted fields are compared against all existing invoices using fuzzy matching (`rapidfuzz`)
4. The similarity score decides what happens next:

| Score | Result |
|---|---|
| 95% or higher | A confirmation page warns of a likely duplicate. The user can cancel or save anyway (saved as *Duplicate*). |
| 70% to 95% | Saved with *Review* status and sent to the Review Queue for a staff member to approve or reject. |
| Below 70% | Saved as *New*. |

5. The image is stored in a private AWS S3 bucket, and the record is stored in PostgreSQL

**Scoring:** invoice number similarity (70% weight) plus amount closeness (30% weight).

## Features

- Login-protected app with separate pages for Upload, All Invoices and Review Queue
- Duplicate confirmation prompt before saving likely duplicates
- Staff-only Review Queue with approve and reject actions
- Toast notifications for upload, duplicate, cancel and review outcomes
- CSV export of invoice data through the Django admin
- Handles both `1,234.56` and `1.234,56` style amounts

## Tech stack

| Layer | Tool |
|---|---|
| Backend | Django 6 |
| Database | PostgreSQL (Neon in production, local Postgres in development) |
| File storage | AWS S3 via `django-storages` |
| OCR / extraction | AWS Textract `AnalyzeExpense` via `boto3` |
| Matching | `rapidfuzz` |
| Static files | WhiteNoise |
| Server | Gunicorn on Render |

## Pages

| URL | Access | Purpose |
|---|---|---|
| `/accounts/login/` | Anyone | Log in |
| `/upload/` | Logged-in users | Upload an invoice |
| `/invoices/` | Logged-in users | All invoices with status and match score |
| `/review/` | Staff only | Approve or reject near-duplicates |
| `/admin/` | Superusers | Manage users and export CSV |

There is no public signup. An admin creates accounts in the Django admin. All users on an instance see the same shared pool of invoices, which is what allows duplicates to be caught across uploaders.

## Local setup

**Requirements:** Python 3.13, PostgreSQL, and an AWS account.

```bash
git clone https://github.com/janani-k-s/invoice-dedup.git
cd invoice-dedup
python -m venv venv
venv\Scripts\activate          # Windows (use: source venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
```

Create a local PostgreSQL database (for example `invoice_dedup`), then create a `.env` file in the project root:

```
DB_NAME=invoice_dedup
DB_USER=postgres
DB_PASSWORD=your_local_password
DB_HOST=localhost
DB_PORT=5432

AWS_ACCESS_KEY_ID=your_key_id
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your-bucket-name
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Uploads go to S3 and Textract even in local development, so AWS credentials are required. Each Textract page costs a small amount, so test with a few images rather than bulk uploads.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Local only | Used when `DATABASE_URL` is not set |
| `DATABASE_URL` | Production | Full Postgres connection string (Neon) |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Yes | IAM user credentials |
| `AWS_REGION` | Yes | Region of the bucket |
| `AWS_S3_BUCKET_NAME` | Yes | Private bucket for invoice images |
| `SECRET_KEY` | Production | Generate a new one; never reuse a development key |
| `DEBUG` | Production | Must be `False` |
| `ALLOWED_HOSTS` | Production | For example `.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | Production | For example `https://*.onrender.com` |

## AWS setup

- **S3 bucket:** keep *Block all public access* turned on. Invoices contain business data.
- **IAM user:** use least privilege. Only these permissions are needed:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::YOUR-BUCKET/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::YOUR-BUCKET"
    },
    {
      "Effect": "Allow",
      "Action": ["textract:AnalyzeExpense"],
      "Resource": "*"
    }
  ]
}
```

- **Billing:** set an AWS Budget alert so unexpected Textract usage is caught early.

## Deployment

The app runs on Render with a Neon PostgreSQL database.

- **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start command:** `gunicorn config.wsgi:application`
- Set the environment variables listed above in Render's dashboard
- Run `python manage.py migrate` against the production database once (with `DATABASE_URL` set) and create a superuser

## Known limitations

- **English-language invoices only.** Textract's `AnalyzeExpense` supports English for structured invoice fields. Other languages may extract poorly. The Review Queue acts as a safety net.
- **Extraction varies by layout.** Invoices with several total-like figures (for example taxable value versus grand total) can be misread, and long seller names may be truncated. The extractor prefers the amount-due field over the plain total to reduce this.
- **Matching uses invoice number and amount only.** Seller and date are extracted but not yet part of the score.
- **JPG and PNG only.** PDF uploads are not supported yet.
- **Single shared workspace.** Every user sees every invoice. There is no per-company separation yet.
- **Pending confirmations are short-lived.** A file waiting on the duplicate confirmation page is held temporarily on the server's disk and is lost if the server restarts before the user responds.
- **Free-tier hosting.** Cold starts after inactivity, and the database has usage limits.
- **No automated test suite yet.**

## Roadmap

- Include seller and date in the similarity score
- Multi-tenancy, so each company has its own users and invoices
- PDF support
- Automated tests
- Signup and invite flow for company admins

## Security notes

- Secrets live in environment variables and `.env`, which is git-ignored
- No public signup; every page except login requires authentication
- S3 bucket is private and the IAM user is limited to that bucket and one Textract call