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


# Fields we care about, in priority order for amount (first found wins)
AMOUNT_FIELD_PRIORITY = ['AMOUNT_DUE', 'TOTAL']
DATE_FIELD_PRIORITY = ['INVOICE_RECEIPT_DATE', 'DUE_DATE']

SIMPLE_FIELD_MAP = {
    'INVOICE_RECEIPT_ID': 'invoice_number',
    'VENDOR_NAME': 'seller_name',
    'RECEIVER_NAME': 'client_name',
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

    # Collect all fields by type first, since some types can appear more than once
    fields_by_type = {}
    for field in summary_fields:
        field_type = field.get('Type', {}).get('Text', '')
        value = field.get('ValueDetection', {}).get('Text', '')
        if field_type and value:
            fields_by_type.setdefault(field_type, []).append(value)

    # Simple 1:1 fields
    for textract_type, our_key in SIMPLE_FIELD_MAP.items():
        if textract_type in fields_by_type:
            result[our_key] = fields_by_type[textract_type][0]

    # Amount: try AMOUNT_DUE first, fall back to TOTAL
    for field_type in AMOUNT_FIELD_PRIORITY:
        if field_type in fields_by_type:
            result['total_amount'] = _parse_amount(fields_by_type[field_type][0])
            break

    # Date: try INVOICE_RECEIPT_DATE first, fall back to DUE_DATE
    for field_type in DATE_FIELD_PRIORITY:
        if field_type in fields_by_type:
            parsed = _parse_date(fields_by_type[field_type][0])
            if parsed:
                result['invoice_date'] = parsed
                break

    return result


def _parse_date(value):
    for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%B %d, %Y', '%d-%b-%y', '%d-%b-%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value):
    cleaned = ''.join(c for c in value if c.isdigit() or c in '.,')
    if not cleaned:
        return 0

    if ',' in cleaned and '.' in cleaned:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
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