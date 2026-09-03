from django.urls import path
from .views import *

app_name = "core"

urlpatterns = [
    path("", home, name="home"),

    path(
        'layerforge/',
        layerforge,
        name='layerforge'
    ),

    path('generate/', generate_svg),

    path(
        'autolytics/',
        autolytics,
        name='autolytics'
    ),

    path(
        'autolytics/results/',
        autolytics_search,
        name='autolytics_search'
    ),

    path(
        'services/',
        services,
        name='services'
    ),

    path(
        'about/',
        about,
        name='about'
    ),

    path(
        "portfolio/<slug:category>/",
        portfolio_category,
        name="portfolio_category"
    ),

    path(
        "portfolio/<slug:category>/<slug:slug>/",
        portfolio_detail,
        name="portfolio_detail"
    ),

    path(
        "contact/",
        contact,
        name="contact",
    ),

    path(
        "order/",
        order,
        name="order",
    ),

    path(
        "live-activity/",
        orders_activity,
        name="orders_activity",
    ),

    path(
        "pricing/",
        pricing,
        name="pricing",
    ),

    path(
        "privacy-policy/",
        privacy_policy,
        name="privacy_policy",
    ),

    path(
        "terms-of-service/",
        terms_of_service,
        name="terms_of_service",
    ),

    path(
        "refund-policy/",
        refund_policy,
        name="refund_policy",
    ),

    path("checkout/", checkout, name="checkout"),

    path("place-order/", place_order, name="place_order"),

    path(
        "payment/easypay/start/<int:order_id>/",
        easypay_start,
        name="easypay_start",
    ),

    path(
        "payment/easypay/callback/",
        easypay_callback,
        name="easypay_callback",
    ),

    path(
        "payment/easypay/result/",
        easypay_result,
        name="easypay_result",
    ),

    path(
        "order/success/<int:order_id>/",
        payment_success,
        name="payment_success",
    ),

    path(
        "success/",
        success_page,
        name="success_page",
    ),

    path("robots.txt", robots_txt),

    path(
        "dashboard/",
        dashboard,
        name="dashboard"
    ),

    path(
        "dashboard/order/<int:order_id>/",
        order_detail,
        name="order_detail"
    ),

    path(
        "dashboard/order/<int:order_id>/review/",
        submit_review,
        name="submit_review"
    ),

    path(
        "dashboard/order/<int:order_id>/revision/",
        request_revision,
        name="request_revision",
    ),

    path("signup/", signup, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path(
        "verify/<uidb64>/<token>/",
        verify_email,
        name="verify_email",
    ),
    path("account/", account, name="account"),
    
]