import random
import string
from accounts.models import User
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from products.utils import send_whatsapp_message
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
        # Generate a random 20-digit string
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

    # apply the best discount of all discounts (price_after_product_discount OR price_after_category_discount)
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
        return sum(availability.quantity for availability in self.availabilities.all())

    def available_colors(self):
        colors = set()
        for availability in self.availabilities.all():
            if availability.color:
                colors.add((availability.color.id, availability.color.name))
        # Convert the set to a list of dictionaries
        return [{"color_id": color_id, "color_name": color_name} for color_id, color_name in colors]

    def available_sizes(self):
        return [availability.size for availability in self.availabilities.all() if availability.size is not None]

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
        null=True, blank=True  
    )
    quantity = models.PositiveIntegerField()
    native_price = models.FloatField(
        default=0.0,
        help_text="The original price the owner paid for this product batch"
    )
    date_added = models.DateTimeField(auto_now_add=True)

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

class Rating(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    user = models.ForeignKey(
        User,  # Assuming you have a User model
        on_delete=models.CASCADE
    )
    star_number = models.IntegerField()
    review = models.CharField(max_length=300, default="No review comment")
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.star_number} stars for {self.product.name} by {self.user.username}"


    def star_ranges(self):
        return range(int(self.star_number)), range(5 - int(self.star_number))

class Shipping(models.Model):
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2)
    shipping_price = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.get_government_display()} - {self.shipping_price}"

class PillItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pill_items')
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, choices=SIZES_CHOICES, null=True)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} - {self.size} - {self.color.name if self.color else 'No Color'}"

class Pill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pills')
    items = models.ManyToManyField(PillItem, related_name='pills')  # Updated to relate to PillItem
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1, default='i')
    date_added = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    coupon = models.ForeignKey('CouponDiscount', on_delete=models.SET_NULL, null=True, blank=True, related_name='pills')
    coupon_discount = models.FloatField(default=0.0)  # Store the coupon discount as a field
    pill_number = models.CharField(
        max_length=20, 
        editable=False,
        unique=True,
        default=generate_pill_number
    )

    def save(self, *args, **kwargs):
        # Generate pill number if not set
        if not self.pill_number:
            self.pill_number = generate_pill_number()
        
        # Check if this is a new pill
        is_new = not self.pk
        
        # First save to create the pill
        super().save(*args, **kwargs)
        
        if is_new:
            # Log the initial status
            PillStatusLog.objects.create(pill=self, status=self.status)
        else:
            # Check if status changed
            old_pill = Pill.objects.get(pk=self.pk)
            if old_pill.status != self.status:
                # Log the status change
                status_log, created = PillStatusLog.objects.get_or_create(
                    pill=self, 
                    status=self.status
                )
                if not created:
                    status_log.changed_at = timezone.now()
                    status_log.save()
            
            # Handle delivered status
            if old_pill.status != 'd' and self.status == 'd':
                self.process_delivery()
        
        # Handle payment status
        if self.paid and self.status != 'p':
            self.status = 'p'
            super().save(*args, **kwargs)
            self.send_payment_notification()

    def process_delivery(self):
        """Process items when pill is marked as delivered"""
        for item in self.items.all():
            # Create sales record
            ProductSales.objects.create(
                product=item.product,
                quantity=item.quantity,
                size=item.size,
                color=item.color,
                price_at_sale=item.product.discounted_price(),
                pill=self
            )
            
            # Decrease product availability
            try:
                availability = ProductAvailability.objects.get(
                    product=item.product,
                    size=item.size,
                    color=item.color
                )
                if availability.quantity < item.quantity:
                    raise ValidationError(f"Not enough inventory for {item.product.name}")
                availability.quantity -= item.quantity
                availability.save()
            except ProductAvailability.DoesNotExist:
                raise ValidationError(f"No matching availability for {item.product.name}")

    def send_payment_notification(self):
        """Send payment confirmation if phone exists"""
        if hasattr(self, 'pilladdress') and self.pilladdress.phone:
            prepare_whatsapp_message(self.pilladdress.phone, self)

    class Meta:
        verbose_name_plural = 'Bills'

    def __str__(self):
        return f"Pill ID: {self.id} - Status: {self.get_status_display()} - Date: {self.date_added}"

    # 1. Price without coupons (sum of product.discounted_price() * quantity)
    def price_without_coupons(self):
        return sum(item.product.discounted_price() * item.quantity for item in self.items.all())

    # 2. Calculate coupon discount (dynamically calculate based on the coupon)
    def calculate_coupon_discount(self):
        if self.coupon:
            # Check if the coupon is valid (within start and end dates)
            now = timezone.now()
            if self.coupon.coupon_start <= now <= self.coupon.coupon_end:
                return self.coupon.discount_value
        return 0.0  # No coupon or invalid coupon

    # 3. Price after coupon discount
    def price_after_coupon_discount(self):
        return self.price_without_coupons() - (self.coupon_discount or 0)

    # 4. Shipping price (based on PillAddress.government)
    def shipping_price(self):
        if hasattr(self, 'pilladdress'):
            try:
                shipping = Shipping.objects.filter(government=self.pilladdress.government).first()
                return shipping.shipping_price
            except Shipping.DoesNotExist:
                return 0.0
        return 0.0  # Default shipping price if PillAddress is not set

    # 5. Final price (price_after_coupon_discount + shipping_price)
    def final_price(self):
        return self.price_after_coupon_discount() + self.shipping_price()

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

class CouponDiscount(models.Model):
    coupon = models.CharField(max_length=100, blank=True, null=True, editable=False)
    discount_value = models.FloatField(null=True, blank=True)
    coupon_start = models.DateTimeField(null=True, blank=True)
    coupon_end = models.DateTimeField(null=True, blank=True)
    available_use_times = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.coupon:
            self.coupon = create_random_coupon()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.coupon

class PillAddress(models.Model):
    pill = models.OneToOneField(Pill, on_delete=models.CASCADE, related_name='pilladdress')
    name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField( null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2)
    pay_method = models.CharField(choices=PAYMENT_CHOICES, max_length=2 , default="c")
    def __str__(self):
        return f"{self.name} - {self.address}"

class PillStatusLog(models.Model):
    pill = models.ForeignKey(Pill, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pill.id} - {self.get_status_display()} at {self.changed_at}"

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

#------------- Alert for low stock and proce drop -------------#

class StockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ['product', 'user'],  # For authenticated users
            ['product', 'email']  # For anonymous users
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
            ['product', 'user'],  # For authenticated users
            ['product', 'email']  # For anonymous users
        ]


#------------- Spin the wheel-------------#

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
    # Prepare the WhatsApp message
    message = (
        f"مرحباً {pill.user.username}،\n\n"
        f"تم استلام طلبك بنجاح.\n\n"
        f"رقم الطلب: {pill.pill_number}\n"
    )

    # Send WhatsApp message
    send_whatsapp_message(
        phone_number=phone_number,
        message=message
    )
