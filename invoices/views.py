from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from .forms import InvoiceUploadForm
from .models import Invoice
from .textract_utils import extract_invoice_fields
#from .dataset_lookup import get_ground_truth
from .matching import find_best_match, get_status_from_score, find_best_match_unsaved,get_status_from_score
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def review_queue(request):
    flagged_invoices = Invoice.objects.filter(status='review').order_by('-created_at')
    return render(request, 'invoices/review_queue.html', {'invoices': flagged_invoices})

@staff_member_required
def review_decision(request, invoice_id):
    if request.method == 'POST':
        invoice = Invoice.objects.get(id=invoice_id)
        decision = request.POST.get('decision')

        if decision == 'approve':
            invoice.status = 'new'
        elif decision == 'reject':
            invoice.status = 'duplicate'

        invoice.save()

    return redirect('review_queue')

@login_required
def upload_invoice(request):
    if request.method == 'POST':
        form = InvoiceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['image']
            filename = uploaded_file.name

            # Temporarily save file so we can reference it after confirmation
            fs = FileSystemStorage(location='media/temp_uploads/')
            temp_filename = fs.save(filename, uploaded_file)

            uploaded_file.seek(0)
            file_bytes = uploaded_file.read()
            extracted = extract_invoice_fields(file_bytes)
            temp_data={
                'invoice_number': extracted['invoice_number'] or 'UNKNOWN',
                'client_name': extracted['client_name'] or 'UNKNOWN',
                'seller_name': extracted['seller_name'] or 'UNKNOWN',
                'invoice_date':str(extracted['invoice_date']) if extracted['invoice_date'] else '',
                'total_amount': str(extracted['total_amount']),
            }
            # Build a temporary unsaved Invoice instance just to run matching
            temp_invoice = Invoice(
                invoice_number=temp_data['invoice_number'],
                total_amount=temp_data['total_amount'],
            )
            best_match, best_score = find_best_match_unsaved(temp_invoice)

            if best_score >= 95:
                # Stash everything needed in session, show confirmation page
                request.session['pending_invoice'] = {
                    'temp_filename': temp_filename,
                    'original_filename': filename,
                    **temp_data,
                    'match_score': best_score,
                    'matched_invoice_id': best_match.id if best_match else None,
                }
                return render(request, 'invoices/confirm_duplicate.html', {
                    'match_score': best_score,
                    'matched_invoice': best_match,
                })
            else:
                # Not a likely duplicate - save immediately as before
                _save_invoice_from_temp(request, temp_filename, filename, temp_data, best_match, best_score)
                return redirect('upload_invoice')

    else:
        form = InvoiceUploadForm()

    invoices = Invoice.objects.all().order_by('-created_at')
    return render(request, 'invoices/upload.html', {'form': form, 'invoices': invoices})


@login_required
def confirm_upload(request):
    """Called when user clicks 'Save anyway' on the duplicate warning page."""
    pending = request.session.get('pending_invoice')
    if not pending:
        return redirect('upload_invoice')

    matched_invoice = None
    if pending['matched_invoice_id']:
        matched_invoice = Invoice.objects.filter(id=pending['matched_invoice_id']).first()

    _save_invoice_from_temp(
        request, pending['temp_filename'], pending['original_filename'],
        pending, matched_invoice, pending['match_score']
    )
    del request.session['pending_invoice']
    return redirect('upload_invoice')


@login_required
def cancel_upload(request):
    """Called when user clicks 'Cancel' - discard the pending upload."""
    pending = request.session.get('pending_invoice')
    if pending:
        fs = FileSystemStorage(location='media/temp_uploads/')
        fs.delete(pending['temp_filename'])
        del request.session['pending_invoice']
    return redirect('upload_invoice')


def _save_invoice_from_temp(request, temp_filename, original_filename, data, matched_invoice, score):
    """Moves the temp file into the real invoice, saves the DB record."""
    from django.core.files import File
    fs = FileSystemStorage(location='media/temp_uploads/')

    invoice = Invoice(
        invoice_number=data['invoice_number'],
        client_name=data['client_name'],
        seller_name=data['seller_name'],
        invoice_date=data['invoice_date'] or None,
        total_amount=data['total_amount'],
        uploaded_by=request.user,
    )
    with fs.open(temp_filename) as f:
        invoice.image.save(original_filename, File(f), save=False)

    invoice.save()

    _, real_score = find_best_match(invoice)
    invoice.status = get_status_from_score(score)
    invoice.match_score = score
    invoice.matched_invoice = matched_invoice
    invoice.save()

    fs.delete(temp_filename)