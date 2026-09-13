from .models import PortfolioItem, PortfolioCategory
from .helpers import get_usd_to_pkr_rate_per_day

def portfolio_categories(request):
    return {
        "portfolio_categories": PortfolioCategory.objects.all()
    }

def currency(request):

    selected_currency = request.COOKIES.get(
        "zafium_currency",
        "USD"
    )

    if selected_currency not in ["USD", "PKR"]:
        selected_currency = "USD"

    rate = get_usd_to_pkr_rate_per_day()

    return {
        "site_currency": selected_currency,
        "usd_to_pkr_rate": rate,
        "currency_data": {
            "currency": selected_currency,
            "rate": rate,
        },
    }