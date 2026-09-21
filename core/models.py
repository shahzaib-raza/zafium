from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
import uuid
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from django.db.models import Q

# Create your models here.


class PortfolioCategory(models.Model):
    class CategoryChoices(models.TextChoices):
        DESIGN = "Design", "Design"
        DATA_SCRAPING = "Data Scraping", "Data Scraping"
        RESEARCH = "Research", "Research"
        DATA_ENTRY = "Data Entry", "Data Entry"
        AUTOMATION = "Automation", "Automation"
        AI = "AI", "AI"
        WEB_DEV = "Web Development", "Web Development"
        VIDEO = "Video", "Video"
        TRAINING = "Training & Education", "Training & Education"

    name = models.CharField(max_length=50, choices=CategoryChoices.choices)

    slug = models.SlugField(unique=True)

    icon = models.CharField(
        max_length=5000,
        blank=True
    )

    def __str__(self):
        return self.name


class PortfolioSubCategory(models.Model):
    category = models.ForeignKey(
        PortfolioCategory,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )

    name = models.CharField(max_length=100)
    slug = models.SlugField()

    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} → {self.name}"


ASPECT_RATIO_CHOICES = [
    ("1/1", "Square (1:1)"),
    ("4/3", "Standard (4:3)"),
    ("3/2", "Photo (3:2)"),
    ("16/9", "Widescreen (16:9)"),
    ("21/9", "Ultra Wide (21:9)"),
    ("4/5", "Portrait (4:5)"),
    ("9/16", "Vertical (9:16)"),
    ("1.91/1", "Social Banner (1.91:1)"),
    ("1/1.414", "A4 Document"),
]


class PortfolioItem(models.Model):

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    category = models.ForeignKey(
        "PortfolioCategory",
        on_delete=models.CASCADE
    )

    subcategory = models.ForeignKey(
        PortfolioSubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects"
    )

    cover_ratio = models.CharField(
        max_length=20,
        choices=ASPECT_RATIO_CHOICES,
        default="16:9",
        help_text="Select the layout type (e.g., 16:9 for videos, 1:1 for logos)"
    )

    short_description = models.CharField(max_length=300)
    description = models.TextField()

    featured = models.BooleanField(default=False)

    cover_image = models.ImageField(upload_to="portfolio/covers/")

    live_url = models.URLField(blank=True)
    publication_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class PortfolioMedia(models.Model):

    IMAGE = "image"
    VIDEO = "video"

    MEDIA_CHOICES = [
        (IMAGE, "Image"),
        (VIDEO, "Video")
    ]

    portfolio = models.ForeignKey(
        PortfolioItem,
        on_delete=models.CASCADE,
        related_name="media"
    )

    media_type = models.CharField(
        max_length=20,
        choices=MEDIA_CHOICES
    )

    image = models.ImageField(
        upload_to="portfolio/images/",
        blank=True
    )

    video = models.FileField(
        upload_to="portfolio/videos/",
        blank=True
    )

    caption = models.CharField(
        max_length=200,
        blank=True
    )

    aspect_ratio = models.CharField(
        max_length=20,
        choices=ASPECT_RATIO_CHOICES,
        default="16:9",
        help_text="Select the layout type (e.g., 16:9 for videos, 1:1 for logos)"
    )

    def __str__(self):
        return f"{self.portfolio.title} - {self.media_type}"


