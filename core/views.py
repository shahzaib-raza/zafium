from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import send_mail

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

# import pprint

from django.conf import settings
from django.http import HttpResponse
from django.contrib import messages
from decimal import Decimal

from django.http import JsonResponse
# import requests
# from requests.exceptions import RequestException

from django.http import Http404

import json
from django.template.loader import render_to_string

from django.views.decorators.csrf import csrf_exempt
import os,uuid
from .utils import _img_array_to_svg
from .models import PortfolioItem, PortfolioCategory, PortfolioSubCategory, Order, OrderItem, OrderReview, OrderRevision, OrderAttachment, UserProfile
from django.db import models

from django.views.decorators.http import require_POST

from .forms import ContactForm
from .helpers import send_contact_email

from .easypay import generate_easypay_hash
from django.utils import timezone
from datetime import timedelta

import cv2
import numpy as np
from collections import defaultdict, Counter
from plotly.offline import plot
from .api_call import get_data_pw, millify
import requests
from plotly import subplots
import plotly.graph_objs as go

from core.services.project_usage import consume_project_usage
from .decorators import project_usage_required

from .models import UserProfile
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator

def get_int(x):
    try:
        return float(x)
    except:
        return None

# Create your views here.
def home(request):
    return render(request, "home.html")

def services(request):
    return render(request, "services.html")

def about(request):
    return render(request, "about.html")

def privacy_policy(request):
    return render(request, "privacy.html")

def terms_of_service(request):
    return render(request, "terms_of_service.html")

def refund_policy(request):
    return render(request, "refund_policy.html")


def portfolio_category(request, category):

    category_obj = get_object_or_404(
        PortfolioCategory,
        slug=category
    )

    sub_slug = request.GET.get("sub", "all")

    projects = PortfolioItem.objects.filter(
        category=category_obj
    )

    if sub_slug != "all":
        projects = projects.filter(subcategory__slug=sub_slug)

    projects = projects.order_by("-created_at")

    paginator = Paginator(projects, 10)
    page = request.GET.get("page", 1)
    projects_page = paginator.get_page(page)

    # 🔥 AJAX request detection
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "includes/portfolio_cards.html",
            {"projects": projects_page}
        )
        return JsonResponse({
            "html": html,
            "has_next": projects_page.has_next()
        })

    return render(request, "portfolio_category.html", {
        "projects": projects_page,
        "category": category_obj,
        "subcategories": category_obj.subcategories.all(),
        "selected_sub": sub_slug,
    })

def portfolio_detail(request, category, slug):

    project = get_object_or_404(PortfolioItem, slug=slug)

    total_projects = PortfolioItem.objects.count()

    return render(request, "portfolio_detail.html", {
        "project": project,
        "total_projects": total_projects
    })

def robots_txt(request):
    return render(
        request,
        "robots.txt",
        content_type="text/plain"
    )


def validate_turnstile(token, secret, remoteip=None):
    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

    data = {
        'secret': secret,
        'response': token
    }

    if remoteip:
        data['remoteip'] = remoteip

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Turnstile validation error: {e}")
        return {'success': False, 'error-codes': ['internal-error']}


def contact(request):

    if request.method == "POST":

        form = ContactForm(request.POST)

        token = request.POST.get("cf-turnstile-response")

        if not token:
            messages.error(
                request,
                "Please complete the CAPTCHA verification."
            )
            return redirect("core:contact")

        result = validate_turnstile(
            token,
            settings.CF_SECRET_KEY,
        )

        if not result.get("success"):
            messages.error(request, "Failed to validate captcha")
            return redirect("core:contact")
        else:
            if form.is_valid():

                send_contact_email(form)

                messages.success(
                    request,
                    "Your message has been sent successfully. We'll get back to you within 24 hours."
                )

                return redirect("core:contact")

            # Form is invalid
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ContactForm()

    return render(
        request,
        "contact.html",
        {
            "form": form,
            'CF_SITE_KEY': settings.CF_SITE_KEY
        },
    )


