that is the full code of my products app of my django ecommerce , read it well so i will ask you some help after that , so read them well and for me .

products.models.py :
import random
import string
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum
from products.utils import send_whatsapp_message
from accounts.models import User
from core import settings

GOVERNMENT_CHOICES = [
    ('1', 'Cairo'),
    ('2', 'Alexandria'),
    ('3', 'Kafr El Sheikh'),
    ('4', 'Dakahlia'),
    ('5', 'Sharqia'),
    ('6', 'Gharbia'),
    ('7', 'Monufia'),
    ('8', 'Qalyubia'),
    ('9', 'Giza'),
    ('10', 'Beni Suef'),
    ('11', 'Fayoum'),
    ('12', 'Minya'),
    ('13', 'Assiut'),
    ('14', 'Sohag'),
    ('15', 'Qena'),
    ('16', 'Luxor'),
    ('17', 'Aswan'),
    ('18', 'Red Sea'),
    ('19', 'Beheira'),
    ('20', 'Ismailia'),
    ('21', 'Suez'),
    ('22', 'Port Said'),
    ('23', 'Damietta'),
    ('24', 'Matruh'),
    ('25', 'New Valley'),
    ('26', 'North Sinai'),
    ('27', 'South Sinai'),
]

PILL_STATUS_CHOICES = [
    ('i', 'initiated'),
    ('w', 'Waiting'),
    ('p', 'Paid'),
    ('u', 'Under Delivery'),
    ('d', 'Delivered'),
    ('r', 'Refused'),
    ('c', 'Canceled'),
]

SIZES_CHOICES = [
    ('s', 'S'),
    ('xs', 'XS'),
    ('m', 'M'),
    ('l', 'L'),
    ('xl', 'XL'),
    ('xxl', 'XXL'),
    ('xxxl', 'XXXL'),
    ('xxxxl', 'XXXXL'),
    ('xxxxxl', 'XXXXXL'),
]

PAYMENT_CHOICES = [
    ('c', 'cash'),
    ('v', 'visa'),
]

def generate_pill_number():
    """Generate a unique 20-digit pill number."""
    while True:
        pill_number = ''.join(random.choices(string.digits, k=20))
        if not Pill.objects.filter(pill_number=pill_number).exists():
            return pill_number

def create_random_coupon():
    letters = string.ascii_lowercase
    nums = ['0', '2', '3', '4', '5', '6', '7', '8', '9']
    marks = ['@', '#', '$', '%', '&', '*']
    return '-'.join(random.choice(letters) + random.choice(nums) + random.choice(marks) for _ in range(5))

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    price = models.FloatField(null=True, blank=True)
    threshold = models.PositiveIntegerField(
        default=10,
        help_text="Minimum quantity threshold for low stock alerts"
    )
    description = models.TextField(max_length=1000, null=True, blank=True)
    is_important = models.BooleanField(
        default=False,
        help_text="Mark if this product is important/special"
    )
    date_added = models.DateTimeField(auto_now_add=True)

    def get_current_discount(self):
        """Returns the best active discount (either product or category level)"""
        now = timezone.now()
        product_discount = self.discounts.filter(
            is_active=True,
            discount_start__lte=now,
            discount_end__gte=now
        ).order_by('-discount').first()

        category_discount = None
        if self.category:
            category_discount = self.category.discounts.filter(
                is_active=True,
                discount_start__lte=now,
                discount_end__gte=now
            ).order_by('-discount').first()

        if product_discount and category_discount:
            return max(product_discount, category_discount, key=lambda d: d.discount)
        return product_discount or category_discount

    def price_after_product_discount(self):
        last_product_discount = self.discounts.last()
        if last_product_discount:
            return self.price - ((last_product_discount.discount / 100) * self.price)
        return self.price

    def price_after_category_discount(self):
        if self.category:  
            last_category_discount = self.category.discounts.last()
            if last_category_discount:
                return self.price - ((last_category_discount.discount / 100) * self.price)
        return self.price

    def discounted_price(self):
        discount = self.get_current_discount()
        if discount:
            return self.price * (1 - discount.discount / 100)
        return self.price

    def has_discount(self):
        return self.get_current_discount() is not None

    def main_image(self):
        images = self.images.all()
        if images.exists():
            return random.choice(images)
        return None

    def images(self):
        return self.images.all()

    def number_of_ratings(self):
        return self.ratings.count()

    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(rating.star_number for rating in ratings) / ratings.count(), 1)
        return 0.0

    def total_quantity(self):
        return self.availabilities.aggregate(total=Sum('quantity'))['total'] or 0

    def available_colors(self):
        """Returns a list of unique colors available for this product."""
        colors = Color.objects.filter(
            productavailability__product=self,
            productavailability__color__isnull=False
        ).distinct().values('id', 'name')
        return [{"color_id": color['id'], "color_name": color['name']} for color in colors]

    def available_sizes(self):
        return self.availabilities.filter(size__isnull=False).values_list('size', flat=True).distinct()

    def is_low_stock(self):
        return self.total_quantity() <= self.threshold
    
    def __str__(self):
        return self.name

class SpecialProduct(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='special_products'
    )
    special_image = models.ImageField(
        upload_to='special_products/',
        null=True,
        blank=True
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Ordering priority (higher numbers come first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Show this special product"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order', '-created_at']
        verbose_name = 'Special Product'
        verbose_name_plural = 'Special Products'

    def __str__(self):
        return f"Special: {self.product.name}"

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductDescription(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='descriptions'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Product Description'
        verbose_name_plural = 'Product Descriptions'

    def __str__(self):
        return f"{self.title} - {self.product.name}"

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    degree = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class ProductAvailability(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='availabilities'
    )
    size = models.CharField(max_length=50, null=True, blank=True)
    color = models.ForeignKey(
        Color,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    quantity = models.PositiveIntegerField()
    native_price = models.FloatField(
        default=0.0,
        help_text="The original price the owner paid for this product batch"
    )
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['product', 'size', 'color']

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color.name if self.color else 'No Color'}"

class ProductSales(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=50, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True, blank=True)
    price_at_sale = models.FloatField()
    date_sold = models.DateTimeField(auto_now_add=True)
    pill = models.ForeignKey('Pill', on_delete=models.CASCADE, related_name='product_sales')

    def __str__(self):
        return f"{self.product.name} - {self.quantity} sold on {self.date_sold}"

class Shipping(models.Model):
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2)
    shipping_price = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.get_government_display()} - {self.shipping_price}"

class PillItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pill_items', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pill_items')
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, choices=SIZES_CHOICES, null=True)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.quantity} - {self.size} - {self.color.name if self.color else 'No Color'}"

    class Meta:
        unique_together = ['user', 'product', 'size', 'color']

class Pill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pills')
    items = models.ManyToManyField(PillItem, related_name='pills')
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1, default='i')
    date_added = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    coupon = models.ForeignKey('CouponDiscount', on_delete=models.SET_NULL, null=True, blank=True, related_name='pills')
    coupon_discount = models.FloatField(default=0.0)
    pill_number = models.CharField(
        max_length=20,
        editable=False,
        unique=True,
        default=generate_pill_number
    )

    def save(self, *args, **kwargs):
        if not self.pill_number:
            self.pill_number = generate_pill_number()
        is_new = not self.pk
        old_status = None if is_new else Pill.objects.get(pk=self.pk).status
        super().save(*args, **kwargs)
        if is_new:
            PillStatusLog.objects.create(pill=self, status=self.status)
            self.items.update(status=self.status)
        else:
            if old_status != self.status:
                status_log, created = PillStatusLog.objects.get_or_create(
                    pill=self,
                    status=self.status
                )
                if not created:
                    status_log.changed_at = timezone.now()
                    status_log.save()
                self.items.update(status=self.status)
            if old_status != 'd' and self.status == 'd':
                self.process_delivery()
        if self.paid and self.status != 'p':
            self.status = 'p'
            super().save(*args, **kwargs)
            self.send_payment_notification()

    def process_delivery(self):
        """Process items when pill is marked as delivered"""
        with transaction.atomic():
            for item in self.items.all():
                availability = ProductAvailability.objects.select_for_update().get(
                    product=item.product,
                    size=item.size,
                    color=item.color
                )
                if availability.quantity < item.quantity:
                    raise ValidationError(f"Not enough inventory for {item.product.name}")
                availability.quantity -= item.quantity
                availability.save()
                ProductSales.objects.create(
                    product=item.product,
                    quantity=item.quantity,
                    size=item.size,
                    color=item.color,
                    price_at_sale=item.product.discounted_price(),
                    pill=self
                )

    def send_payment_notification(self):
        """Send payment confirmation if phone exists"""
        if hasattr(self, 'pilladdress') and self.pilladdress.phone:
            prepare_whatsapp_message(self.pilladdress.phone, self)

    class Meta:
        verbose_name_plural = 'Bills'

    def __str__(self):
        return f"Pill ID: {self.id} - Status: {self.get_status_display()} - Date: {self.date_added}"

    def price_without_coupons(self):
        return sum(item.product.discounted_price() * item.quantity for item in self.items.all())

    def calculate_coupon_discount(self):
        if self.coupon:
            now = timezone.now()
            if self.coupon.coupon_start <= now <= self.coupon.coupon_end:
                return self.coupon.discount_value
        return 0.0

    def price_after_coupon_discount(self):
        return self.price_without_coupons() - (self.coupon_discount or 0)

    def shipping_price(self):
        if hasattr(self, 'pilladdress'):
            try:
                shipping = Shipping.objects.filter(government=self.pilladdress.government).first()
                return shipping.shipping_price
            except Shipping.DoesNotExist:
                return 0.0
        return 0.0

    def final_price(self):
        return self.price_after_coupon_discount() + self.shipping_price()

