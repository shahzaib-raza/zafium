from django.contrib import admin
from django.utils import timezone

from .models import (
    UserProfile,
    ProjectUsageSettings,
    ProjectUsage,
    PortfolioItem,
    PortfolioMedia,
    PortfolioCategory,
    PortfolioSubCategory,
    Order,
    OrderItem,
    OrderReview,
    OrderDelivery,
    OrderRevision,
    OrderAttachment,
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

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email",
        "plan",
        "phone",
        "country",
        "company",
        "created_at",
    )

    list_filter = (
        "plan",
        "country",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "phone",
        "company",
    )

    readonly_fields = (
        "created_at",
    )

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email

@admin.register(ProjectUsageSettings)
class ProjectUsageSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "free_daily_limit",
        "paid_daily_limit",
        "updated_at",
    )

    readonly_fields = (
        "updated_at",
    )

    def has_add_permission(self, request):
        # Only allow one settings record
        return not ProjectUsageSettings.objects.exists()


@admin.register(ProjectUsage)
class ProjectUsageAdmin(admin.ModelAdmin):
    list_display = (
        "identity_key",
        "project",
        "date",
        "count",
    )

    list_filter = (
        "project",
        "date",
    )

    search_fields = (
        "identity_key",
        "project",
    )

    readonly_fields = (
        "identity_key",
        "project",
        "date",
        "count",
    )

    ordering = (
        "-date",
        "-count",
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "category", "subcategory", "quantity", "price", "total_price")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


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
        "visible_to_user",
        "uploaded_at",
    )

    readonly_fields = (
        "uploaded_at",
    )

class OrderAttachmentInline(admin.TabularInline):
    model = OrderAttachment
    extra = 0
    readonly_fields = ("uploaded_at",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "project_status",
        "progress",
        "payment_status",
        "easypay_order_ref",
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
        "easypay_order_ref",
    )

    search_fields = (
        "user__name",
        "user__email",
        "user__phone",
        "easypay_order_ref",
    )

    autocomplete_fields = (
        "user",
    )

    readonly_fields = (
        "created_at",
        "total_amount",
    )

    fieldsets = (
        (
            "Order Information",
            {
                "fields": (
                    "user",
                    "description",
                )
            },
        ),
        (
            "Internal Admin Notes",
            {
                "fields": (
                    "notes",
                )
            },
        ),
        (
            "Project Status",
            {
                "fields": (
                    "project_status",
                    "progress",
                    "latest_update",
                    "estimated_delivery",
                    "completed_at",
                )
            },
        ),
        (
            "Payment",
            {
                "fields": (
                    "payment_method",
                    "payment_status",
                    "easypay_order_ref",
                    "transaction_id",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "total_amount",
                )
            },
        ),
    )

    inlines = [
        OrderItemInline,
        OrderDeliveryInline,
        OrderAttachmentInline,
    ]

    def __str__(self):
        return f"Order #{self.id} - {self.user.name} "
    

@admin.register(OrderDelivery)
class OrderDeliveryAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "order",
        "visible_to_user",
        "uploaded_at",
    )

    list_filter = (
        "visible_to_user",
        "uploaded_at",
    )

    search_fields = (
        "title",
        "order__id",
        "order__user__name",
        "order__user__email",
    )


@admin.register(OrderRevision)
class OrderRevisionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "user",
        "status",
        "created_at",
        "resolved_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "order__id",
        "order__user__name",
        "order__user__email",
        "message",
    )

    readonly_fields = (
        "created_at",
    )

    autocomplete_fields = (
        "order",
    )

    fieldsets = (

        (
            "Revision",
            {
                "fields": (
                    "order",
                    "status",
                    "message",
                )
            },
        ),

        (
            "Dates",
            {
                "fields": (
                    "created_at",
                    "resolved_at",
                )
            },
        ),

    )

    def user(self, obj):
        return obj.order.user.name

    user.short_description = "UserProfile"

    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        if obj.status == Order.ProjectStatus.DELIVERED:

            obj.revisions.filter(
                status=OrderRevision.Status.PENDING
            ).update(
                status=OrderRevision.Status.COMPLETED,
                resolved_at=timezone.now(),
            )