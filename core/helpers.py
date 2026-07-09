from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


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