class PillAddress(models.Model):
    pill = models.OneToOneField(Pill, on_delete=models.CASCADE, related_name='pilladdress')
    name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2)
    pay_method = models.CharField(choices=PAYMENT_CHOICES, max_length=2, default="c")

    def __str__(self):
        return f"{self.name} - {self.address}"

class PillStatusLog(models.Model):
    pill = models.ForeignKey(Pill, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pill.id} - {self.get_status_display()} at {self.changed_at}"

class CouponDiscount(models.Model):
    coupon = models.CharField(max_length=100, blank=True, null=True, editable=False)
    discount_value = models.FloatField(null=True, blank=True)
    coupon_start = models.DateTimeField(null=True, blank=True)
    coupon_end = models.DateTimeField(null=True, blank=True)
    available_use_times = models.PositiveIntegerField(default=1)

    def save(self, *args, **kwargs):
        if not self.coupon:
            self.coupon = create_random_coupon()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.coupon

class Rating(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    star_number = models.IntegerField()
    review = models.CharField(max_length=300, default="No review comment")
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.star_number} stars for {self.product.name} by {self.user.username}"

    def star_ranges(self):
        return range(int(self.star_number)), range(5 - int(self.star_number))

class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='discounts')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='discounts')
    discount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    discount_start = models.DateTimeField()
    discount_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        target = f"Product: {self.product.name}" if self.product else f"Category: {self.category.name}"
        return f"{self.discount}% discount on {target}"

    def clean(self):
        if not self.product and not self.category:
            raise ValidationError("Either product or category must be set")
        if self.product and self.category:
            raise ValidationError("Cannot set both product and category")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.is_active and self.discount_start <= now <= self.discount_end

class PayRequest(models.Model):
    pill = models.ForeignKey('Pill', on_delete=models.CASCADE, related_name='pay_requests')
    image = models.ImageField(upload_to='pay_requests/')
    date = models.DateTimeField(auto_now_add=True)
    is_applied = models.BooleanField(default=False)

    def __str__(self):
        return f"PayRequest for Pill {self.pill.id} - Applied: {self.is_applied}"

class LovedProduct(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='loved_products',
        null=True,
        blank=True
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} loved by {self.user.username if self.user else 'anonymous'}"

class StockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ['product', 'user'],
            ['product', 'email']
        ]

class PriceDropAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    last_price = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ['product', 'user'],
            ['product', 'email']
        ]

class SpinWheelDiscount(models.Model):
    name = models.CharField(max_length=100)
    coupon = models.OneToOneField(CouponDiscount, on_delete=models.CASCADE)
    probability = models.FloatField(
        default=0.1,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Probability of winning (0 to 1)"
    )
    is_active = models.BooleanField(default=True)
    daily_spin_limit = models.PositiveIntegerField(
        default=1,
        help_text="Maximum spins per user per day"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    min_order_value = models.FloatField(
        default=0,
        help_text="Minimum order value to claim the prize"
    )

    def __str__(self):
        return f"{self.name} ({self.coupon.coupon})"

    def is_available(self):
        now = timezone.now()
        return (self.is_active and 
                self.start_date <= now <= self.end_date)

class SpinWheelResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    spin_wheel = models.ForeignKey(SpinWheelDiscount, on_delete=models.CASCADE)
    won = models.BooleanField(default=False)
    coupon = models.ForeignKey(
        CouponDiscount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    spin_date = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    used_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [['user', 'spin_wheel', 'spin_date']]

def prepare_whatsapp_message(phone_number, pill):
    print(f"Preparing WhatsApp message for phone number: {phone_number}")
    message = (
        f"مرحباً {pill.user.username}،\n\n"
        f"تم استلام طلبك بنجاح.\n\n"
        f"رقم الطلب: {pill.pill_number}\n"
    )
    send_whatsapp_message(
        phone_number=phone_number,
        message=message
    )

products.serializers.py :
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from collections import defaultdict
from urllib.parse import urljoin
from django.utils import timezone
from django.db.models import Sum
from accounts.models import User
from .models import (
    Category, CouponDiscount, Discount, LovedProduct, PayRequest, PillAddress,
    PillItem, PillStatusLog, PriceDropAlert, ProductDescription, Shipping,
    SpecialProduct, SpinWheelDiscount, SpinWheelResult, StockAlert,
    SubCategory, Brand, Product, ProductImage, ProductAvailability, Rating, Color, Pill
)

class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'category', 'category_name']

    def get_category_name(self, obj):
        return obj.category.name
    
class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'subcategories']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class ProductDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDescription
        fields = ['id', 'title', 'description', 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProductDescriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDescription
        fields = ['product', 'title', 'description', 'order']
    
    def to_internal_value(self, data):
        if isinstance(data, list):
            return [super().to_internal_value(item) for item in data]
        return super().to_internal_value(data)

class BulkProductDescriptionSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        descriptions = [ProductDescription(**item) for item in validated_data]
        return ProductDescription.objects.bulk_create(descriptions)

class PillItemCreateUpdateSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    color = serializers.PrimaryKeyRelatedField(queryset=Color.objects.all(), required=False, allow_null=True)

    class Meta:
        model = PillItem
        fields = ['product', 'quantity', 'size', 'color']

    def validate(self, data):
        # For both create and update cases
        instance = getattr(self, 'instance', None)
        product = data.get('product', getattr(instance, 'product', None))
        size = data.get('size', getattr(instance, 'size', None))
        color = data.get('color', getattr(instance, 'color', None))
        quantity = data.get('quantity', getattr(instance, 'quantity', 1))

        # Validate stock availability
        self._validate_stock(product, size, color, quantity)
        return data

    def _validate_stock(self, product, size, color, quantity):
        if quantity <= 0:
            raise serializers.ValidationError({
                'quantity': 'Quantity must be greater than 0.'
            })

        availabilities = ProductAvailability.objects.filter(
            product=product,
            size=size,
            color=color
        )

        if not availabilities.exists():
            color_name = color.name if color else 'N/A'
            raise serializers.ValidationError({
                'non_field_errors': [
                    f"The selected variant (Size: {size or 'N/A'}, Color: {color_name}) "
                    f"is not available for {product.name}."
                ]
            })

        total_available = availabilities.aggregate(total=Sum('quantity'))['total'] or 0

        if total_available < quantity:
            color_name = color.name if color else 'N/A'
            raise serializers.ValidationError({
                'quantity': [
                    f"Not enough stock for {product.name} "
                    f"(Size: {size or 'N/A'}, Color: {color_name}). "
                    f"Available: {total_available}, Requested: {quantity}."
                ]
            })


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = '__all__'

class ProductAvailabilitySerializer(serializers.ModelSerializer):
    color = serializers.PrimaryKeyRelatedField(
        queryset=Color.objects.all(),
        allow_null=True,
        required=False
    )
    size = serializers.CharField(
        allow_null=True,
        required=False
    )
    product_name = serializers.SerializerMethodField()
    native_price = serializers.FloatField()

    class Meta:
        model = ProductAvailability
        fields = ['id', 'product', 'product_name', 'size', 'color', 'quantity', 'native_price', 'date_added']
        read_only_fields = ['date_added']

    def get_product_name(self, obj):
        return obj.product.name

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.color:
            representation['color'] = ColorSerializer(instance.color).data
        else:
            representation['color'] = None
        return representation

class ProductAvailabilityBreifedSerializer(serializers.Serializer):
    size = serializers.CharField()
    color = serializers.CharField()
    quantity = serializers.IntegerField()
    is_low_stock = serializers.SerializerMethodField()

    def get_is_low_stock(self, obj):
        return obj.product.is_low_stock()

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'product', 'user', 'star_number', 'review', 'date_added']
        read_only_fields = ['date_added', 'user']

    def validate(self, data):
        if data.get('star_number') < 1 or data.get('star_number') > 5:
            raise serializers.ValidationError("Star number must be between 1 and 5.")
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ProductImageBulkUploadSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False
    )

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    availabilities = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()
    number_of_ratings = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    available_colors = serializers.SerializerMethodField()
    available_sizes = serializers.SerializerMethodField()
    current_discount = serializers.SerializerMethodField()
    discount_expiry = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    descriptions = ProductDescriptionSerializer(many=True, read_only=True)
    category_id = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    sub_category_id = serializers.SerializerMethodField()
    sub_category_name = serializers.SerializerMethodField()
    brand_id = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category_id', 'category_name', 'sub_category_id', 'sub_category_name',
            'brand_id', 'brand_name', 'price', 'description', 'date_added', 'discounted_price',
            'has_discount', 'current_discount', 'discount_expiry', 'main_image', 'images', 'number_of_ratings',
            'average_rating', 'total_quantity', 'available_colors', 'available_sizes', 'availabilities',
            'descriptions', 'threshold', 'is_low_stock', 'is_important'
        ]

    def get_category_id(self, obj):
        return obj.category.id if obj.category else None

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_sub_category_id(self, obj):
        return obj.sub_category.id if obj.sub_category else None

    def get_sub_category_name(self, obj):
        return obj.sub_category.name if obj.sub_category else None

    def get_brand_id(self, obj):
        return obj.brand.id if obj.brand else None

    def get_brand_name(self, obj):
        return obj.brand.name if obj.brand else None

    def get_availabilities(self, obj):
        grouped_availabilities = defaultdict(int)
        for availability in obj.availabilities.all():
            key = (availability.size, availability.color.id if availability.color else None, availability.color.name if availability.color else None)
            grouped_availabilities[key] += availability.quantity
        result = [
            {
                "size": size,
                "color_id": color_id,
                "color": color_name,
                "quantity": quantity
            }
            for (size, color_id, color_name), quantity in grouped_availabilities.items()
        ]
        return result

    def get_discounted_price(self, obj):
        return obj.discounted_price()

    def get_current_discount(self, obj):
        now = timezone.now()
        product_discount = obj.discounts.filter(
            is_active=True,
            discount_start__lte=now,
            discount_end__gte=now
        ).order_by('-discount').first()
        category_discount = None
        if obj.category:
            category_discount = obj.category.discounts.filter(
                is_active=True,
                discount_start__lte=now,
                discount_end__gte=now
            ).order_by('-discount').first()
        if product_discount and category_discount:
            return max(product_discount.discount, category_discount.discount)
        elif product_discount:
            return product_discount.discount
        elif category_discount:
            return category_discount.discount
        return None

    def get_discount_expiry(self, obj):
        now = timezone.now()
        discount = obj.discounts.filter(
            is_active=True,
            discount_start__lte=now,
            discount_end__gte=now
        ).order_by('-discount_end').first()
        if not discount and obj.category:
            discount = obj.category.discounts.filter(
                is_active=True,
                discount_start__lte=now,
                discount_end__gte=now
            ).order_by('-discount_end').first()
        return discount.discount_end if discount else None
    
    def get_has_discount(self, obj):
        return obj.has_discount()

    def get_main_image(self, obj):
        main_image = obj.main_image()
        if main_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(main_image.image.url)
            else:
                base_url = ""
                return urljoin(base_url, main_image.image.url)
        return None

    def get_number_of_ratings(self, obj):
        return obj.number_of_ratings()

    def get_average_rating(self, obj):
        return obj.average_rating()

    def get_total_quantity(self, obj):
        return obj.total_quantity()

    def get_available_colors(self, obj):
        return obj.available_colors()

    def get_available_sizes(self, obj):
        return obj.available_sizes()

    def get_is_low_stock(self, obj):
        return obj.is_low_stock()

class ProductBreifedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']

class CouponCodeField(serializers.Field):
    def to_internal_value(self, data):
        try:
            return CouponDiscount.objects.get(coupon=data)
        except CouponDiscount.DoesNotExist:
            raise serializers.ValidationError("Coupon does not exist.")

    def to_representation(self, value):
        return value.coupon

class SpecialProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = SpecialProduct
        fields = [
            'id', 'product', 'product_id', 'special_image',
            'order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class UserCartSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    color = ColorSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = PillItem
        fields = ['id', 'product', 'quantity', 'size', 'color', 'total_price', 'date_added']

    def get_total_price(self, obj):
        return obj.product.discounted_price() * obj.quantity

class PillCouponApplySerializer(serializers.ModelSerializer):
    coupon = CouponCodeField()
    # coupon_name = serializers.SerializerMethodField()
    # coupon_description = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Pill
        fields = [
            'id', 'coupon', 
            'price_without_coupons', 'coupon_discount', 
            'price_after_coupon_discount', 'final_price',
            # 'coupon_name', 'coupon_description',
            'discount_percentage'
        ]
        read_only_fields = [
            'id', 'price_without_coupons', 
            'coupon_discount', 'price_after_coupon_discount', 
            'final_price', 
            # 'coupon_name', 
            # 'coupon_description', 
            'discount_percentage'
        ]
    
    def validate_coupon(self, value):
        pill = self.instance
        now = timezone.now()
        
        # Check if coupon is valid
        if not (value.coupon_start <= now <= value.coupon_end):
            raise serializers.ValidationError(
                { "message": "This coupon has expired."}
            )
        
        # Check if coupon is already applied
        if pill.coupon:
            raise serializers.ValidationError(
                { "message": "A coupon is already applied to this order."}
            )
        
        # Check coupon usage limits
        if value.available_use_times <= 0:
            raise serializers.ValidationError(
                { "message": "This coupon has no remaining uses."}
            )
        
        # Check minimum order value if applicable
        if hasattr(value, 'min_order_value') and pill.price_without_coupons() < value.min_order_value:
            raise serializers.ValidationError({
                "message": f"Order must be at least {value.min_order_value} to use this coupon."
            })
        
        return value
    
    def get_coupon_name(self, obj):
        return obj.coupon.name if obj.coupon else None
    
    def get_coupon_description(self, obj):
        return obj.coupon.description if obj.coupon else None
    
    def get_discount_percentage(self, obj):
        if obj.coupon and obj.price_without_coupons() > 0:
            return round((obj.coupon_discount / obj.price_without_coupons()) * 100)
        return 0
    
    def update(self, instance, validated_data):
        coupon = validated_data.get('coupon')
        instance.coupon = coupon
        instance.coupon_discount = (coupon.discount_value / 100) * instance.price_without_coupons()
        instance.save()
        
        # Update coupon usage
        coupon.available_use_times -= 1
        coupon.save()
        
        return instance
    
class PillAddressSerializer(serializers.ModelSerializer):
    government = serializers.SerializerMethodField()

    class Meta:
        model = PillAddress
        fields = ['name', 'email', 'phone', 'address', 'government']

    def get_government(self, obj):
        return obj.get_government_display()

class PillItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    color = ColorSerializer(read_only=True)

    class Meta:
        model = PillItem
        fields = ['id', 'product', 'quantity', 'size', 'color', 'status', 'date_added']

class PillItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PillItem
        fields = ['product', 'quantity', 'size', 'color']

class PillCreateSerializer(serializers.ModelSerializer):
    items = PillItemCreateSerializer(many=True, required=False)  # Make items optional
    user_name = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Pill
        fields = ['id', 'user', 'user_name', 'user_username', 'items', 'status', 'date_added', 'paid']
        read_only_fields = ['id', 'status', 'date_added', 'paid']

    def get_user_name(self, obj):
        return obj.user.name

    def get_user_username(self, obj):
        return obj.user.username

    def create(self, validated_data):
        user = validated_data['user']
        items_data = validated_data.pop('items', None)  # Get items if provided
        
        # Create the pill first
        pill = Pill.objects.create(**validated_data)
        
        if items_data:
            # If items were provided in the request
            pill_items = [
                PillItem(
                    user=user,  # Important to set the user
                    product=item['product'],
                    quantity=item['quantity'],
                    size=item.get('size'),
                    color=item.get('color'),
                    status=pill.status  # Set initial status
                ) for item in items_data
            ]
            created_items = PillItem.objects.bulk_create(pill_items)
            pill.items.set(created_items)
        else:
            # If no items provided, use the user's cart items
            cart_items = PillItem.objects.filter(user=user, status__isnull=True)
            if not cart_items.exists():
                raise ValidationError("No items provided in request and no items in cart to create a pill.")
            pill.items.set(cart_items)
            cart_items.update(status=pill.status)
        
        return pill

class PillStatusLogSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = PillStatusLog
        fields = ['status', 'status_display', 'changed_at']

    def get_status_display(self, obj):
        return obj.get_status_display()

class PayRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayRequest
        fields = ['id', 'pill', 'image', 'date', 'is_applied']
        read_only_fields = ['id', 'date']

class ShippingSerializer(serializers.ModelSerializer):
    government_name = serializers.SerializerMethodField()

    class Meta:
        model = Shipping
        fields = ['id', 'government', 'government_name', 'shipping_price']

    def get_government_name(self, obj):
        return obj.get_government_display()

class PillAddressCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PillAddress
        fields = ['id', 'pill', 'name', 'email', 'phone', 'address', 'government', 'pay_method']
        read_only_fields = ['id', 'pill']

class CouponDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponDiscount
        fields = ['coupon', 'discount_value', 'coupon_start', 'coupon_end', 'available_use_times']

class PillDetailSerializer(serializers.ModelSerializer):
    items = PillItemSerializer(many=True, read_only=True)
    coupon = CouponDiscountSerializer(read_only=True)
    pilladdress = PillAddressSerializer(read_only=True)
    shipping_price = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()
    status_logs = PillStatusLogSerializer(many=True, read_only=True)
    pay_requests = PayRequestSerializer(many=True, read_only=True)
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Pill
        fields = [
            'id', 'user_name', 'user_username', 'items', 'status', 'status_display', 'date_added', 'paid', 'coupon', 'pilladdress',
            'price_without_coupons', 'coupon_discount', 'price_after_coupon_discount',
            'shipping_price', 'final_price', 'status_logs', 'pay_requests'
        ]
        read_only_fields = ['date_added', 'price_without_coupons', 'coupon_discount', 'price_after_coupon_discount', 'shipping_price', 'final_price']

    def get_user_name(self, obj):
        return obj.user.name

    def get_user_username(self, obj):
        return obj.user.username
    
    def get_shipping_price(self, obj):
        return obj.shipping_price()

    def get_status_display(self, obj):
        return obj.get_status_display()
    
    def get_final_price(self, obj):
        return obj.price_after_coupon_discount() + obj.shipping_price()

class DiscountSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Discount
        fields = [
            'id', 'product', 'product_name', 'category', 'category_name',
            'discount', 'discount_start', 'discount_end', 'is_active'
        ]
        read_only_fields = ['is_active']

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_is_active(self, obj):
        return obj.is_currently_active

    def validate(self, data):
        if not data.get('product') and not data.get('category'):
            raise serializers.ValidationError("Either product or category must be set")
        if data.get('product') and data.get('category'):
            raise serializers.ValidationError("Cannot set both product and category")
        return data

class LovedProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = LovedProduct
        fields = ['id', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'created_at']

class StockAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAlert
        fields = ['id', 'product', 'email', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'email': {'required': False}
        }

class PriceDropAlertSerializer(serializers.ModelSerializer):
    last_price = serializers.FloatField(required=False)
    
    class Meta:
        model = PriceDropAlert
        fields = ['id', 'product', 'email', 'last_price', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'email': {'required': False}
        }

    def validate_last_price(self, value):
        if value and value <= 0:
            raise serializers.ValidationError("Price must be positive")
        return value



class SpinWheelDiscountSerializer(serializers.ModelSerializer):
    coupon = serializers.PrimaryKeyRelatedField(queryset=CouponDiscount.objects.all())

    class Meta:
        model = SpinWheelDiscount
        fields = ['id', 'name', 'probability', 'daily_spin_limit', 'min_order_value', 'start_date', 'end_date', 'is_active', 'coupon']
        read_only_fields = ['id']

    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date.")
        if data['probability'] < 0 or data['probability'] > 1:
            raise serializers.ValidationError("Probability must be between 0 and 1.")
        if data['daily_spin_limit'] <= 0:
            raise serializers.ValidationError("Daily spin limit must be positive.")
        if data['min_order_value'] < 0:
            raise serializers.ValidationError("Minimum order value cannot be negative.")
        return data

class SpinWheelResultSerializer(serializers.ModelSerializer):
    coupon = CouponDiscountSerializer(read_only=True)
    
    class Meta:
        model = SpinWheelResult
        fields = ['id', 'won', 'coupon', 'spin_date', 'used', 'used_date']

products.views.py :
from datetime import timedelta
import random
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, F, Count, Q
from django.db import transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework import filters as rest_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from .serializers import *
from .filters import CategoryFilter, CouponDiscountFilter, PillFilter, ProductFilter
from .models import (
    Category, Color, CouponDiscount, PillAddress, ProductAvailability,
    ProductImage, ProductSales, Rating, Shipping, SubCategory, Brand, Product, Pill
)
from .permissions import IsOwner, IsOwnerOrReadOnly

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CategoryFilter
    
class SubCategoryListView(generics.ListAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']

class BrandListView(generics.ListAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    pagination_class = None

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'category__name', 'brand__name', 'description']

class Last10ProductsListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'

class ActiveSpecialProductsView(generics.ListAPIView):
    serializer_class = SpecialProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return SpecialProduct.objects.filter(is_active=True).order_by('-order')[:10]

class UserCartView(generics.ListAPIView):
    serializer_class = UserCartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PillItem.objects.filter(user=self.request.user, status__isnull=True).order_by('-date_added')

class PillItemCreateView(generics.CreateAPIView):
    serializer_class = PillItemCreateUpdateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        product = serializer.validated_data['product']
        size = serializer.validated_data.get('size')
        color = serializer.validated_data.get('color')
        quantity = serializer.validated_data['quantity']

        with transaction.atomic():
            # Check for existing item
            existing_item = PillItem.objects.filter(
                user=user,
                product=product,
                size=size,
                color=color,
                status__isnull=True
            ).first()

            if existing_item:
                # Validate the combined quantity
                combined_quantity = existing_item.quantity + quantity
                try:
                    # Reuse the serializer's validation
                    temp_data = {
                        'product': product,
                        'size': size,
                        'color': color,
                        'quantity': combined_quantity
                    }
                    serializer.__class__(data=temp_data).is_valid(raise_exception=True)
                except serializers.ValidationError as e:
                    raise serializers.ValidationError(e.detail)

                # Update existing item
                existing_item.quantity = combined_quantity
                existing_item.save()
            else:
                # Create new item
                serializer.save(user=user, status=None)



class PillItemUpdateView(generics.UpdateAPIView):
    serializer_class = PillItemCreateUpdateSerializer
    permission_classes = [IsAuthenticated]
    queryset = PillItem.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
        # return super().get_queryset().filter(user=self.request.user, status__isnull=True)

    def patch(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = self.get_object()
            if 'quantity' in request.data and int(request.data.get('quantity', 1)) <= 0:
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            data = request.data.copy()
            allowed_fields = ['quantity']
            data = {k: v for k, v in data.items() if k in allowed_fields}
            serializer = self.get_serializer(instance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)

class PillItemDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PillItem.objects.filter(user=self.request.user, status__isnull=True)

class PillItemPermissionMixin:
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class PillCreateView(generics.CreateAPIView, PillItemPermissionMixin):
    queryset = Pill.objects.all()
    serializer_class = PillCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # The logic is now handled in the serializer
        serializer.save()

class PillCouponApplyView(generics.UpdateAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillCouponApplySerializer
    lookup_field = 'id'

    def perform_update(self, serializer):
        coupon = serializer.validated_data.get('coupon')
        pill = self.get_object()
        if pill.coupon:
            return Response({"error": "This pill already has a coupon applied."}, status=status.HTTP_400_BAD_REQUEST)
        if not self.is_coupon_valid(coupon):
            return Response({"error": "Coupon is not valid or expired."}, status=status.HTTP_400_BAD_REQUEST)
        if not self.is_coupon_available(coupon):
            return Response({"error": "Coupon is not available."}, status=status.HTTP_400_BAD_REQUEST)
        pill = serializer.save(coupon=coupon)
        coupon_discount_amount = (coupon.discount_value / 100) * pill.price_without_coupons()
        pill.coupon_discount = coupon_discount_amount
        pill.save()
        coupon.available_use_times -= 1
        coupon.save()
        return Response(self.get_pill_data(pill), status=status.HTTP_200_OK)

    def is_coupon_valid(self, coupon):
        now = timezone.now()
        return coupon.coupon_start <= now <= coupon.coupon_end

    def is_coupon_available(self, coupon):
        return coupon.available_use_times > 0

    def get_pill_data(self, pill):
        return {
            "id": pill.id,
            "coupon": pill.coupon.coupon if pill.coupon else None,
            "price_without_coupons": pill.price_without_coupons(),
            "coupon_discount": pill.coupon_discount,
            "price_after_coupon_discount": pill.price_after_coupon_discount(),
            "final_price": pill.final_price(),
        }

class PillAddressCreateUpdateView(generics.CreateAPIView, generics.UpdateAPIView, PillItemPermissionMixin):
    queryset = PillAddress.objects.all()
    serializer_class = PillAddressCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pill_id = self.kwargs.get('pill_id')
        pill = get_object_or_404(Pill, id=pill_id, user=self.request.user)
        try:
            return PillAddress.objects.get(pill=pill)
        except PillAddress.DoesNotExist:
            return None

    def perform_create(self, serializer):
        pill_id = self.kwargs.get('pill_id')
        pill = get_object_or_404(Pill, id=pill_id, user=self.request.user)
        serializer.save(pill=pill)
        pill.status = 'w'
        pill.save()

    def perform_update(self, serializer):
        pill_id = self.kwargs.get('pill_id')
        pill = get_object_or_404(Pill, id=pill_id, user=self.request.user)
        serializer.save(pill=pill)
        pill.status = 'w'
        pill.save()

class PillDetailView(generics.RetrieveAPIView, PillItemPermissionMixin):
    queryset = Pill.objects.all()
    serializer_class = PillDetailSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pill_id = self.kwargs.get('id')
        return get_object_or_404(Pill, id=pill_id, user=self.request.user)

class UserPillsView(generics.ListAPIView):
    serializer_class = PillDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pill.objects.filter(user=self.request.user).order_by('-date_added')

class CustomerRatingListCreateView(generics.ListCreateAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Rating.objects.filter(user=self.request.user)

class CustomerRatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated, IsOwner]

class getColors(generics.ListAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer

class PayRequestListCreateView(generics.ListCreateAPIView):
    queryset = PayRequest.objects.all()
    serializer_class = PayRequestSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['is_applied', 'pill__pill_number', 'pill__user__name', 'pill__pilladdress__email', 'pill__pilladdress__phone', 'pill__pilladdress__government']
    search_fields = ['pill__pill_number', 'pill__user__name', 'pill__pilladdress__email', 'pill__pilladdress__phone', 'pill__pilladdress__government']

    def perform_create(self, serializer):
        pill_id = self.request.data.get('pill')
        try:
            pill = Pill.objects.get(id=pill_id, user=self.request.user)
            if pill.paid:
                raise serializers.ValidationError("This pill is already paid.")
            serializer.save(pill=pill)
        except Pill.DoesNotExist:
            raise serializers.ValidationError("Pill does not exist or you do not have permission to create a payment request for this pill.")

class ProductsWithActiveDiscountAPIView(APIView):
    def get(self, request):
        now = timezone.now()
        product_discounts = Discount.objects.filter(
            is_active=True,
            discount_start__lte=now,
            discount_end__gte=now,
            product__isnull=False
        ).values_list('product_id', flat=True)
        category_discounts = Discount.objects.filter(
            is_active=True,
            discount_start__lte=now,
            discount_end__gte=now,
            category__isnull=False
        ).values_list('category_id', flat=True)
        products = Product.objects.filter(
            Q(id__in=product_discounts) | Q(category_id__in=category_discounts)
        ).distinct()
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class LovedProductListCreateView(generics.ListCreateAPIView):
    serializer_class = LovedProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return LovedProduct.objects.filter(user=self.request.user)
        return LovedProduct.objects.none()

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

class LovedProductRetrieveDestroyView(generics.RetrieveDestroyAPIView):
    queryset = LovedProduct.objects.all()
    serializer_class = LovedProductSerializer
    permission_classes = [IsOwnerOrReadOnly]

class StockAlertCreateView(generics.CreateAPIView):
    serializer_class = StockAlertSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        email = request.data.get('email')
        user = request.user if request.user.is_authenticated else None
        product = get_object_or_404(Product, id=product_id)
        if product.total_quantity() > 0:
            return Response(
                {"error": "Product is already in stock"},
                status=status.HTTP_400_BAD_REQUEST
            )
        existing_alert = StockAlert.objects.filter(
            product=product,
            user=user if user else None,
            email=email if not user else None
        ).exists()
        if existing_alert:
            return Response(
                {"error": "You already requested an alert for this product"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PriceDropAlertCreateView(generics.CreateAPIView):
    serializer_class = PriceDropAlertSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        email = request.data.get('email')
        user = request.user if request.user.is_authenticated else None
        last_price = request.data.get('last_price')
        product = get_object_or_404(Product, id=product_id)
        alert, created = PriceDropAlert.objects.update_or_create(
            product=product,
            user=user if user else None,
            email=email if not user else None,
            defaults={
                'last_price': last_price or product.price,
                'is_notified': False
            }
        )
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        serializer = self.get_serializer(alert)
        return Response(serializer.data, status=status_code)

class UserActiveAlertsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        back_in_stock_alerts = StockAlert.objects.filter(
            user=request.user,
            is_notified=False
        ).select_related('product').annotate(
            available_quantity=Sum('product__availabilities__quantity')
        ).filter(
            available_quantity__gt=0
        )
        price_drop_alerts = PriceDropAlert.objects.filter(
            user=request.user,
            is_notified=False
        ).select_related('product').filter(
            product__price__lt=F('last_price')
        )
        back_in_stock_data = []
        for alert in back_in_stock_alerts:
            product_data = ProductSerializer(alert.product, context={'request': request}).data
            back_in_stock_data.append(product_data)
        price_drop_data = []
        for alert in price_drop_alerts:
            alert_data = PriceDropAlertSerializer(alert).data
            product_data = ProductSerializer(alert.product, context={'request': request}).data
            alert_data['product_data'] = product_data
            price_drop_data.append(alert_data)
        return Response({
            'back_in_stock_alerts': back_in_stock_data,
            'price_drop_alerts': price_drop_data
        })

class MarkAlertAsNotifiedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, alert_type, alert_id):
        if alert_type == 'stock':
            model = StockAlert
        elif alert_type == 'price':
            model = PriceDropAlert
        else:
            return Response({'error': 'Invalid alert type'}, status=400)
        alert = get_object_or_404(model, id=alert_id, user=request.user)
        alert.is_notified = True
        alert.save()
        return Response({'status': 'success'})

class NewArrivalsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'sub_category', 'brand']

    def get_queryset(self):
        queryset = Product.objects.all().order_by('-date_added')
        days = self.request.query_params.get('days', None)
        if days:
            date_threshold = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(date_added__gte=date_threshold)
        return queryset

class BestSellersView(generics.ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'sub_category', 'brand']

    def get_queryset(self):
        queryset = Product.objects.annotate(
            total_sold=Sum('sales__quantity')
        ).filter(
            total_sold__gt=0
        ).order_by('-total_sold')
        days = self.request.query_params.get('days', None)
        if days:
            date_threshold = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(
                sales__date_sold__gte=date_threshold
            ).annotate(
                recent_sold=Sum('sales__quantity')
            ).order_by('-recent_sold')
        return queryset

class FrequentlyBoughtTogetherView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        product_id = self.request.query_params.get('product_id')
        if not product_id:
            return Product.objects.none()
        frequent_products = Product.objects.filter(
            sales__pill__items__product_id=product_id
        ).exclude(
            id=product_id
        ).annotate(
            co_purchase_count=Count('id')
        ).order_by('-co_purchase_count')[:5]
        return frequent_products

class ProductRecommendationsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_product_id = self.request.query_params.get('product_id')
        recommendations = []
        if current_product_id:
            current_product = get_object_or_404(Product, id=current_product_id)
            similar_products = Product.objects.filter(
                Q(category=current_product.category) |
                Q(sub_category=current_product.sub_category) |
                Q(brand=current_product.brand)
            ).exclude(id=current_product_id).distinct()
            recommendations.extend(list(similar_products))
        loved_products = Product.objects.filter(
            lovedproduct__user=user
        ).exclude(id__in=[p.id for p in recommendations]).distinct()
        recommendations.extend(list(loved_products))
        purchased_products = Product.objects.filter(
            sales__pill__user=user
        ).exclude(id__in=[p.id for p in recommendations]).distinct()
        recommendations.extend(purchased_products)
        seen = set()
        unique_recommendations = []
        for product in recommendations:
            if product.id not in seen:
                seen.add(product.id)
                unique_recommendations.append(product)
            if len(unique_recommendations) >= 12:
                break
        return unique_recommendations

class SpinWheelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        spin_wheel = SpinWheelDiscount.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).first()
        if not spin_wheel:
            return Response(
                {"error": "No active spin wheel available"},
                status=status.HTTP_404_NOT_FOUND
            )
        today = now.date()
        spins_today = SpinWheelResult.objects.filter(
            user=request.user,
            spin_wheel=spin_wheel,
            spin_date__date=today
        ).count()
        remaining_spins = max(0, spin_wheel.daily_spin_limit - spins_today)
        return Response({
            **SpinWheelDiscountSerializer(spin_wheel).data,
            "remaining_spins": remaining_spins
        })

    def post(self, request):
        now = timezone.now()
        spin_wheel = SpinWheelDiscount.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).first()
        if not spin_wheel:
            return Response(
                {"error": "No active spin wheel available"},
                status=status.HTTP_404_NOT_FOUND
            )
        today = now.date()
        spins_today = SpinWheelResult.objects.filter(
            user=request.user,
            spin_wheel=spin_wheel,
            spin_date__date=today
        ).count()
        if spins_today >= spin_wheel.daily_spin_limit:
            return Response(
                {"error": "Daily spin limit reached"},
                status=status.HTTP_400_BAD_REQUEST
            )
        won = random.random() < spin_wheel.probability
        coupon = spin_wheel.coupon if won else None
        result = SpinWheelResult.objects.create(
            user=request.user,
            spin_wheel=spin_wheel,
            won=won,
            coupon=coupon
        )
        return Response(SpinWheelResultSerializer(result).data)

class SpinWheelHistoryView(generics.ListAPIView):
    serializer_class = SpinWheelResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SpinWheelResult.objects.filter(user=self.request.user).order_by('-spin_date')

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CategoryFilter
    permission_classes = [IsAdminUser]

class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]

class SubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']
    permission_classes = [IsAdminUser]

class SubCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminUser]

class BrandListCreateView(generics.ListCreateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminUser]

class BrandRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAdminUser]

