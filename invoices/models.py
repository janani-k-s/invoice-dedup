from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Invoice(models.Model):
    STATUS_CHOICES = [
        ('new','New'),
        ('duplicate','Duplicate'),
        ('review','Needs Review'),
    ]

    invoice_number = models.CharField(max_length=100)
    client_name = models.CharField(max_length=255)
    seller_name = models.CharField(max_length=255)
    invoice_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    image=models.ImageField(upload_to='invoices/', null=True, blank=True)
    uploaded_by=models.ForeignKey(User, on_delete=models.CASCADE)

    status=models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    match_score=models.FloatField(null=True, blank=True)
    matched_invoice=models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='duplicate_of')
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} - {self.seller_name} - {self.invoice_number}"