from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from django.conf import settings

from pathlib import Path
from decimal import Decimal
import requests
import os
import json
import datetime as dt


def send_contact_email(form):

    inquiry_type = form.cleaned_data["inquiry_type"]

    name = form.cleaned_data["name"]
    email = form.cleaned_data["email"]
    phone = form.cleaned_data["phone"]
    subject = form.cleaned_data["subject"]
    message = form.cleaned_data["message"]
    order_id = form.cleaned_data.get("order_id")

    #
    # EMAIL TO ADMIN
    #

    admin_context = {
        "name": name,
        "email": email,
        "phone": phone,
        "subject": subject,
        "message": message,
        "order_id": order_id,
        "inquiry_type": inquiry_type,
    }

    admin_html = render_to_string(
        "emails/contact_admin.html",
        admin_context,
    )

    admin_email = EmailMultiAlternatives(
        subject=f"[{inquiry_type.upper()}] {subject}",
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.DEFAULT_FROM_EMAIL],
    )

    admin_email.attach_alternative(
        admin_html,
        "text/html",
    )

    admin_email.send()

    #
    # EMAIL TO USER
    #

    user_context = {
        "name": name,
        "subject": subject,
        "order_id": order_id,
        "inquiry_type": inquiry_type,
    }

    user_html = render_to_string(
        "emails/contact_confirmation.html",
        user_context,
    )

    user_email = EmailMultiAlternatives(
        subject=f"Thanks for contacting Zafium - {subject}",
        body="Thank you for contacting us.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    user_email.attach_alternative(
        user_html,
        "text/html",
    )

    user_email.send()


EXCHANGE_FILE = Path(settings.BASE_DIR) / "exchange_rate.json"

def get_usd_to_pkr_rate_per_day():

    today = dt.date.today()

    # Existing cached rate
    if EXCHANGE_FILE.exists():

        try:
            with open(EXCHANGE_FILE, "r") as file:
                available_rate = json.load(file)

            fetched_date = dt.date.fromisoformat(
                available_rate["fetched_date"]
            )

            # Rate is still valid for today
            if fetched_date == today:
                return Decimal(str(available_rate["rate"]))

        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Fetch fresh rate
    response = requests.get(
        "https://open.er-api.com/v6/latest/USD",
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    usd_pkr = Decimal(str(data["rates"]["PKR"]))

    available_rate = {
        "fetched_date": today.isoformat(),
        "rate": str(usd_pkr),
    }

    with open(EXCHANGE_FILE, "w") as file:
        json.dump(available_rate, file)

    return usd_pkr