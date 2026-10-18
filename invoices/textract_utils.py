
import time
import boto3
from datetime import datetime
from django.conf import settings


def get_textract_client():
    kwargs = {"region_name": settings.AWS_REGION}

    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

    return boto3.client("textract", **kwargs)


AMOUNT_FIELD_PRIORITY = ["AMOUNT_DUE", "TOTAL"]
DATE_FIELD_PRIORITY = ["INVOICE_RECEIPT_DATE", "DUE_DATE"]

SIMPLE_FIELD_MAP = {
    "INVOICE_RECEIPT_ID": "invoice_number",
    "VENDOR_NAME": "seller_name",
    "RECEIVER_NAME": "client_name",
}


def extract_invoice_fields(file_bytes, filename=None, s3_key=None):
    client = get_textract_client()

    if filename and filename.lower().endswith(".pdf"):
        if not s3_key:
            raise ValueError("PDF processing requires an S3 object key.")

        response = client.start_expense_analysis(
            DocumentLocation={
                "S3Object": {
                    "Bucket": settings.AWS_S3_BUCKET_NAME,
                    "Name": s3_key,
                }
            }
        )
        job_id = response["JobId"]

        for _ in range(60):
            result = client.get_expense_analysis(JobId=job_id)
            status = result["JobStatus"]

            if status == "SUCCEEDED":
                break
            if status == "FAILED":
                raise RuntimeError("Textract could not process this PDF.")

            time.sleep(2)
        else:
            raise TimeoutError("PDF analysis timed out. Please try again.")

        expense_documents = result.get("ExpenseDocuments", [])
        next_token = result.get("NextToken")

        while next_token:
            page = client.get_expense_analysis(
                JobId=job_id, NextToken=next_token
            )
            expense_documents.extend(page.get("ExpenseDocuments", []))
            next_token = page.get("NextToken")

        response = {"ExpenseDocuments": expense_documents}
    else:
        response = client.analyze_expense(Document={"Bytes": file_bytes})

    result = {
        "invoice_number": "",
        "client_name": "",
        "seller_name": "",
        "invoice_date": None,
        "total_amount": 0,
    }

    documents = response.get("ExpenseDocuments", [])
    if not documents:
        return result

    fields_by_type = {}
    for document in documents:
        for field in document.get("SummaryFields", []):
            field_type = field.get("Type", {}).get("Text", "")
            value = field.get("ValueDetection", {}).get("Text", "")
            if field_type and value:
                fields_by_type.setdefault(field_type, []).append(value)

    for textract_type, our_key in SIMPLE_FIELD_MAP.items():
        if fields_by_type.get(textract_type):
            result[our_key] = fields_by_type[textract_type][0]

    for field_type in AMOUNT_FIELD_PRIORITY:
        if fields_by_type.get(field_type):
            result["total_amount"] = _parse_amount(
                fields_by_type[field_type][0]
            )
            break

    for field_type in DATE_FIELD_PRIORITY:
        if fields_by_type.get(field_type):
            parsed = _parse_date(fields_by_type[field_type][0])
            if parsed:
                result["invoice_date"] = parsed
                break

    return result


def _parse_date(value):
    for fmt in (
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%d-%b-%y",
        "%d-%b-%Y",
    ):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value):
    cleaned = "".join(c for c in value if c.isdigit() or c in ".,")
    if not cleaned:
        return 0

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        last_part = cleaned.split(",")[-1]
        if len(last_part) == 2:
            cleaned = cleaned.replace(",", ".")
            if cleaned.count(".") > 1:
                parts = cleaned.split(".")
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
        else:
            cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return 0