def orders_activity(request):
    # Active projects (everything except completed, delivered and cancelled)
    # Active projects
    active_count = Order.objects.filter(
        project_status__in=[
            Order.ProjectStatus.NEW,
            Order.ProjectStatus.PLANNING,
            Order.ProjectStatus.IN_PROGRESS,
            Order.ProjectStatus.TESTING,
            Order.ProjectStatus.REVISION,
        ]
    ).count()

    print("active_count:", active_count)

    # Completed projects
    completed_count = Order.objects.filter(
        project_status__in=[
            Order.ProjectStatus.COMPLETED,
            Order.ProjectStatus.DELIVERED,
        ]
    ).count()

    print("completed_count:", completed_count)

    # Latest featured 5-star review
    featured_review = (
        OrderReview.objects
        .select_related(
            "order",
            "order__client",
        )
        .filter(
            approved=True,
            rating=5,
        )
        .order_by("-created_at")
        .first()
    )

    # All approved reviews
    reviews = (
        OrderReview.objects
        .select_related(
            "order",
            "order__user",
        )
        .filter(
            approved=True,
        )
        .order_by("-order__created_at")
    )

    try:
        active_count = int(active_count)
    except:
        active_count = 0

    try:
        completed_count = int(completed_count)
    except:
        completed_count = 0

    context = {
        "active_count": active_count,
        "completed_count": completed_count,
        "featured_review": featured_review,
        "reviews": reviews,
    }

    return render(
        request,
        "orders_activity.html",
        context,
    )


def pricing(request):

    categories = (
        PortfolioCategory.objects
        .prefetch_related("subcategories")
        .order_by("name")
    )

    return render(
        request,
        "pricing.html",
        {
            "categories": categories,
        },
    )

# ____________________________________________________________________________________________________________


def signup(request):

    if request.user.is_authenticated:
        return redirect("core:account")

    if request.method == "POST":

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        # -------------------------
        # VALIDATION
        # -------------------------

        if not first_name or not last_name or not email:
            return render(
                request,
                "authentication/signup.html",
                {
                    "error": "Please fill in all required fields."
                }
            )

        if password != password_confirm:
            return render(
                request,
                "authentication/signup.html",
                {
                    "error": "Passwords do not match.",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                }
            )

        if len(password) < 8:
            return render(
                request,
                "authentication/signup.html",
                {
                    "error": "Password must be at least 8 characters long.",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                }
            )

        if User.objects.filter(email=email).exists():
            return render(
                request,
                "authentication/signup.html",
                {
                    "error": "An account with this email already exists.",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                }
            )

        # -------------------------
        # CREATE USER
        # -------------------------

        with transaction.atomic():

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # Account cannot log in until email is verified
            user.is_active = False
            user.save(update_fields=["is_active"])

            # Every new account starts as FREE
            UserProfile.objects.create(
                user=user,
                plan=UserProfile.Plan.FREE,
            )

        # -------------------------
        # VERIFICATION EMAIL
        # -------------------------

        uid = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        token = default_token_generator.make_token(user)

        verification_url = request.build_absolute_uri(
            reverse(
                "core:verify_email",
                kwargs={
                    "uidb64": uid,
                    "token": token,
                }
            )
        )

        subject = "Verify your Zafium account"

        context = {
            "user": user,
            "verification_url": verification_url,
        }

        text_message = render_to_string(
            "authentication/verification_email.txt",
            context,
        )

        html_message = render_to_string(
            "authentication/verification_email.html",
            context,
        )

        email = EmailMultiAlternatives(
            subject="Verify your Zafium account",
            body=text_message,
            from_email=None,
            to=[user.email],
        )

        email.attach_alternative(
            html_message,
            "text/html",
        )

        email.send(fail_silently=False)

        return render(
            request,
            "authentication/check_email.html",
            {
                "email": user.email
            }
        )

    return render(
        request,
        "authentication/signup.html"
    )