class ColorListCreateView(generics.ListCreateAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    permission_classes = [IsAdminUser]

class ColorRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'category__name', 'brand__name', 'description']
    permission_classes = [IsAdminUser]

class ProductListBreifedView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductBreifedSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'category__name', 'brand__name', 'description']
    permission_classes = [IsAdminUser]

class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]

class ProductImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    filterset_fields = ['product']
    permission_classes = [IsAdminUser]

class ProductImageBulkCreateView(generics.CreateAPIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = ProductImageBulkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data['product']
        images = serializer.validated_data['images']
        product_images = [
            ProductImage(product=product, image=image)
            for image in images
        ]
        ProductImage.objects.bulk_create(product_images)
        return Response(
            {"message": "Images uploaded successfully."},
            status=status.HTTP_201_CREATED
        )

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminUser]

class ProductDescriptionListCreateView(generics.ListCreateAPIView):
    queryset = ProductDescription.objects.all()
    serializer_class = ProductDescriptionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product']
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST' and isinstance(self.request.data, list):
            return ProductDescriptionCreateSerializer
        return ProductDescriptionSerializer

class ProductDescriptionBulkCreateView(generics.CreateAPIView):
    queryset = ProductDescription.objects.all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if isinstance(self.request.data, list):
            class BulkSerializer(ProductDescriptionCreateSerializer):
                class Meta(ProductDescriptionCreateSerializer.Meta):
                    list_serializer_class = BulkProductDescriptionSerializer
            return BulkSerializer
        return ProductDescriptionCreateSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            serializer = self.get_serializer(data=request.data, many=True)
        else:
            serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ProductDescriptionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductDescription.objects.all()
    serializer_class = ProductDescriptionSerializer
    permission_classes = [IsAdminUser]

