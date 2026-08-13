from rapidfuzz import fuzz
from .models import Invoice


def calculate_similarity(invoice_number_a, invoice_number_b, amount_a, amount_b):
    """
    Compares two invoices on invoice_number and amount, returns a 0-100 score.
    """
    number_score = fuzz.ratio(str(invoice_number_a), str(invoice_number_b))

    # Amount comparison: treat as very close if within a small tolerance
    try:
        amount_a = float(amount_a)
        amount_b = float(amount_b)
        if amount_a == 0 and amount_b == 0:
            amount_score = 100
        else:
            diff = abs(amount_a - amount_b)
            largest = max(abs(amount_a), abs(amount_b), 1)
            amount_score = max(0, 100 - (diff / largest * 100))
    except (ValueError, TypeError):
        amount_score = 0

    # Weighted combination: invoice number matters most
    combined_score = (number_score * 0.7) + (amount_score * 0.3)
    return combined_score


def find_best_match(new_invoice):
    """
    Compares new_invoice against all existing invoices (excluding itself),
    returns (best_match_invoice, best_score) or (None, 0) if no others exist.
    """
    existing = Invoice.objects.exclude(pk=new_invoice.pk)

    best_match = None
    best_score = 0

    for other in existing:
        score = calculate_similarity(
            new_invoice.invoice_number, other.invoice_number,
            new_invoice.total_amount, other.total_amount
        )
        if score > best_score:
            best_score = score
            best_match = other

    return best_match, best_score

def find_best_match_unsaved(temp_invoice):
    """
    Same as find_best_match, but for an invoice that hasn't been saved yet
    (no pk), so there's nothing to exclude - compares against all existing invoices.
    """
    existing = Invoice.objects.all()

    best_match = None
    best_score = 0

    for other in existing:
        score = calculate_similarity(
            temp_invoice.invoice_number, other.invoice_number,
            temp_invoice.total_amount, other.total_amount
        )
        if score > best_score:
            best_score = score
            best_match = other

    return best_match, best_score

def get_status_from_score(score):
    if score >= 95:
        return 'duplicate'
    elif score >= 70:
        return 'review'
    else:
        return 'new'