from django import forms
from .models import Order


class ContactForm(forms.Form):

    INQUIRY_CHOICES = (
        ("new", "New Customer"),
        ("existing", "Existing Customer"),
    )

    inquiry_type = forms.ChoiceField(
        choices=INQUIRY_CHOICES,
        widget=forms.RadioSelect,
        initial="new",
    )

    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "placeholder": "Your Name"
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": "Your Email"
        })
    )

    phone = forms.CharField(
        required=False,
        max_length=30,
        widget=forms.TextInput(attrs={
            "placeholder": "Phone (Optional)"
        })
    )

    order_id = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            "placeholder": "Order ID"
        })
    )

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "placeholder": "Subject"
        })
    )

    message = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": "How can we help you?"
        })
    )

    def clean(self):

        cleaned_data = super().clean()

        inquiry_type = cleaned_data.get("inquiry_type")
        order_id = cleaned_data.get("order_id")
        email = cleaned_data.get("email")

        if inquiry_type == "existing":

            if not order_id:
                self.add_error(
                    "order_id",
                    "Order ID is required."
                )

            elif not Order.objects.filter(
                id=order_id,
                client__email=email
            ).exists():

                self.add_error(
                    "order_id",
                    "We couldn't find an order with this Order ID and email."
                )

        return cleaned_data