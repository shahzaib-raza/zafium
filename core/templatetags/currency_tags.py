from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def display_price(value, currency_data):

    if value is None:
        return "0"

    value = Decimal(str(value))

    currency = currency_data["currency"]
    rate = Decimal(str(currency_data["rate"]))

    if currency == "PKR":
        converted = value * rate
        return f"₨{converted:,.0f}"

    return f"${value:,.2f}"