def login_view(request):

    if request.user.is_authenticated:
        return redirect("core:account")

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=email,
            password=password,
        )

        if user is None:

            # Check whether the email exists but is not verified
            existing_user = User.objects.filter(
                email=email
            ).first()

            if existing_user and not existing_user.is_active:

                return render(
                    request,
                    "authentication/login.html",
                    {
                        "error":
                            "Please verify your email address "
                            "before signing in."
                    }
                )

            return render(
                request,
                "authentication/login.html",
                {
                    "error":
                        "Invalid email address or password.",
                    "email": email,
                }
            )

        login(request, user)

        next_url = request.POST.get("next")

        if next_url:
            return redirect(next_url)

        return redirect("core:account")

    next_url = request.GET.get("next", "")

    return render(
        request,
        "authentication/login.html",
        {
            "next": next_url
        }
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:account")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = User.objects.filter(email=email).first()

        if user is None:
            return render(
                request,
                "authentication/login.html",
                {
                    "error": "Invalid email address or password.",
                    "email": email,
                }
            )

        if not user.is_active:
            return render(
                request,
                "authentication/login.html",
                {
                    "error": "Please verify your email address before signing in.",
                    "email": email,
                }
            )

        authenticated_user = authenticate(
            request,
            username=user.username,
            password=password,
        )

        if authenticated_user is None:
            return render(
                request,
                "authentication/login.html",
                {
                    "error": "Invalid email address or password.",
                    "email": email,
                }
            )

        login(request, authenticated_user)

        next_url = request.POST.get("next")

        if next_url:
            return redirect(next_url)

        return redirect("core:account")

    next_url = request.GET.get("next", "")

    return render(
        request,
        "authentication/login.html",
        {
            "next": next_url,
        }
    )


@login_required
def logout_view(request):

    logout(request)

    return redirect("core:login")


def verify_email(request, uidb64, token):

    if request.user.is_authenticated:
        return redirect("core:account")

    try:

        uid = force_str(
            urlsafe_base64_decode(uidb64)
        )

        user = User.objects.get(pk=uid)

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
    ):

        user = None

    if user is not None and default_token_generator.check_token(
        user,
        token
    ):

        if not user.is_active:

            user.is_active = True

            user.save(
                update_fields=["is_active"]
            )

        return render(
            request,
            "authentication/email_verified.html"
        )

    return render(
        request,
        "authentication/verification_invalid.html"
    )


@login_required
def account(request):

    user = request.user

    profile = getattr(
        user,
        "profile",
        None
    )

    return render(
        request,
        "authentication/account.html",
        {
            "user": user,
            "profile": profile,
        }
    )

# ____________________________________________________________________________________________________________

@login_required
def dashboard(request):

    orders = (
        request.user.orders
        .prefetch_related(
            "items__subcategory",
            "review",
        )
        .order_by("-created_at")
    )

    order_id = request.GET.get("order_id")

    if order_id:
        orders = orders.filter(id=order_id)

    active_orders = orders.exclude(
        project_status__in=[
            Order.ProjectStatus.COMPLETED,
            Order.ProjectStatus.DELIVERED,
            Order.ProjectStatus.CANCELLED,
        ]
    )

    completed_orders = orders.filter(
        project_status__in=[
            Order.ProjectStatus.COMPLETED,
            Order.ProjectStatus.DELIVERED,
        ]
    )

    return render(
        request,
        "dashboard.html",
        {
            "user": request.user,
            "orders": orders,
            "active_orders": active_orders,
            "completed_orders": completed_orders,
        }
    )

@login_required
def order_detail(request, order_id):


    order = get_object_or_404(
        request.user.orders.prefetch_related(
            "items__subcategory",
            "review",
            "deliveries",
        ),
        id=order_id
    )

    return render(
        request,
        "order_detail.html",
        {
            "client": request.user,
            "order": order,
        }
    )


@login_required
@require_POST
def submit_review(request, order_id):

    order = get_object_or_404(
        request.user.orders,
        id=order_id
    )

    if order.project_status not in (
        Order.ProjectStatus.COMPLETED,
        Order.ProjectStatus.DELIVERED,
    ):
        messages.error(
            request,
            "Reviews are only allowed after project completion."
        )

        return redirect(
            "core:order_detail",
            order_id=order.id
        )

    if hasattr(order, "review"):
        messages.warning(
            request,
            "You have already reviewed this project."
        )

        return redirect(
            "core:order_detail",
            order_id=order.id
        )

    OrderReview.objects.create(
        order=order,
        rating=int(request.POST.get("rating")),
        title=request.POST.get("title"),
        review=request.POST.get("review"),
    )

    messages.success(
        request,
        "Thank you for your feedback!"
    )

    return redirect(
        "core:order_detail",
        order_id=order.id
    )

