from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PortfolioSitemap(Sitemap):
    protocol = "https"
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            "ai",
            "web-development",
            "Design",
            "automation",
            "research",
            'data-scraping',
            'video',
            'training',
        ]

    def location(self, item):
        return reverse(
            "core:portfolio_category",
            kwargs={"category": item},
        )

class StaticViewSitemap(Sitemap):

    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            'core:home',
            'core:about',
            'core:services',
            'core:order',
            'core:layerforge',
            'core:autolytics',
            'core:contact',
            'core:orders_activity',
            'core:privacy_policy',
            'core:terms_of_service',
            'core:refund_policy',
            'core:pricing',
        ]

    def location(self, item):
        return reverse(item)