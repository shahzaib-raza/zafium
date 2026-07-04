from .models import PortfolioItem, PortfolioCategory

def portfolio_categories(request):
    return {
        "portfolio_categories": PortfolioCategory.objects.all()
    }