@login_required
def request_revision(request, order_id):


    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
    )

    # Only allow revisions after delivery
    if order.project_status != Order.ProjectStatus.DELIVERED:

        messages.error(
            request,
            "Revision requests are only available after the project has been delivered."
        )

        return redirect(
            "core:order_detail",
            order_id=order.id,
        )

    # Maximum 3 revisions
    if order.revision_count >= 3:

        messages.error(
            request,
            "You have reached the maximum of 3 revision requests for this order."
        )

        return redirect(
            "core:order_detail",
            order_id=order.id,
        )

    # Prevent multiple pending requests
    if order.revisions.filter(
        status=OrderRevision.Status.PENDING
    ).exists():

        messages.warning(
            request,
            "You already have a pending revision request."
        )

        return redirect(
            "core:order_detail",
            order_id=order.id,
        )

    if request.method == "POST":

        message = request.POST.get(
            "message",
            ""
        ).strip()

        if not message:

            messages.error(
                request,
                "Please describe the changes you would like."
            )

            return render(
                request,
                "request_revision.html",
                {
                    "order": order,
                },
            )

        OrderRevision.objects.create(
            order=order,
            message=message,
        )

        order.project_status = Order.ProjectStatus.REVISION
        order.progress = 80
        order.save(update_fields=[
            "project_status",
            "progress",
        ])

        messages.success(
            request,
            "Your revision request has been submitted successfully."
        )

        return redirect(
            "core:order_detail",
            order_id=order.id,
        )

    return render(
        request,
        "request_revision.html",
        {
            "order": order,
        },
    )

# ____________________________________________________________________________________________________________

def success_page(request):
    return render(request, "success.html")

def order(request):
    categories = PortfolioCategory.objects.prefetch_related(
        "subcategories"
    )

    return render(
        request,
        "order.html",
        {
            "categories": categories,
        },
    )