class SpecialProductListCreateView(generics.ListCreateAPIView):
    queryset = SpecialProduct.objects.all()
    serializer_class = SpecialProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'product']
    ordering_fields = ['order', 'created_at']
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save()

class SpecialProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SpecialProduct.objects.all()
    serializer_class = SpecialProductSerializer
    permission_classes = [IsAdminUser]

class PillListCreateView(generics.ListCreateAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillCreateSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = PillFilter
    search_fields = ['pilladdress__phone', 'pilladdress__government', 'pilladdress__name', 'user__name', 'user__username']
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PillCreateSerializer
        return PillDetailSerializer

class PillRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillDetailSerializer
    permission_classes = [IsAdminUser]

class DiscountListCreateView(generics.ListCreateAPIView):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'category', 'is_active']

class DiscountRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminUser]

class CouponListCreateView(generics.ListCreateAPIView):
    queryset = CouponDiscount.objects.all()
    serializer_class = CouponDiscountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CouponDiscountFilter
    permission_classes = [IsAdminUser]

class CouponRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CouponDiscount.objects.all()
    serializer_class = CouponDiscountSerializer
    permission_classes = [IsAdminUser]

class ShippingListCreateView(generics.ListCreateAPIView):
    queryset = Shipping.objects.all()
    serializer_class = ShippingSerializer
    filterset_fields = ['government']
    permission_classes = [IsAdminUser]

class ShippingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Shipping.objects.all()
    serializer_class = ShippingSerializer
    permission_classes = [IsAdminUser]

class RatingListCreateView(generics.ListCreateAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    filterset_fields = ['product']
    permission_classes = [IsAdminUser]

class RatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAdminUser]

class ProductAvailabilityListCreateView(generics.ListCreateAPIView):
    queryset = ProductAvailability.objects.all()
    serializer_class = ProductAvailabilitySerializer
    # permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'color', 'size']

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        size = request.data.get('size')
        color_id = request.data.get('color')
        
        existing_availability = ProductAvailability.objects.filter(
            product_id=product_id,
            size=size,
            color_id=color_id
        ).first()
        
        if existing_availability:
            # Update existing record
            serializer = self.get_serializer(existing_availability, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            # Handle quantity updates (add to existing quantity)
            if 'quantity' in request.data:
                new_quantity = existing_availability.quantity + int(request.data['quantity'])
                serializer.validated_data['quantity'] = new_quantity
            
            # Save the updated instance
            serializer.save()
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
        else:
            # Create new record
            return super().create(request, *args, **kwargs)

class ProductAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductAvailability.objects.all()
    serializer_class = ProductAvailabilitySerializer
    # permission_classes = [IsAdminUser]

class ProductAvailabilitiesView(generics.ListAPIView):
    serializer_class = ProductAvailabilityBreifedSerializer

    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product, context={'request': request})
        return Response(serializer.data['availabilities'], status=status.HTTP_200_OK)

class AdminPayRequestCreateView(generics.CreateAPIView):
    queryset = PayRequest.objects.all()
    serializer_class = PayRequestSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        pill_id = self.request.data.get('pill')
        try:
            pill = Pill.objects.get(id=pill_id)
            if pill.paid:
                raise serializers.ValidationError("This pill is already paid.")
            serializer.save(pill=pill, is_applied=True)
        except Pill.DoesNotExist:
            raise serializers.ValidationError("Pill does not exist.")

class ApplyPayRequestView(generics.UpdateAPIView):
    queryset = PayRequest.objects.all()
    serializer_class = PayRequestSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        pay_request = self.get_object()
        if pay_request.is_applied:
            return Response(
                {"error": "This payment request is already applied."},
                status=status.HTTP_400_BAD_REQUEST
            )
        pay_request.is_applied = True
        pay_request.save()
        pill = pay_request.pill
        pill.paid = True
        pill.status = 'p'
        pill.save()
        serializer = self.get_serializer(pay_request)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


class SpinWheelDiscountListCreateView(generics.ListCreateAPIView):
    queryset = SpinWheelDiscount.objects.all()
    serializer_class = SpinWheelDiscountSerializer
    # permission_classes = [IsAdminUser]

class SpinWheelDiscountRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SpinWheelDiscount.objects.all()
    serializer_class = SpinWheelDiscountSerializer
    # permission_classes = [IsAdminUser]








products.permissions.py :
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from products.models import Pill, PillAddress, PillItem

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow users to manage their own ratings
        return obj.user == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
    



class PillItemPermissionMixin:
    """Mixin to ensure pill items belong to the authenticated user"""
    
    def get_queryset(self):
        return PillItem.objects.filter(user=self.request.user)
    
    def check_pill_ownership(self, pill_id):
        """Check if the pill belongs to the authenticated user"""
        try:
            pill = Pill.objects.get(id=pill_id, user=self.request.user)
            return pill
        except Pill.DoesNotExist:
            raise PermissionDenied("You don't have permission to access this pill.")

    def check_address_ownership(self, address_id):
        """Check if the address belongs to a pill owned by the authenticated user"""
        try:
            address = PillAddress.objects.get(id=address_id, pill__user=self.request.user)
            return address
        except PillAddress.DoesNotExist:
            raise PermissionDenied("You don't have permission to access this address.")

products.filters.py :

from .models import Category, Pill, Product, ProductImage
from django_filters import rest_framework as filters
from django.db.models import Q, F, FloatField, Case, When,Exists, OuterRef
from django.utils import timezone
from .models import Product, CouponDiscount

class ProductFilter(filters.FilterSet):
    price_min = filters.NumberFilter(method='filter_by_discounted_price_min')
    price_max = filters.NumberFilter(method='filter_by_discounted_price_max')
    color = filters.CharFilter(method='filter_by_color')
    size = filters.CharFilter(method='filter_by_size')
    has_images = filters.BooleanFilter(method='filter_has_images')

    class Meta:
        model = Product
        fields = ['category', 'sub_category', 'brand', 'has_images','is_important']

    def filter_by_discounted_price_min(self, queryset, name, value):
        now = timezone.now()

        # Annotate the queryset with product discounts
        queryset = queryset.annotate(
            product_discount_price=Case(
                When(
                    Q(discounts__discount_start__lte=now) &
                    Q(discounts__discount_end__gte=now),
                    then=F('price') * (1 - F('discounts__discount') / 100)
                ),
                default=F('price'),
                output_field=FloatField()
            ),
            category_discount_price=Case(
                When(
                    Q(category__discounts__discount_start__lte=now) &
                    Q(category__discounts__discount_end__gte=now),
                    then=F('price') * (1 - F('category__discounts__discount') / 100)
                ),
                default=F('price'),
                output_field=FloatField()
            )
        ).annotate(
            final_price=Case(
                When(
                    product_discount_price__lt=F('category_discount_price'),
                    then=F('product_discount_price')
                ),
                default=F('category_discount_price'),
                output_field=FloatField()
            )
        )

        return queryset.filter(final_price__gte=value).distinct()

    def filter_by_discounted_price_max(self, queryset, name, value):
        now = timezone.now()

        # Same annotation logic as above
        queryset = queryset.annotate(
            product_discount_price=Case(
                When(
                    Q(discounts__discount_start__lte=now) &
                    Q(discounts__discount_end__gte=now),
                    then=F('price') * (1 - F('discounts__discount') / 100)
                ),
                default=F('price'),
                output_field=FloatField()
            ),
            category_discount_price=Case(
                When(
                    Q(category__discounts__discount_start__lte=now) &
                    Q(category__discounts__discount_end__gte=now),
                    then=F('price') * (1 - F('category__discounts__discount') / 100)
                ),
                default=F('price'),
                output_field=FloatField()
            )
        ).annotate(
            final_price=Case(
                When(
                    product_discount_price__lt=F('category_discount_price'),
                    then=F('product_discount_price')
                ),
                default=F('category_discount_price'),
                output_field=FloatField()
            )
        )

        return queryset.filter(final_price__lte=value).distinct()

    def filter_by_color(self, queryset, name, value):
        return queryset.filter(availabilities__color__name__iexact=value).distinct()

    def filter_by_size(self, queryset, name, value):
        return queryset.filter(availabilities__size__iexact=value).distinct()

    def filter_has_images(self, queryset, name, value):
        if value:
            # Filter products that have at least one related image
            return queryset.filter(Exists(ProductImage.objects.filter(product=OuterRef('pk'))))
        else:
            # Filter products that do not have any related images
            return queryset.filter(~Exists(ProductImage.objects.filter(product=OuterRef('pk'))))

    def filter_queryset(self, queryset):
        # Apply the filters first
        queryset = super().filter_queryset(queryset)
        # Get the `limit` parameter from the query string (default to 10 if not provided)
        limit = int(self.request.query_params.get('limit', 10))
        # Order by `date_added` and slice the queryset
        return queryset.order_by('-date_added')[:limit]
    
    
    
    
    
    
