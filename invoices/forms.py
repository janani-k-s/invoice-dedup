
from django import forms
from .models import Invoice


class InvoiceUploadForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['image']

    def clean_image(self):
        uploaded_file = self.cleaned_data.get('image')

        if not uploaded_file:
            raise forms.ValidationError("Please select an invoice file.")

        allowed_extensions = ('.jpg', '.jpeg', '.png')
        filename = uploaded_file.name.lower()

        if not filename.endswith(allowed_extensions):
            raise forms.ValidationError(
                "Only JPG, JPEG and PNG files are allowed."
            )

        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                "File size must not exceed 10 MB."
            )

        return uploaded_file