def send_order_emails(order):

    user = order.user

    order_summary = ""

    for item in order.items.select_related("subcategory"):
        order_summary += (
            f"{item.subcategory.name} "
            f"x {item.quantity} "
            f"= PKR{item.total_price()}\n"
        )

    # -------------------------
    # Admin Email
    # -------------------------
    send_mail(
        subject=f"New Order #{order.id}",
        message=f"""
        New Order Received

        Client: {user.profile.name}
        Email: {user.email}
        Phone: {user.profile.phone}

        Items:

        {order_summary}

        Status:
        {order.get_project_status_display()}

        Progress:
        {order.progress}%

        Total:
        PKR{order.total_amount}
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL],
        fail_silently=False,
    )


    # -------------------------
    # Customer HTML Email
    # -------------------------
    context = {
        "order": order,
        "items": order.items.select_related("subcategory"),
        "order_summary": order_summary,
    }

    html_content = render_to_string(
        "order_confirmation.html",
        context,
    )

    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=f"Thank you for your order #{order.id}",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.profile.email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()

@login_required
def checkout(request):

    # User should only arrive here from order.html
    if request.method != "POST":
        return redirect("core:order")

    name = request.POST.get("name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    description = request.POST.get("description", "").strip()
    # attachments = request.FILES.getlist("attachments")

    raw_items = request.POST.get("items", "[]")

    try:
        items = json.loads(raw_items)
    except json.JSONDecodeError:
        messages.error(request, "Invalid order.")
        return redirect("core:order")

    checkout_items = []
    grand_total = Decimal("0.00")

    for item in items:

        try:
            sub_id, qty = item.split("|")
            qty = int(qty)

            if qty < 1:
                continue

            sub = PortfolioSubCategory.objects.select_related(
                "category"
            ).get(pk=sub_id)

        except Exception:
            continue

        line_total = sub.price * qty

        checkout_items.append({
            "subcategory_id": sub.id,
            "category": sub.category.name,
            "subcategory": sub.name,
            "quantity": qty,
            "price": str(sub.price),
            "total": str(line_total),
        })

        grand_total += line_total

    if not checkout_items:
        messages.error(request, "Please add at least one service.")
        return redirect("core:order")

    # Save checkout data in session
    request.session["checkout"] = {

        "customer": {
            "name": name,
            "email": email,
            "phone": phone,
            "description": description,
        },

        "items": checkout_items,

        "total": str(grand_total),
    }

    return render(
        request,
        "checkout.html",
        {
            "customer": request.session["checkout"]["customer"],
            "items": checkout_items,
            "total": grand_total,
        },
    )


def easypay_result(request):

    status = request.GET.get("status")
    desc = request.GET.get("desc")
    order_ref = request.GET.get("orderRefNumber")

    if not order_ref:
        return render(
            request,
            "success.html",
            {
                "payment_status": "failed",
                "message": (
                    "Easypaisa did not return "
                    "an order reference."
                ),
            },
            status=400,
        )

    order = Order.objects.filter(
        easypay_order_ref=order_ref
    ).first()

    if not order:
        return render(
            request,
            "success.html",
            {
                "payment_status": "failed",
                "message": (
                    "We could not find the "
                    "corresponding order."
                ),
            },
            status=404,
        )

    if status == "Success":

        if order.payment_status != "paid":

            order.payment_status = "paid"
            order.save(
                update_fields=["payment_status"]
            )

            send_order_emails(order)

        return redirect(
            "core:payment_success",
            order_id=order.id,
        )

    # Any non-success result
    if order.payment_status != "paid":

        order.payment_status = "failed"
        order.save(
            update_fields=["payment_status"]
        )

    return render(
        request,
        "success.html",
        {
            "payment_status": "failed",
            "order": order,
            "message": (
                "Your Easypaisa payment was "
                "not completed."
            ),
            "payment_description": desc,
        },
    )


def easypay_callback(request):

    auth_token = request.GET.get("auth_token")

    if not auth_token:
        return render(
            request,
            "success.html",
            {
                "payment_status": "failed",
                "message": (
                    "Easypaisa did not return "
                    "an authentication token."
                ),
            },
            status=400,
        )

    return render(
        request,
        "easypay_confirm.html",
        {
            "auth_token": auth_token,
            "easypay_confirm_url": settings.EASYPAY_CONFIRM_URL,
            "post_back_url": (
                "https://www.zafium.com/"
                "payment/easypay/result/"
            ),
        },
    )


def easypay_start(request, order_id):

    order = get_object_or_404(
        Order.objects.select_related("user"),
        pk=order_id,
    )

    # Don't allow already-paid orders to start
    # another payment.
    if order.payment_status == "paid":
        return redirect(
            "core:payment_success",
            order_id=order.id,
        )

    email = order.user.email
    phone = order.user.profile.phone

    print(email)
    print(phone)

    # Generate an expiry time.
    expiry_date = (
        timezone.now() + timedelta(minutes=340)
    ).strftime("%Y%m%d %H%M%S")

    # Easypaisa requires amount with ONE decimal
    # place for merchantHashedReq.
    amount = f"{order.total_amount:.1f}"

    post_back_url = request.build_absolute_uri(
        "/payment/easypay/callback/"
    )

    payment_method = "CC_PAYMENT_METHOD"

    hash_fields = {
        "amount": amount,
        "storeId": str(settings.EASYPAY_STORE_ID),
        "autoRedirect": "0",
        "orderRefNum": order.easypay_order_ref,
        "expiryDate": expiry_date,
        "postBackURL": post_back_url,
    }

    merchant_hashed_req = generate_easypay_hash(
        hash_fields
    )

    print(merchant_hashed_req)

    return render(
        request,
        "easypay_redirect.html",
        {
            "easypay_url": settings.EASYPAY_INDEX_URL,

            "store_id":
                settings.EASYPAY_STORE_ID,

            "amount": amount,

            "post_back_url":
                post_back_url,

            "order_ref_num":
                order.easypay_order_ref,

            "expiry_date":
                expiry_date,

            "merchant_hashed_req":
                merchant_hashed_req,

            "auto_redirect": "0",

            "payment_method":
                payment_method,

            "email": email,
            "phone": phone,
        },
    )


def place_order(request):

    if request.method != "POST":
        return redirect("core:order")

    checkout = request.session.get("checkout")

    if not checkout:
        messages.error(request, "Your checkout session has expired.")
        return redirect("core:order")

    customer = checkout["customer"]
    items = checkout["items"]

    payment_method = request.POST.get("payment_method")

    if not payment_method:
        messages.error(request, "Please select a payment method.")
        return redirect("core:checkout")

    name=customer["name"]
    email=customer["email"]
    phone=customer["phone"]
    description = request.POST.get("description", "").strip()
    attachments = request.FILES.getlist("attachments")
    payment_method=payment_method


    order = Order.objects.create(
        user=request.user,
        payment_method=payment_method,
        description=description,
    )

    order.easypay_order_ref = f"ZAF-{order.id}-{uuid.uuid4().hex[:12].upper()}"

    for attachment in attachments:
        OrderAttachment.objects.create(
            order=order,
            file=attachment
        )

    # Create Order Items
    for item in items:

        sub = PortfolioSubCategory.objects.select_related(
            "category"
        ).get(pk=item["subcategory_id"])

        OrderItem.objects.create(
            order=order,
            category=sub.category,
            subcategory=sub,
            quantity=item["quantity"],
            price=item["price"],
        )

    request.session["order_id"] = order.id

    order.save()

    return redirect(
        "core:easypay_start",
        order_id=order.id,
    )


def payment_success(request):

    """
    order = get_object_or_404(Order, pk=order_id)

    order.payment_status = "paid"
    order.save()

    send_order_emails(order)
    """

    return redirect("core:success_page")

# ____________________________________________________________________________________________________________

MEDIA_ROOT='media'
os.makedirs(MEDIA_ROOT,exist_ok=True)

def layerforge(request):
    return render(request,'layerforge/layerforge.html')

@csrf_exempt
def generate_svg(request):

    
    if not consume_project_usage(request, "layerforge"):
        return HttpResponse(
            "daily_limit_reached",
            content_type="text/plain",
            status=429
        )

    try:
        uploaded = request.FILES["image"]

        file_name = uploaded.name

        edge_detection_threshold = int(request.POST.get("edge_detection_threshold", 10))
        min_anchor_distance = int(request.POST.get("min_anchor_distance", 15))

        # Decode image directly from memory
        """
        image_bytes = np.frombuffer(uploaded.read(), np.uint8)
        img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        """
        uploaded.seek(0)
        image_bytes = np.frombuffer(
            uploaded.read(),
            np.uint8
        )

        img = cv2.imdecode(
            image_bytes,
            cv2.IMREAD_COLOR
        )

        if img is None:
            raise ValueError(
                "OpenCV could not decode the uploaded image."
            )

        img = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2RGB
        )
        svg_text = _img_array_to_svg(
            img,
            edge_detection_threshold=edge_detection_threshold,
            min_anchor_distance=min_anchor_distance,
        )

        filename = "_".join(str(file_name).split(".")[:-1])
        filename = filename+"_layerforged.svg"

        return HttpResponse(svg_text, content_type="image/svg+xml")
    except Exception as e:
        print(e)
        with open("templates/layerforge/sorry.html", "r", encoding="utf-8") as f:
            html = f.read()
        return HttpResponse(html, content_type="text/html", status=400)

# _______________________________________________________________________________________________________________

def autolytics(request):
    return render(request,'autolytics/autolytics.html')

def autolytics_search(request):

    print("Search called")

    mm = request.GET.get("make")
    mn = request.GET.get("model")
    ct = request.GET.get("city")

    if not any([mm, mn, ct]):
        return render(request, "sorry.html")

    if request.method == 'GET':
        make = request.GET.get('make')
        model = request.GET.get('model')
        city = request.GET.get('city')

        if make is not None and model is not None and city is not None:

            # Check and consume Autolytics quota
            if not consume_project_usage(request, "autolytics"):
                return render(
                    request,
                    "autolytics/autolytics.html",
                    {
                        "usage_limit_exceeded": True
                    },
                    status=429
                )

            data = get_data_pw(mm, mn, ct)

        else:
            data = None
    if data is None:
        return render(request, "sorry.html")

    try:
        # data['price'].apply(get_int)
        # data['year'].apply(get_int)
        data = [(get_int(y), get_int(p)) for y, p in data]
        mm = mm.strip().capitalize()
        mn = mn.strip().capitalize()
        ct = ct.strip().capitalize()
        tit = mm + " " + mn + " (" + ct + ")"

        # Formatting data for bar plot
        # fory = data['year'].value_counts()[:]

        sp = subplots.make_subplots(
                    rows=3,
                    cols=1,
                    subplot_titles=['Price_Scatter', 'Quantity_Bars', 'Detail Bars'],
                    specs=[[{"type": "xy"}],
                        [{"type": "xy"}],
                        [{"type": "polar"}]]
                )

        # x_vals = data['year']
        # y_vals = data['price']

        x_vals = [y for y, _ in data]
        y_vals = [p for _, p in data]

        fory = Counter(x_vals)

        n = len(x_vals)

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        den = sum((x - x_mean) ** 2 for x in x_vals)

        slope = num / den
        intercept = y_mean - slope * x_mean

        best_fit_line = [slope * x + intercept for x in x_vals]

        sp.add_trace(go.Scatter(x=x_vals,
                                y=y_vals,
                                name="Each Available "+mn+" Price",
                                mode='markers',
                                marker={'color': 'tomato', 'size': 12},
                                hovertemplate="<br>".join([
                                    "year: %{x}",
                                    "price: "+"%{y}",
                                ]),
                                hoverlabel={'font': {'color': 'white'}}
                            ),
                        row=1,
                        col=1
                    )
        sp.add_trace(go.Line(x=x_vals,
                                y=best_fit_line,
                                name="Linear Increment",
                                mode='lines',
                                line=dict(color='royalblue'),
                                hoverinfo='skip',
                                hovertemplate="<br>".join([
                                    "year: %{x}",
                                    "price: "+"%{y}",
                                ]),
                            hoverlabel={'font': {'color': 'white'}}
                            ),
                        row=1,
                        col=1
                    )
        x_ = sorted(fory.keys())
        y_ = [fory[k] for k in x_]
        sp.add_trace(go.Bar(x=x_,
                            y=y_,
                            name="No. of "+mn+" for sale per year",
                            marker={'color': 'tomato'},
                            hovertemplate="<br>".join([
                                    "year: %{x}",
                                    f"No. of {mn} found: "+"%{y}",
                                ]),
                                hoverlabel={'font': {'color': 'white'}}
                        ),
                        row=2,
                        col=1
                    )

        # Formatting data for C_bar
        """
        grouped_data = data.groupby(['year'])
        gd_min_price = grouped_data.min().reset_index()['price'].tolist()
        gd_max_price = grouped_data.max().reset_index()['price'].tolist()
        gd_years = grouped_data.mean().reset_index()['year'].tolist()
        gd_mean_price = grouped_data.mean().reset_index()['price'].round(2).tolist()
        """
        grouped = defaultdict(list)
        for year, price in data:
            grouped[year].append(price)

        gd_years = sorted(grouped.keys())

        gd_min_price = [min(grouped[y]) for y in gd_years]
        gd_max_price = [max(grouped[y]) for y in gd_years]
        gd_mean_price = [
            round(sum(grouped[y]) / len(grouped[y]), 2)
            for y in gd_years
        ]

        sp.add_trace(
                go.Barpolar(r=gd_min_price,
                            name='Min Price Per Year',
                            marker_color='rgb(255, 170, 51)',
                            text=gd_years,
                            hovertemplate="<br>".join([
                                    "year: %{text}",
                                    "min_price: %{r}",
                                ]),
                            hoverlabel={'font': {'color': 'white'}}
                        ),
                row=3,
                col=1,
            )

        sp.add_trace(
                go.Barpolar(r=gd_mean_price,
                            name='Mean Price Per Year',
                            marker_color='rgb(236, 88, 0)',
                            text=gd_years,
                            hovertemplate="<br>".join([
                                    "year: %{text}",
                                    "mean_price: %{r}",
                                ]),
                            hoverlabel={'font': {'color': 'white'}}
                        ),
                row=3,
                col=1,
        )

        sp.add_trace(
                go.Barpolar(r=gd_max_price,
                            marker_color='rgb(139, 64, 0)',
                            name='Max Price Per Year',
                            text=gd_years,
                            hovertemplate="<br>".join([
                                    "year: %{text}",
                                    "max_price: %{r}",
                                ]),
                            hoverlabel={'font': {'color': 'white'}}
                        ),
                row=3,
                col=1,
        )

        sp.update_layout({
            'plot_bgcolor': 'rgba(2, 6, 23, 0)',   # transparent
            'paper_bgcolor': 'rgba(15, 23, 42, 0)',  # matches card
            'font_color': '#e5e7eb',
            'font_size': 15,
            'autosize': True,
            'height': 1800,
            'title': tit,
            'polar_bgcolor': 'rgba(79, 83, 88, 0.4)',
            'polar_angularaxis_visible': False,
            'polar_angularaxis_showticklabels': True,
            'polar_angularaxis_ticks': "",
            'polar_radialaxis_ticks': None,
            'polar_radialaxis_visible': False,
            'polar_radialaxis_showticklabels': False,
        })

        sp.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )

        prc = [p for _, p in data if p is not None]
        plot_div = plot({'data': sp}, output_type='div')
        min_price = int(min(prc))
        avg_price = int(sum(prc) / len(prc))
        max_price = int(max(prc))
        mini = millify(min_price)
        price = millify(avg_price)
        maxi = millify(max_price)
        return render(request, "autolytics/results/autolytics_results.html", context={
            "plot_div": plot_div,
            "avg_price": price,
            "min_price": mini,
            "max_price": maxi,
        })
    except Exception as e:
        print(e)
        return render(request, "autolytics/results/sorry.html")