class CouponDiscountFilter(filters.FilterSet):
    available = filters.BooleanFilter(method='filter_available')

    class Meta:
        model = CouponDiscount
        fields = ['available']

    def filter_available(self, queryset, name, value):
        now = timezone.now()
        if value:
            return queryset.filter(
                available_use_times__gt=0,
                coupon_start__lte=now,
                coupon_end__gte=now
            )
        return queryset

class CategoryFilter(filters.FilterSet):
    has_image = filters.BooleanFilter(method='filter_has_image')

    class Meta:
        model = Category
        fields = ['has_image']

    def filter_has_image(self, queryset, name, value):
        if value:
            # Filter categories that have an image
            return queryset.filter(~Q(image__isnull=True) & ~Q(image__exact=''))
        else:
            # Filter categories that do not have an image
            return queryset.filter(Q(image__isnull=True) | Q(image__exact=''))
        
class PillFilter(filters.FilterSet):
    # Add a date range filter for the `date_added` field
    start_date = filters.DateFilter(field_name='date_added', lookup_expr='gte', label='Start Date')
    end_date = filters.DateFilter(field_name='date_added', lookup_expr='lte', label='End Date')

    class Meta:
        model = Pill
        fields = ['status', 'paid', 'pill_number', 'pilladdress__government', 'pilladdress__pay_method']
        
 
        