class SaaSProduct(models.Model):
    """
    A Zafium SaaS product such as LayerForge or Autolytics.
    """

    name = models.CharField(
        max_length=100
    )

    slug = models.SlugField(
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    free_daily_limit = models.PositiveIntegerField(
        default=5,
        validators=[
            MinValueValidator(1)
        ],
        help_text="Daily usage limit for free users."
    )

    usage_unit = models.CharField(
        max_length=50,
        default="uses",
        help_text="Unit shown to users, e.g. images, searches, requests.",
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SaaSPlan(models.Model):
    """
    A paid monthly plan belonging to a SaaS product.

    Example:

    LayerForge
        Starter -> 20/day -> $5
        Growth  -> 50/day -> $10
        Pro     -> 100/day -> $20
    """

    product = models.ForeignKey(
        SaaSProduct,
        on_delete=models.CASCADE,
        related_name="plans"
    )

    name = models.CharField(
        max_length=100
    )

    daily_limit = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1)
        ],
        help_text="Maximum number of operations allowed per day."
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ]
    )

    currency = models.CharField(
        max_length=3,
        choices=[
            ("USD", "USD"),
            ("PKR", "PKR"),
        ],
        default="USD"
    )

    billing_period_days = models.PositiveIntegerField(
        default=30,
        validators=[
            MinValueValidator(1)
        ],
        help_text="Number of days this plan remains active."
    )

    is_active = models.BooleanField(
        default=True
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "product",
            "sort_order",
            "price",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"],
                name="unique_saas_plan_name_per_product"
            ),
        ]

        indexes = [
            models.Index(
                fields=["product", "is_active"]
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class SaaSSubscription(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saas_subscriptions"
    )

    product = models.ForeignKey(
        SaaSProduct,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    plan = models.ForeignKey(
        SaaSPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # Snapshot of the purchased plan
    daily_limit = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1)
        ]
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ]
    )

    currency = models.CharField(
        max_length=3,
        choices=[
            ("USD", "USD"),
            ("PKR", "PKR"),
        ],
        default="USD"
    )

    billing_period_days = models.PositiveIntegerField(
        default=30,
        validators=[
            MinValueValidator(1)
        ]
    )

    # Subscription period
    start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "product",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "end_date",
                    "status",
                ]
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(daily_limit__gt=0),
                name="saas_subscription_daily_limit_gt_zero"
            ),
            models.CheckConstraint(
                condition=Q(billing_period_days__gt=0),
                name="saas_subscription_billing_days_gt_zero"
            ),
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name="saas_subscription_price_gte_zero"
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.product.name} - "
            f"{self.plan.name}"
        )

    @property
    def is_active(self):
        if self.status != self.Status.ACTIVE:
            return False

        if not self.start_date or not self.end_date:
            return False

        now = timezone.now()

        return self.start_date <= now < self.end_date

    @property
    def remaining_days(self):
        if not self.end_date:
            return 0

        remaining = self.end_date - timezone.now()

        if remaining.total_seconds() <= 0:
            return 0

        return remaining.days + 1

    def activate(self, start_date=None):
        start_date = start_date or timezone.now()

        self.start_date = start_date

        self.end_date = (
            start_date +
            timedelta(days=self.billing_period_days)
        )

        self.status = self.Status.ACTIVE

        self.save(
            update_fields=[
                "start_date",
                "end_date",
                "status",
                "updated_at",
            ]
        )

    def cancel(self):
        self.status = self.Status.CANCELLED

        self.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    def expire(self):
        self.status = self.Status.EXPIRED

        self.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )


