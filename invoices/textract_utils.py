import boto3
from datetime import datetime
from django.conf import settings


def get_textract_client():
    return boto3.client(
        'textract',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


# Maps Textract's field labels to our own field names
FIELD_MAP = {
    'INVOICE_RECEIPT_ID': 'invoice_number',
    'VENDOR_NAME': 'seller_name',
    'RECEIVER_NAME': 'client_name',
    'INVOICE_RECEIPT_DATE': 'invoice_date',
    'TOTAL': 'total_amount',
}


def extract_invoice_fields(file_bytes):
    """
    Sends raw image bytes to Textract's AnalyzeExpense API,
    returns a dict shaped like get_ground_truth()'s output.
    """
    client = get_textract_client()
    response = client.analyze_expense(Document={'Bytes': file_bytes})

    result = {
        'invoice_number': '',
        'client_name': '',
        'seller_name': '',
        'invoice_date': None,
        'total_amount': 0,
    }

    if not response.get('ExpenseDocuments'):
        return result

    summary_fields = response['ExpenseDocuments'][0].get('SummaryFields', [])

    for field in summary_fields:
        field_type = field.get('Type', {}).get('Text', '')
        value = field.get('ValueDetection', {}).get('Text', '')

        if field_type in FIELD_MAP:
            key = FIELD_MAP[field_type]

            if key == 'invoice_date':
                result[key] = _parse_date(value)
            elif key == 'total_amount':
                result[key] = _parse_amount(value)
            else:
                result[key] = value

    return result


def _parse_date(value):
    # Textract dates can come in various formats - try common ones
    for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%B %d, %Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value):
    # Keep only digits, commas, and periods
    cleaned = ''.join(c for c in value if c.isdigit() or c in '.,')
    if not cleaned:
        return 0

    if ',' in cleaned and '.' in cleaned:
        # Both separators present - whichever comes LAST is the decimal point
        if cleaned.rfind(',') > cleaned.rfind('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Only comma present - if exactly 2 digits follow it, it's a decimal separator
        last_part = cleaned.split(',')[-1]
        if len(last_part) == 2:
            cleaned = cleaned.replace(',', '.')
            if cleaned.count('.') > 1:
                parts = cleaned.split('.')
                cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        else:
            cleaned = cleaned.replace(',', '')

    try:
        return float(cleaned)
    except ValueError:
        return 0