products.urls.py :
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Customer Endpoints
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('subcategories/', views.SubCategoryListView.as_view(), name='subcategory-list'),
    path('brands/', views.BrandListView.as_view(), name='brand-list'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<int:id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('last-products/', views.Last10ProductsListView.as_view(), name='last-products'),
    path('special-products/active/', views.ActiveSpecialProductsView.as_view(), name='special-products'),
    path('cart/', views.UserCartView.as_view(), name='user-cart'),
    path('cart/add/', views.PillItemCreateView.as_view(), name='cart-add'),
    path('cart/update/<int:pk>/', views.PillItemUpdateView.as_view(), name='cart-update'),
    path('cart/delete/<int:pk>/', views.PillItemDeleteView.as_view(), name='cart-delete'),
    path('pills/init/', views.PillCreateView.as_view(), name='pill-create'),
    path('pills/<int:id>/apply-coupon/', views.PillCouponApplyView.as_view(), name='pill-coupon-apply'),
    path('pills/<int:pill_id>/address-info/', views.PillAddressCreateUpdateView.as_view(), name='pill-address-create-update'),
    path('pills/<int:id>/', views.PillDetailView.as_view(), name='pill-detail'),
    path('user-pills/', views.UserPillsView.as_view(), name='user-pills'),
    path('ratings/', views.CustomerRatingListCreateView.as_view(), name='customer-rating-list-create'),
    path('ratings/<int:pk>/', views.CustomerRatingDetailView.as_view(), name='customer-rating-detail'),
    path('colors/', views.getColors.as_view(), name='color-list'),
    path('pay-requests/', views.PayRequestListCreateView.as_view(), name='pay-request-list-create'),
    path('discounts/active/', views.ProductsWithActiveDiscountAPIView.as_view(), name='products-with-discount'),
    path('loved-products/', views.LovedProductListCreateView.as_view(), name='loved-product-list-create'),
    path('loved-products/<int:pk>/', views.LovedProductRetrieveDestroyView.as_view(), name='loved-product-detail'),
    path('alerts/stock/', views.StockAlertCreateView.as_view(), name='stock-alert-create'),
    path('alerts/price-drop/', views.PriceDropAlertCreateView.as_view(), name='price-drop-alert-create'),
    path('alerts/my-alerts/', views.UserActiveAlertsView.as_view(), name='active-alerts'),
    path('alerts/mark-notified/<str:alert_type>/<int:alert_id>/', views.MarkAlertAsNotifiedView.as_view(), name='mark-alert-notified'),
    path('products/new-arrivals/', views.NewArrivalsView.as_view(), name='new-arrivals'),
    path('products/best-sellers/', views.BestSellersView.as_view(), name='best-sellers'),
    path('products/frequently-bought-together/', views.FrequentlyBoughtTogetherView.as_view(), name='frequently-bought-together'),
    path('products/recommendations/', views.ProductRecommendationsView.as_view(), name='recommendations'),
    path('spin-wheel/', views.SpinWheelView.as_view(), name='spin-wheel'),
    path('spin-wheel/history/', views.SpinWheelHistoryView.as_view(), name='spin-wheel-history'),
    path('products/<int:product_id>/availabilities/', views.ProductAvailabilitiesView.as_view(), name='product-availabilities'),

    # Admin Endpoints
    path('dashboard/categories/', views.CategoryListCreateView.as_view(), name='admin-category-list-create'),
    path('dashboard/categories/<int:pk>/', views.CategoryRetrieveUpdateDestroyView.as_view(), name='admin-category-detail'),
    path('dashboard/subcategories/', views.SubCategoryListCreateView.as_view(), name='admin-subcategory-list-create'),
    path('dashboard/subcategories/<int:pk>/', views.SubCategoryRetrieveUpdateDestroyView.as_view(), name='admin-subcategory-detail'),
    path('dashboard/brands/', views.BrandListCreateView.as_view(), name='admin-brand-list-create'),
    path('dashboard/brands/<int:pk>/', views.BrandRetrieveUpdateDestroyView.as_view(), name='admin-brand-detail'),
    path('dashboard/colors/', views.ColorListCreateView.as_view(), name='admin-color-list-create'),
    path('dashboard/colors/<int:id>/', views.ColorRetrieveUpdateDestroyView.as_view(), name='admin-color-detail'),
    path('dashboard/products/', views.ProductListCreateView.as_view(), name='admin-product-list-create'),
    path('dashboard/products-breifed/', views.ProductListBreifedView.as_view(), name='admin-product-list-breifed'),
    path('dashboard/products/<int:pk>/', views.ProductRetrieveUpdateDestroyView.as_view(), name='admin-product-detail'),
    path('dashboard/product-images/', views.ProductImageListCreateView.as_view(), name='admin-product-image-list-create'),
    path('dashboard/product-images/bulk/', views.ProductImageBulkCreateView.as_view(), name='admin-product-image-bulk-create'),
    path('dashboard/product-images/<int:pk>/', views.ProductImageDetailView.as_view(), name='admin-product-image-detail'),
    path('dashboard/product-descriptions/', views.ProductDescriptionListCreateView.as_view(), name='admin-product-description-list-create'),
    path('dashboard/product-descriptions/bulk/', views.ProductDescriptionBulkCreateView.as_view(), name='admin-product-description-bulk-create'),
    path('dashboard/product-descriptions/<int:pk>/', views.ProductDescriptionRetrieveUpdateDestroyView.as_view(), name='admin-product-description-detail'),
    path('dashboard/special-products/', views.SpecialProductListCreateView.as_view(), name='admin-special-product-list-create'),
    path('dashboard/special-products/<int:pk>/', views.SpecialProductRetrieveUpdateDestroyView.as_view(), name='admin-special-product-detail'),
    path('dashboard/pills/', views.PillListCreateView.as_view(), name='admin-pill-list-create'),
    path('dashboard/pills/<int:pk>/', views.PillRetrieveUpdateDestroyView.as_view(), name='admin-pill-detail'),
    path('dashboard/discounts/', views.DiscountListCreateView.as_view(), name='admin-discount-list-create'),
    path('dashboard/discounts/<int:pk>/', views.DiscountRetrieveUpdateDestroyView.as_view(), name='admin-discount-detail'),
    path('dashboard/coupons/', views.CouponListCreateView.as_view(), name='admin-coupon-list-create'),
    path('dashboard/coupons/<int:pk>/', views.Coupfrom django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Customer Endpoints
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('subcategories/', views.SubCategoryListView.as_view(), name='subcategory-list'),
    path('brands/', views.BrandListView.as_view(), name='brand-list'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<int:id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('last-products/', views.Last10ProductsListView.as_view(), name='last-products'),
    path('special-products/active/', views.ActiveSpecialProductsView.as_view(), name='special-products'),
    path('cart/', views.UserCartView.as_view(), name='user-cart'),
    path('cart/add/', views.PillItemCreateView.as_view(), name='cart-add'),
    path('cart/update/<int:pk>/', views.PillItemUpdateView.as_view(), name='cart-update'),
    path('cart/delete/<int:pk>/', views.PillItemDeleteView.as_view(), name='cart-delete'),
    path('pills/init/', views.PillCreateView.as_view(), name='pill-create'),
    path('pills/<int:id>/apply-coupon/', views.PillCouponApplyView.as_view(), name='pill-coupon-apply'),
    path('pills/<int:pill_id>/address-info/', views.PillAddressCreateUpdateView.as_view(), name='pill-address-create-update'),
    path('pills/<int:id>/', views.PillDetailView.as_view(), name='pill-detail'),
    path('user-pills/', views.UserPillsView.as_view(), name='user-pills'),
    path('ratings/', views.CustomerRatingListCreateView.as_view(), name='customer-rating-list-create'),
    path('ratings/<int:pk>/', views.CustomerRatingDetailView.as_view(), name='customer-rating-detail'),
    path('colors/', views.getColors.as_view(), name='color-list'),
    path('pay-requests/', views.PayRequestListCreateView.as_view(), name='pay-request-list-create'),
    path('discounts/active/', views.ProductsWithActiveDiscountAPIView.as_view(), name='products-with-discount'),
    path('loved-products/', views.LovedProductListCreateView.as_view(), name='loved-product-list-create'),
    path('loved-products/<int:pk>/', views.LovedProductRetrieveDestroyView.as_view(), name='loved-product-detail'),
    path('alerts/stock/', views.StockAlertCreateView.as_view(), name='stock-alert-create'),
    path('alerts/price-drop/', views.PriceDropAlertCreateView.as_view(), name='price-drop-alert-create'),
    path('alerts/my-alerts/', views.UserActiveAlertsView.as_view(), name='active-alerts'),
    path('alerts/mark-notified/<str:alert_type>/<int:alert_id>/', views.MarkAlertAsNotifiedView.as_view(), name='mark-alert-notified'),
    path('products/new-arrivals/', views.NewArrivalsView.as_view(), name='new-arrivals'),
    path('products/best-sellers/', views.BestSellersView.as_view(), name='best-sellers'),
    path('products/frequently-bought-together/', views.FrequentlyBoughtTogetherView.as_view(), name='frequently-bought-together'),
    path('products/recommendations/', views.ProductRecommendationsView.as_view(), name='recommendations'),
    path('spin-wheel/', views.SpinWheelView.as_view(), name='spin-wheel'),
    path('spin-wheel/history/', views.SpinWheelHistoryView.as_view(), name='spin-wheel-history'),
    path('products/<int:product_id>/availabilities/', views.ProductAvailabilitiesView.as_view(), name='product-availabilities'),

    # Admin Endpoints
    path('dashboard/categories/', views.CategoryListCreateView.as_view(), name='admin-category-list-create'),
    path('dashboard/categories/<int:pk>/', views.CategoryRetrieveUpdateDestroyView.as_view(), name='admin-category-detail'),
    path('dashboard/subcategories/', views.SubCategoryListCreateView.as_view(), name='admin-subcategory-list-create'),
    path('dashboard/subcategories/<int:pk>/', views.SubCategoryRetrieveUpdateDestroyView.as_view(), name='admin-subcategory-detail'),
    path('dashboard/brands/', views.BrandListCreateView.as_view(), name='admin-brand-list-create'),
    path('dashboard/brands/<int:pk>/', views.BrandRetrieveUpdateDestroyView.as_view(), name='admin-brand-detail'),
    path('dashboard/colors/', views.ColorListCreateView.as_view(), name='admin-color-list-create'),
    path('dashboard/colors/<int:id>/', views.ColorRetrieveUpdateDestroyView.as_view(), name='admin-color-detail'),
    path('dashboard/products/', views.ProductListCreateView.as_view(), name='admin-product-list-create'),
    path('dashboard/products-breifed/', views.ProductListBreifedView.as_view(), name='admin-product-list-breifed'),
    path('dashboard/products/<int:pk>/', views.ProductRetrieveUpdateDestroyView.as_view(), name='admin-product-detail'),
    path('dashboard/product-images/', views.ProductImageListCreateView.as_view(), name='admin-product-image-list-create'),
    path('dashboard/product-images/bulk/', views.ProductImageBulkCreateView.as_view(), name='admin-product-image-bulk-create'),
    path('dashboard/product-images/<int:pk>/', views.ProductImageDetailView.as_view(), name='admin-product-image-detail'),
    path('dashboard/product-descriptions/', views.ProductDescriptionListCreateView.as_view(), name='admin-product-description-list-create'),
    path('dashboard/product-descriptions/bulk/', views.ProductDescriptionBulkCreateView.as_view(), name='admin-product-description-bulk-create'),
    path('dashboard/product-descriptions/<int:pk>/', views.ProductDescriptionRetrieveUpdateDestroyView.as_view(), name='admin-product-description-detail'),
    path('dashboard/special-products/', views.SpecialProductListCreateView.as_view(), name='admin-special-product-list-create'),
    path('dashboard/special-products/<int:pk>/', views.SpecialProductRetrieveUpdateDestroyView.as_view(), name='admin-special-product-detail'),
    path('dashboard/pills/', views.PillListCreateView.as_view(), name='admin-pill-list-create'),
    path('dashboard/pills/<int:pk>/', views.PillRetrieveUpdateDestroyView.as_view(), name='admin-pill-detail'),
    path('dashboard/discounts/', views.DiscountListCreateView.as_view(), name='admin-discount-list-create'),
    path('dashboard/discounts/<int:pk>/', views.DiscountRetrieveUpdateDestroyView.as_view(), name='admin-discount-detail'),
    path('dashboard/coupons/', views.CouponListCreateView.as_view(), name='admin-coupon-list-create'),
    path('dashboard/coupons/<int:pk>/', views.CouponRetrieveUpdateDestroyView.as_view(), name='admin-coupon-detail'),
    path('dashboard/shipping/', views.ShippingListCreateView.as_view(), name='admin-shipping-list-create'),
    path('dashboard/shipping/<int:pk>/', views.ShippingRetrieveUpdateDestroyView.as_view(), name='admin-shipping-detail'),
    path('dashboard/ratings/', views.RatingListCreateView.as_view(), name='admin-rating-list-create'),
    path('dashboard/ratings/<int:pk>/', views.RatingDetailView.as_view(), name='admin-rating-detail'),
    path('dashboard/product-availabilities/', views.ProductAvailabilityListCreateView.as_view(), name='admin-product-availability-list-create'),
    path('dashboard/product-availabilities/<int:pk>/', views.ProductAvailabilityDetailView.as_view(), name='admin-product-availability-detail'),
    path('dashboard/pay-requests/create/', views.AdminPayRequestCreateView.as_view(), name='admin-pay-request-create'),
    path('dashboard/pay-requests/<int:id>/apply/', views.ApplyPayRequestView.as_view(), name='admin-pay-request-apply'),
    path('dashboard/spin-wheel/', views.SpinWheelDiscountListCreateView.as_view(), name='spin-wheel-list-create'),
    path('dashboard/spin-wheel/<int:pk>/', views.SpinWheelDiscountRetrieveUpdateDestroyView.as_view(), name='spin-wheel-detail'),

]onRetrieveUpdateDestroyView.as_view(), name='admin-coupon-detail'), 
    path('dashboard/shipping/', views.ShippingListCreateView.as_view(), name='admin-shipping-list-create'),
    path('dashboard/shipping/<int:pk>/', views.ShippingRetrieveUpdateDestroyView.as_view(), name='admin-shipping-detail'),
    path('dashboard/ratings/', views.RatingListCreateView.as_view(), name='admin-rating-list-create'),
    path('dashboard/ratings/<int:pk>/', views.RatingDetailView.as_view(), name='admin-rating-detail'),
    path('dashboard/product-availabilities/', views.ProductAvailabilityListCreateView.as_view(), name='admin-product-availability-list-create'),
    path('dashboard/product-availabilities/<int:pk>/', views.ProductAvailabilityDetailView.as_view(), name='admin-product-availability-detail'),
    path('dashboard/pay-requests/create/', views.AdminPayRequestCreateView.as_view(), name='admin-pay-request-create'),
    path('dashboard/pay-requests/<int:id>/apply/', views.ApplyPayRequestView.as_view(), name='admin-pay-request-apply'),
    path('dashboard/spin-wheel/', views.SpinWheelDiscountListCreateView.as_view(), name='spin-wheel-list-create'),
    path('dashboard/spin-wheel/<int:pk>/', views.SpinWheelDiscountRetrieveUpdateDestroyView.as_view(), name='spin-wheel-detail'),

]