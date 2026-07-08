from django.contrib import admin

from .models import (
    Client,
    PortfolioItem,
    PortfolioMedia,
    PortfolioCategory,
    PortfolioSubCategory,
    Order,
    OrderItem,
    OrderReview,
    OrderDelivery,
)

class PortfolioMediaInline(admin.TabularInline):
    model = PortfolioMedia
    extra = 1


@admin.register(PortfolioCategory)
class PortfolioCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(PortfolioSubCategory)
class PortfolioSubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "email",
        "phone",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "phone",
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "category", "subcategory", "quantity", "price", "total_price")


@admin.register(OrderReview)
class OrderReviewAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "rating",
        "approved",
        "created_at",
    )

    list_filter = (
        "rating",
        "approved",
    )

    search_fields = (
        "order__name",
        "order__email",
        "title",
    )

    list_editable = (
        "approved",
    )


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "category",
        "featured",
        "cover_ratio"
    )

    prepopulated_fields = {
        "slug": ("title",)
    }

    inlines = [
        PortfolioMediaInline
    ]

class OrderDeliveryInline(admin.TabularInline):
    model = OrderDelivery
    extra = 1

    fields = (
        "title",
        "file",
        "visible_to_client",
        "uploaded_at",
    )

    readonly_fields = (
        "uploaded_at",
    )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "client",
        "project_status",
        "progress",
        "payment_status",
        "created_at",
        "total_amount",
    )

    list_editable = (
        "project_status",
        "progress",
        "payment_status",
    )

    list_filter = (
        "project_status",
        "payment_status",
        "created_at",
    )

    search_fields = (
        "client__name",
        "client__email",
        "client__phone",
    )

    autocomplete_fields = (
        "client",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = [
        OrderDeliveryInline,
    ]

    def __str__(self):
        return f"Order #{self.id} - {self.client.name} "
    

@admin.register(OrderDelivery)
class OrderDeliveryAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "order",
        "visible_to_client",
        "uploaded_at",
    )

    list_filter = (
        "visible_to_client",
        "uploaded_at",
    )

    search_fields = (
        "title",
        "order__id",
        "order__client__name",
        "order__client__email",
    )