class SaaSInvoice(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saas_invoices"
    )

    subscription = models.ForeignKey(
        SaaSSubscription,
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    # Snapshot of what was purchased
    product_name = models.CharField(
        max_length=100
    )

    plan_name = models.CharField(
        max_length=100
    )

    daily_limit = models.PositiveIntegerField()

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=3,
        choices=[
            ("USD", "USD"),
            ("PKR", "PKR"),
        ],
        default="USD"
    )

    billing_period_days = models.PositiveIntegerField(
        default=30
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    payment_method = models.CharField(
        max_length=30,
        blank=True,
    )

    transaction_id = models.CharField(
        max_length=200,
        blank=True,
    )

    issued_at = models.DateTimeField(
        auto_now_add=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.invoice_number} - {self.user.email}"


class UserProfile(models.Model):
    """
    Additional information associated with a Zafium user.

    SaaS subscription status is intentionally NOT stored here.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        blank=True,
    )

    company = models.CharField(
        max_length=150,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.email


class SaaSUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="saas_usage",
    )

    identity_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Used to track anonymous users.",
    )

    product = models.ForeignKey(
        SaaSProduct,
        on_delete=models.PROTECT,
        related_name="usage",
    )

    date = models.DateField()

    count = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        ordering = ["-date"]

        constraints = [
            models.CheckConstraint(
                condition=Q(count__gte=0),
                name="saas_usage_count_gte_zero",
            ),

            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False, identity_key="")
                    |
                    Q(user__isnull=True, identity_key__gt="")
                ),
                name="saas_usage_user_or_anonymous",
            ),

            models.UniqueConstraint(
                fields=[
                    "user",
                    "product",
                    "date",
                ],
                condition=Q(user__isnull=False),
                name="unique_daily_user_product_usage",
            ),

            models.UniqueConstraint(
                fields=[
                    "identity_key",
                    "product",
                    "date",
                ],
                condition=Q(user__isnull=True),
                name="unique_daily_anonymous_product_usage",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "product", "date"]
            ),
            models.Index(
                fields=["identity_key", "product", "date"]
            ),
        ]

    def __str__(self):
        if self.user_id:
            identity = self.user.email
        else:
            identity = self.identity_key

        return f"{identity} - {self.product.name} - {self.date}"


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class ProjectStatus(models.TextChoices):
        NEW = "new", "New"
        PLANNING = "planning", "Planning"
        IN_PROGRESS = "in_progress", "In Progress"
        TESTING = "testing", "Testing"
        REVISION = "revision", "Revision"
        COMPLETED = "completed", "Completed"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Credit / Debit Card"
        BANK = "bank", "Bank Transfer"
        JAZZCASH = "jazzcash", "JazzCash"
        EASYPAISA = "easypaisa", "Easypaisa"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    currency = models.CharField(
    max_length=3,
        choices=[
            ("USD", "USD"),
            ("PKR", "PKR"),
        ],
        default="USD",
    )

    description = models.TextField(
        blank=True,
        help_text="Project requirements provided by the client."
    )
    
    notes = models.TextField(blank=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    project_status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.NEW
    )

    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text="Project completion percentage."
    )

    latest_update = models.TextField(
        blank=True,
        help_text="Latest progress update visible to the customer."
    )

    estimated_delivery = models.DateField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    transaction_id = models.CharField(
        max_length=200,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        return sum(item.total_price() for item in self.items.all())

    @property
    def is_completed(self):
        return self.project_status in (
            self.ProjectStatus.COMPLETED,
            self.ProjectStatus.DELIVERED
        )
    
    @property
    def revision_count(self):
        return self.revisions.count()

    @property
    def can_request_revision(self):
        return self.revision_count < 3

    def __str__(self):
        return f"Order #{self.id} - {self.user.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    category = models.ForeignKey(PortfolioCategory, on_delete=models.SET_NULL, null=True)
    subcategory = models.ForeignKey(PortfolioSubCategory, on_delete=models.SET_NULL, null=True)

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.price * self.quantity
    

class OrderRevision(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="revisions",
    )

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Revision #{self.pk} - Order #{self.order.id}"


class OrderReview(models.Model):

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="review"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    title = models.CharField(
        max_length=150
    )

    review = models.TextField()

    approved = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.user.first_name} ({self.rating}/5)"


class OrderAttachment(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    file = models.FileField(
        upload_to="order_attachments/%Y/%m/"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
    

class OrderDelivery(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )

    title = models.CharField(
        max_length=200,
        help_text="Example: Final Website, Source Code, Documentation"
    )

    description = models.TextField(
        blank=True
    )

    file = models.FileField(
        upload_to="deliveries/%Y/%m/"
    )

    visible_to_user = models.BooleanField(
        default=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.order} - {self.title}"

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        super().save(*args, **kwargs)

        # Automatically mark the project as delivered
        if is_new:

            self.order.project_status = Order.ProjectStatus.DELIVERED

            if not self.order.completed_at:
                self.order.completed_at = timezone.now()

            self.order.progress = 100

            self.order.save(
                update_fields=[
                    "project_status",
                    "completed_at",
                    "progress",
                ]
            )