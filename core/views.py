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
from .models import PortfolioItem, PortfolioCategory, PortfolioSubCategory, Order, OrderItem
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

# ____________________________________________________________________________________________________________

def success_page(request):
    return render(request, "success.html")


def create_order(request):

    print("METHOD:", request.method)
    print("POST:", request.POST)

    categories = PortfolioCategory.objects.prefetch_related("subcategories")

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")

        order = Order.objects.create(
            name=name,
            email=email,
            phone=phone
        )

        items = json.loads(request.POST.get("items", "[]"))

        order_summary = ""

        for item in items:
            # format: subcategory_id|quantity
            sub_id, qty = item.split("|")

            sub = PortfolioSubCategory.objects.get(id=sub_id)

            order_item = OrderItem.objects.create(
                order=order,
                category=sub.category,
                subcategory=sub,
                quantity=int(qty),
                price=sub.price
            )

            order_summary += f"{sub.name} x {qty} = {order_item.total_price()}\n"

        # ✅ SEND EMAIL HERE (AFTER LOOP)
        send_mail(
            subject=f"New Order #{order.id}",
            message=f"""
                New Order Received

                Client: {name}
                Email: {email}
                Phone: {phone}

                Items:
                {order_summary}

                Total: {order.total_amount()}
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=False
        )

        send_mail(
            subject=f"Thank you for your order #{order.id}",
            message=f"""
                Hi {name},

                Thank you for placing your order with us.

                We have successfully received your request and our team will start processing it shortly.

                -------------------------
                ORDER DETAILS
                -------------------------

                Order ID: #{order.id}

                Items:
                {order_summary}

                Total: {order.total_amount()}

                We will contact you soon if we need any further details.

                If you have any questions, feel free to reply to this email.

                Best regards,  
                Team zafium
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )

        return redirect("core:success_page")

    return render(request, "order.html", {
        "categories": categories
    })


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

    # Create Order
    order = Order.objects.create(
        name=customer["name"],
        email=customer["email"],
        phone=customer["phone"],
        payment_method=payment_method,
        payment_status="pending",
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

    # Store order id in session
    request.session["order_id"] = order.id

    # Clear checkout session
    del request.session["checkout"]

    # Redirect according to payment method

    if payment_method == "card":
        return redirect("core:payment_success", order_id=order.id)

    elif payment_method == "paypal":
        return redirect("core:payment_success", order_id=order.id)

    elif payment_method == "jazzcash":
        return redirect("core:payment_success", order_id=order.id)

    elif payment_method == "easypaisa":
        return redirect("core:payment_success", order_id=order.id)

    elif payment_method == "bank":
        return redirect("core:payment_success", order_id=order.id)

    messages.error(request, "Invalid payment method.")
    return redirect("core:checkout")


def payment_success(request, order_id):

    order = get_object_or_404(Order, pk=order_id)

    order.payment_status = "paid"
    order.save()

    order_summary = ""

    for item in order.items.all():
        order_summary += (
            f"{item.subcategory.name} "
            f"x {item.quantity} "
            f"= ${item.total_price()}\n"
        )

    # Admin email
    send_mail(
        subject=f"New Paid Order #{order.id}",
        message=f"""
    New Paid Order

    Customer:
    {order.name}

    Email:
    {order.email}

    Phone:
    {order.phone}

    Items:

    {order_summary}

    Total:
    ${order.total_amount}
    """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL],
        fail_silently=False,
    )

    # Customer email
    context = {
        "order": order,
        "order_summary": order_summary,
    }

    html_message = render_to_string(
        "order_confirmation.html",
        context,
    )

    plain_message = strip_tags(html_message)

    email = EmailMultiAlternatives(
        subject=f"Payment Received • Order #{order.id}",
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
    )

    email.attach_alternative(html_message, "text/html")
    email.send()

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
