from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import send_mail

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from django.conf import settings
from django.http import HttpResponse
from django.contrib import messages
from decimal import Decimal

from django.http import JsonResponse
import json
from django.template.loader import render_to_string

from django.views.decorators.csrf import csrf_exempt
import os,uuid
from .utils import _img_array_to_svg
from .models import PortfolioItem, PortfolioCategory, PortfolioSubCategory, Order, OrderItem, OrderReview, Client

from django.views.decorators.http import require_POST

from .forms import ContactForm
from .helpers import send_contact_email

import cv2
import numpy as np
from collections import defaultdict, Counter
from plotly.offline import plot
from .api_call import get_data_pw, millify
from plotly import subplots
import plotly.graph_objs as go

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


def contact(request):

    if request.method == "POST":

        form = ContactForm(request.POST)

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
            "order__client",
        )
        .filter(
            approved=True,
        )
        .order_by("-order__created_at")
    )

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

# ____________________________________________________________________________________________________________

def dashboard(request, token):

    client = get_object_or_404(
        Client,
        access_token=token
    )

    orders = (
        client.orders
        .prefetch_related(
            "items__subcategory",
            "review"
        )
        .order_by("-created_at")
    )

    order_id = request.GET.get("order_id")

    orders = Order.objects.filter(client=client)

    if order_id:
        orders = orders.filter(id=order_id)

    if not orders.exists():
        raise Http404("Dashboard not found.")

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
            "client": client,
            "orders": orders,
            "active_orders": active_orders,
            "completed_orders": completed_orders,
            "dashboard_token": client.access_token,
        }
    )


def order_detail(request, token, order_id):

    client = get_object_or_404(
        Client,
        access_token=token
    )

    order = get_object_or_404(
        client.orders.prefetch_related(
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
            "client": client,
            "order": order,
            "dashboard_token": client.access_token,
        }
    )


@require_POST
def submit_review(request, token, order_id):

    client = get_object_or_404(
        Client,
        access_token=token
    )

    order = get_object_or_404(
        client.orders,
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
            token=client.access_token,
            order_id=order.id
        )

    if hasattr(order, "review"):
        messages.warning(
            request,
            "You have already reviewed this project."
        )

        return redirect(
            "core:order_detail",
            token=client.access_token,
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
        token=client.access_token,
        order_id=order.id
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

    client = order.client

    order_summary = ""

    for item in order.items.select_related("subcategory"):
        order_summary += (
            f"{item.subcategory.name} "
            f"x {item.quantity} "
            f"= ${item.total_price()}\n"
        )

    # -------------------------
    # Admin Email
    # -------------------------
    send_mail(
        subject=f"New Order #{order.id}",
        message=f"""
        New Order Received

        Client: {client.name}
        Email: {client.email}
        Phone: {client.phone}

        Items:

        {order_summary}

        Status:
        {order.get_project_status_display()}

        Progress:
        {order.progress}%

        Total:
        ${order.total_amount}
        
        Client Access Token: { client.access_token }
        Client Dashboard URL: https://www.zafium.com/dashboard/{ client.access_token }/
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
        to=[client.email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()


def checkout(request):

    # User should only arrive here from order.html
    if request.method != "POST":
        return redirect("core:order")

    name = request.POST.get("name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")

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
    payment_method=payment_method

    client, _ = Client.objects.get_or_create(
        email=email,
        defaults={
            "name": name,
            "phone": phone,
        }
    )

    order = Order.objects.create(
        client=client,
        payment_method=payment_method,
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

    del request.session["checkout"]

    return redirect(
        "core:payment_success",
        order_id=order.id
    )


def payment_success(request, order_id):

    order = get_object_or_404(Order, pk=order_id)

    order.payment_status = "paid"
    order.save()

    send_order_emails(order)

    return redirect("core:success_page")

# ____________________________________________________________________________________________________________

MEDIA_ROOT='media'
os.makedirs(MEDIA_ROOT,exist_ok=True)

def layerforge(request):
    return render(request,'layerforge/layerforge.html')

@csrf_exempt
def generate_svg(request):
    try:
        uploaded = request.FILES["image"]

        k_min = int(request.POST.get("k_min", 3))
        k_max = int(request.POST.get("k_max", 15))
        cluster_scale = float(request.POST.get("cluster_scale", 0.5))
        min_area_ratio = float(request.POST.get("min_area_ratio", 0.0003))
        smooth = request.POST.get("smooth") == "true"

        # Decode image directly from memory
        image_bytes = np.frombuffer(uploaded.read(), np.uint8)
        img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        svg_text = _img_array_to_svg(
            img,
            K_MIN=k_min,
            K_MAX=k_max,
            CLUSTER_SCALE=cluster_scale,
            MIN_AREA_RATIO=min_area_ratio,
            smooth=smooth
        )

        return HttpResponse(svg_text, content_type="image/svg+xml")
    except:
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
