
from rapidfuzz import fuzz
from .models import Invoice


def calculate_similarity(
    invoice_number_a,
    invoice_number_b,
    amount_a,
    amount_b,
    seller_a="",
    seller_b="",
):
    """
    Compare invoice number, amount, and vendor.
    Returns a score from 0 to 100.
    """

    # Compare invoice numbers
    number_a = str(invoice_number_a or "").strip().lower()
    number_b = str(invoice_number_b or "").strip().lower()

    if number_a and number_b:
        number_score = fuzz.ratio(number_a, number_b)
    else:
        number_score = 0

    # Compare vendor names
    vendor_a = str(seller_a or "").strip()
    vendor_b = str(seller_b or "").strip()

    if vendor_a and vendor_b:
        seller_score = fuzz.ratio(
            vendor_a.lower(),
            vendor_b.lower(),
        )
    else:
        seller_score = 0

    # Compare invoice amounts
    try:
        amount_a = float(amount_a)
        amount_b = float(amount_b)

        if amount_a == 0 and amount_b == 0:
            amount_score = 100
        else:
            difference = abs(amount_a - amount_b)
            largest = max(abs(amount_a), abs(amount_b), 1)

            amount_score = max(
                0,
                100 - (difference / largest * 100),
            )

    except (ValueError, TypeError):
        amount_score = 0

    # Weighted matching score
    combined_score = (
        number_score * 0.50
        + amount_score * 0.30
        + seller_score * 0.20
    )

    # Missing vendor information: do not auto-classify
    # as a duplicate.
    if not vendor_a or not vendor_b:
        combined_score = min(combined_score, 94)

    # Clearly different vendors: treat as unrelated invoices.
    elif seller_score < 50:
        return 0

    return combined_score


def find_best_match(new_invoice):
    """
    Compare a saved invoice against existing invoices,
    excluding itself.
    Returns (best_match, best_score).
    """

    existing = Invoice.objects.exclude(pk=new_invoice.pk)

    best_match = None
    best_score = 0

    for other in existing:
        score = calculate_similarity(
            new_invoice.invoice_number,
            other.invoice_number,
            new_invoice.total_amount,
            other.total_amount,
            new_invoice.seller_name,
            other.seller_name,
        )

        if score > best_score:
            best_score = score
            best_match = other

    return best_match, best_score


def find_best_match_unsaved(temp_invoice):
    """
    Compare an unsaved invoice against existing invoices.
    """

    existing = Invoice.objects.all()

    best_match = None
    best_score = 0

    for other in existing:
        score = calculate_similarity(
            temp_invoice.invoice_number,
            other.invoice_number,
            temp_invoice.total_amount,
            other.total_amount,
            temp_invoice.seller_name,
            other.seller_name,
        )

        if score > best_score:
            best_score = score
            best_match = other

    return best_match, best_score


def get_status_from_score(score):
    """
    Convert the matching score into an invoice status.
    """

    if score >= 95:
        return "duplicate"
    elif score >= 70:
        return "review"
    else:
        return "new"
