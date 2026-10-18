
from datetime import date, datetime

from rapidfuzz import fuzz
from .models import Invoice


def calculate_similarity(
    invoice_number_a,
    invoice_number_b,
    amount_a,
    amount_b,
    seller_a="",
    seller_b="",
    date_a=None,
    date_b=None,
):
    """Compare invoice number, amount, vendor, and date."""

    number_a = str(invoice_number_a or "").strip().lower()
    number_b = str(invoice_number_b or "").strip().lower()

    number_score = (
        fuzz.ratio(number_a, number_b)
        if number_a and number_b else 0
    )

    vendor_a = str(seller_a or "").strip()
    vendor_b = str(seller_b or "").strip()

    seller_score = (
        fuzz.ratio(vendor_a.lower(), vendor_b.lower())
        if vendor_a and vendor_b else 0
    )

    try:
        amount_a = float(amount_a)
        amount_b = float(amount_b)
        largest = max(abs(amount_a), abs(amount_b), 1)

        if amount_a == 0 and amount_b == 0:
            amount_score = 100
        else:
            amount_score = max(
                0, 100 - abs(amount_a - amount_b) / largest * 100
            )
    except (ValueError, TypeError):
        amount_score = 0

    def parse_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if value:
            try:
                return date.fromisoformat(str(value))
            except (ValueError, TypeError):
                pass
        return None

    date_a = parse_date(date_a)
    date_b = parse_date(date_b)

    date_missing = not date_a or not date_b
    date_mismatch = False

    if date_missing:
        date_score = 0
    else:
        days_apart = abs((date_a - date_b).days)
        date_score = max(0, 100 - days_apart * 10)
        date_mismatch = days_apart != 0

    combined_score = (
        number_score * 0.40
        + amount_score * 0.25
        + seller_score * 0.20
        + date_score * 0.15
    )

    if not vendor_a or not vendor_b:
        combined_score = min(combined_score, 94)
    elif seller_score < 50:
        return 0

    # Missing or different dates require review, not auto-duplicate.
    if date_missing or date_mismatch:
        combined_score = min(combined_score, 94)

    return combined_score


def find_best_match(new_invoice):
    """Compare a saved invoice against other invoices."""

    existing = Invoice.objects.exclude(pk=new_invoice.pk)
    best_match, best_score = None, 0

    for other in existing:
        score = calculate_similarity(
            new_invoice.invoice_number,
            other.invoice_number,
            new_invoice.total_amount,
            other.total_amount,
            new_invoice.seller_name,
            other.seller_name,
            new_invoice.invoice_date,
            other.invoice_date,
        )

        if score > best_score:
            best_match, best_score = other, score

    return best_match, best_score


def find_best_match_unsaved(temp_invoice):
    """Compare an unsaved invoice against existing invoices."""

    existing = Invoice.objects.all()
    best_match, best_score = None, 0

    for other in existing:
        score = calculate_similarity(
            temp_invoice.invoice_number,
            other.invoice_number,
            temp_invoice.total_amount,
            other.total_amount,
            temp_invoice.seller_name,
            other.seller_name,
            temp_invoice.invoice_date,
            other.invoice_date,
        )

        if score > best_score:
            best_match, best_score = other, score

    return best_match, best_score


def get_status_from_score(score):
    """Convert the matching score into an invoice status."""

    if score >= 95:
        return "duplicate"
    elif score >= 70:
        return "review"
    return "new"
