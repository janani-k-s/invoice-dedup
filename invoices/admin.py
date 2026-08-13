import csv
from django.contrib import admin
from django.http import HttpResponse
from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'seller_name', 'client_name', 'total_amount', 'status', 'match_score', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'seller_name', 'client_name')
    readonly_fields = ('status', 'match_score', 'matched_invoice', 'invoice_number', 'client_name', 'seller_name', 'invoice_date', 'total_amount')
    actions = ['export_as_csv']

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=invoices_export.csv'

        writer = csv.writer(response)
        writer.writerow([
            'Invoice Number', 'Client Name', 'Seller Name', 'Invoice Date',
            'Total Amount', 'Status', 'Match Score', 'Uploaded By', 'Created At'
        ])

        for invoice in queryset:
            writer.writerow([
                invoice.invoice_number,
                invoice.client_name,
                invoice.seller_name,
                invoice.invoice_date,
                invoice.total_amount,
                invoice.status,
                invoice.match_score,
                invoice.uploaded_by,
                invoice.created_at,
            ])

        return response

    export_as_csv.short_description = "Export selected invoices as CSV"