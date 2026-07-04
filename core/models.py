from django.db import models

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
        max_length=50,
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
    


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Credit / Debit Card"
        PAYPAL = "paypal", "PayPal"
        BANK = "bank", "Bank Transfer"
        JAZZCASH = "jazzcash", "JazzCash"
        EASYPAISA = "easypaisa", "Easypaisa"

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    country = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    transaction_id = models.CharField(
        max_length=200,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_amount(self):
        return sum(item.total_price() for item in self.items.all())


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