import random
import string
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum
from products.utils import send_whatsapp_message
from accounts.models import YEAR_CHOICES, User
from core import settings
from django.utils import timezone
from django.utils.html import format_html
import logging

logger = logging.getLogger(__name__)

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
    product_type = [
        ('book', 'Book'),
        ('product', 'Product'),
    ]
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)  
    type = models.CharField(
        max_length=20,
        choices=product_type,
        default='product',
        help_text="Type of the product"
    )
    class Meta:
        ordering = ['-created_at']  

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    created_at = models.DateTimeField(default=timezone.now)  

    class Meta:
        ordering = ['-created_at']  
        verbose_name_plural = 'Sub Categories'

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)  

    class Meta:
        ordering = ['-created_at']  

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name
    
class Teacher(models.Model):
    name = models.CharField(max_length=150)
    bio = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='teachers/', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='teachers')
    facebook = models.CharField(max_length=200, null=True, blank=True)
    instagram = models.CharField(max_length=200, null=True, blank=True)
    twitter = models.CharField(max_length=200, null=True, blank=True)
    linkedin = models.CharField(max_length=200, null=True, blank=True)
    youtube = models.CharField(max_length=200, null=True, blank=True)
    whatsapp = models.CharField(max_length=200, null=True, blank=True)
    tiktok = models.CharField(max_length=200, null=True, blank=True)
    telegram = models.CharField(max_length=200, null=True, blank=True)
    website = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    product_type = [
            ('book', 'Book'),
            ('product', 'Product'),
        ]
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
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
    base_image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        help_text="Main image for the product"
    )

    type = models.CharField(
        max_length=20,
        choices=product_type,
        default='product',
        help_text="Type of the product"
    )
    year = models.CharField(
        max_length=20,
        choices=YEAR_CHOICES,
        null=True,
        blank=True,
    )
    
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
        if self.base_image:
            return self.base_image  # This should return a FileField/ImageField object

        images = self.images.all()
        if images.exists():
            # Make sure this returns a FileField/ImageField object
            return random.choice(images).image

        return None  # Explicitly return None if no image is found

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

    class Meta:
        ordering = ['-date_added']
        
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
    
class BestProduct(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='best_products'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Ordering priority (higher numbers come first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Show this product"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order', '-created_at']


    def __str__(self):
        return self.product.name

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='product_images/')
    created_at = models.DateTimeField(default=timezone.now)  

    class Meta:
        ordering = ['-created_at']  

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
    created_at = models.DateTimeField(default=timezone.now)  # Added

    class Meta:
        ordering = ['-created_at']  # Added

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
        ordering = ['-date_added'] 

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color.name if self.color else 'No Color'}"

# class ProductSales(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
#     quantity = models.PositiveIntegerField()
#     size = models.CharField(max_length=50, null=True, blank=True)
#     color = models.ForeignKey(Color, on_delete=models.CASCADE, null=True, blank=True)
#     price_at_sale = models.FloatField()
#     date_sold = models.DateTimeField(auto_now_add=True)
#     pill = models.ForeignKey('Pill', on_delete=models.CASCADE, related_name='product_sales')

#     def __str__(self):
#         return f"{self.product.name} - {self.quantity} sold on {self.date_sold}"

class Shipping(models.Model):
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2)
    shipping_price = models.FloatField(default=0.0)
    

    def __str__(self):
        return f"{self.get_government_display()} - {self.shipping_price}"

    class Meta:
        ordering = ['government']  

class PillItem(models.Model):
    pill = models.ForeignKey('Pill', on_delete=models.CASCADE, null=True, blank=True, related_name='pill_items')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pill_items', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pill_items')
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, choices=SIZES_CHOICES, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    # New fields for sales analysis
    native_price_at_sale = models.FloatField(null=True, blank=True)
    price_at_sale = models.FloatField(null=True, blank=True)
    date_sold = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_added']
        unique_together = ['user', 'product', 'size', 'color', 'status', 'pill']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['date_sold']),
            models.Index(fields=['product', 'status']),
        ]

    def save(self, *args, **kwargs):
        # Set date_sold when status changes to 'paid' or 'delivered'
        if self.status in ['p', 'd'] and not self.date_sold:
            self.date_sold = timezone.now()
            
        # Set prices if not already set
        if self.status in ['p', 'd'] and not self.price_at_sale:
            self.price_at_sale = self.product.discounted_price()
            
        if self.status in ['p', 'd'] and not self.native_price_at_sale:
            availability = self.product.availabilities.filter(
                size=self.size,
                color=self.color
            ).first()
            self.native_price_at_sale = availability.native_price if availability else 0
            
        super().save(*args, **kwargs)
     



class Pill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pills')
    items = models.ManyToManyField(PillItem, related_name='pills')
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1, default='i')
    date_added = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    coupon = models.ForeignKey('CouponDiscount', on_delete=models.SET_NULL, null=True, blank=True, related_name='pills')
    coupon_discount = models.FloatField(default=0.0)  # Stores discount amount
    gift_discount = models.ForeignKey('PillGift', on_delete=models.SET_NULL, null=True, blank=True, related_name='pills')
    tracking_number = models.CharField(max_length=50, null=True, blank=True)
    pill_number = models.CharField(max_length=20, editable=False, unique=True, default=generate_pill_number)
    
    # Khazenly fields
    is_shipped = models.BooleanField(default=False)
    khazenly_data = models.JSONField(null=True, blank=True)
    # Fawaterak fields
    fawaterak_invoice_key = models.CharField(max_length=100, null=True, blank=True)
    fawaterak_data = models.JSONField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.pill_number:
            self.pill_number = generate_pill_number()

        # Track if is_shipped is being changed
        is_new_shipped = False
        if self.pk:
            try:
                old_pill = Pill.objects.get(pk=self.pk)
                if not old_pill.is_shipped and self.is_shipped:
                    is_new_shipped = True
            except Pill.DoesNotExist:
                pass
        elif self.is_shipped:
            is_new_shipped = True

        is_new = not self.pk
        old_status = None if is_new else Pill.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        if is_new:
            PillStatusLog.objects.create(pill=self, status=self.status)
            for item in self.items.all():
                item.status = self.status
                if self.status in ['p', 'd']:
                    self._update_pill_item_prices(item)
                item.save()
            self.apply_gift_discount()
        else:
            if old_status != self.status:
                status_log, created = PillStatusLog.objects.get_or_create(
                    pill=self,
                    status=self.status
                )
                if not created:
                    status_log.changed_at = timezone.now()
                    status_log.save()

                if self.status in ['c', 'r'] and old_status == 'd':
                    self.restore_inventory()

                self.items.update(status=self.status)

                if self.status in ['p', 'd']:
                    for item in self.items.all():
                        self._update_pill_item_prices(item)
                        item.save()

                if self.status != 'd' and not self.paid:
                    self.apply_gift_discount()

                if old_status != 'd' and self.status == 'd':
                    self.process_delivery()

                if self.paid and self.status != 'p':
                    super().save(*args, **kwargs)
                    self.send_payment_notification()

        # Create Khazenly order if is_shipped was just set to True
        if is_new_shipped:
            self._create_khazenly_order()

    def _create_khazenly_order(self):
        """Create Khazenly order when is_shipped is set to True"""
        try:
            from services.khazenly_service import khazenly_service  # Fixed import
            
            logger.info(f"Creating Khazenly order for pill {self.pill_number}")
            
            result = khazenly_service.create_order(self)
            
            if result['success']:
                # Update the model without triggering save again
                Pill.objects.filter(pk=self.pk).update(khazenly_data=result['data'])
                logger.info(f"✓ Successfully created Khazenly order for pill {self.pill_number}")
            else:
                logger.error(f"✗ Failed to create Khazenly order for pill {self.pill_number}: {result['error']}")
                
        except Exception as e:
            logger.error(f"✗ Error creating Khazenly order for pill {self.pill_number}: {str(e)}")
    

    @property
    def khazenly_order_number(self):
        """Get Khazenly order number from stored data"""
        if self.khazenly_data:
            return self.khazenly_data.get('orderNumber', self.pill_number)
        return None

    @property
    def has_khazenly_order(self):
        """Check if this pill has a Khazenly order"""
        return bool(self.khazenly_data)

    @property
    def khazenly_status(self):
        """Get Khazenly order status"""
        if self.has_khazenly_order:
            return "Created"
        elif self.is_shipped:
            return "Pending"
        else:
            return "Not Shipped"
    def create_fawry_payment(self):
        """Create Fawry payment invoice"""
        from services.fawaterak_service import FawaterakService
        service = FawaterakService()
        result, error = service.create_fawry_invoice(self)
        
        if result:
            self.fawaterak_invoice_key = result.get('invoice_key')
            self.fawaterak_data = result
            self.save()
            return result.get('invoice_url')
        
        logger.error(f"Failed to create Fawry payment: {error}")
        return None
    def create_fawaterak_invoice(self):
        """Create a Fawaterak Fawry invoice for this pill"""
        from services.fawaterak_service import FawaterakService
        
        fawaterak = FawaterakService()
        invoice_data, error = fawaterak.create_fawry_invoice(self)
        
        if invoice_data:
            self.fawaterak_invoice_key = invoice_data.get('invoice_key')
            self.fawaterak_data = invoice_data
            self.save(update_fields=['fawaterak_invoice_key', 'fawaterak_data'])
            return invoice_data.get('invoice_url')
        return None

    def check_fawaterak_payment(self):
        """Check payment status with Fawaterak"""
        if not self.fawaterak_invoice_key:
            return None, "No Fawaterak invoice associated"
            
        from services.fawaterak_service import FawaterakService
        
        fawaterak = FawaterakService()
        payment_data, error = fawaterak.check_payment_status(self.fawaterak_invoice_key)
        
        if payment_data:
            # Update payment status if needed
            if payment_data.get('payment_status') == 'paid' and not self.paid:
                self.paid = True
                self.status = 'p'  # Set to paid status
                self.save(update_fields=['paid', 'status'])
            return payment_data, None
        return None, error

    @property
    def fawaterak_payment_url(self):
        """Get Fawaterak payment URL if exists"""
        if self.fawaterak_invoice_key and self.fawaterak_data:
            return self.fawaterak_data.get('invoice_url')
        return None

    @property
    def fawaterak_payment_status(self):
        """Get Fawaterak payment status"""
        if not self.fawaterak_invoice_key:
            return "No invoice"
        if self.paid:
            return "Paid"
        return "Pending"

    def _update_pill_item_prices(self, item):
        """Helper method to update prices and sale date on a pill item"""
        if item.status in ['p', 'd']:
            if not item.date_sold:
                item.date_sold = timezone.now()

            if not item.price_at_sale:
                item.price_at_sale = item.product.discounted_price()

            if not item.native_price_at_sale:
                availability = item.product.availabilities.filter(
                    size=item.size,
                    color=item.color
                ).first()
                item.native_price_at_sale = availability.native_price if availability else 0

    def restore_inventory(self):
        """Restore inventory quantities for all items in the pill"""
        with transaction.atomic():
            for item in self.items.all():
                try:
                    availability = ProductAvailability.objects.select_for_update().get(
                        product=item.product,
                        size=item.size,
                        color=item.color
                    )
                    availability.quantity += item.quantity
                    availability.save()
                except ProductAvailability.DoesNotExist:
                    continue

    def process_delivery(self):
        """Process items when pill is marked as delivered"""
        with transaction.atomic():
            for item in self.items.all():
                try:
                    color = item.color if item.color else None
                    availability = ProductAvailability.objects.select_for_update().get(
                        product=item.product,
                        size=item.size,
                        color=color
                    )
                    if availability.quantity < item.quantity:
                        raise ValidationError(
                            f"Not enough inventory for {item.product.name} "
                            f"(Size: {item.size}, Color: {item.color.name if item.color else 'N/A'}). "
                            f"Required: {item.quantity}, Available: {availability.quantity}"
                        )
                    availability.quantity -= item.quantity
                    availability.save()
                    self._update_pill_item_prices(item)
                    item.save()
                except ProductAvailability.DoesNotExist:
                    raise ValidationError(
                        f"Inventory record for {item.product.name} "
                        f"(Size: {item.size}, Color: {item.color.name if item.color else 'N/A'}) not found."
                    )

    def send_payment_notification(self):
        """Send payment confirmation if phone exists"""
        if hasattr(self, 'pilladdress') and self.pilladdress.phone:
            prepare_whatsapp_message(self.pilladdress.phone, self)

    def price_without_coupons_or_gifts(self):
        return sum(item.product.discounted_price() * item.quantity for item in self.items.all())

    def calculate_coupon_discount(self):
        if self.coupon:
            now = timezone.now()
            if self.coupon.coupon_start <= now <= self.coupon.coupon_end:
                return self.price_without_coupons_or_gifts() * (self.coupon.discount_value / 100)
        return 0.0

    def calculate_gift_discount(self):
        if self.gift_discount and self.gift_discount.is_available(self.price_without_coupons_or_gifts()):
            return self.price_without_coupons_or_gifts() * (self.gift_discount.discount_value / 100)
        return 0.0

    def shipping_price(self):
        if hasattr(self, 'pilladdress'):
            try:
                shipping = Shipping.objects.filter(government=self.pilladdress.government).first()
                return shipping.shipping_price if shipping else 0.0
            except:
                return 0.0
        return 0.0

    def final_price(self):
        base_price = self.price_without_coupons_or_gifts()
        gift_discount = self.calculate_gift_discount()
        coupon_discount = self.calculate_coupon_discount()
        return max(0, base_price - gift_discount - coupon_discount) + self.shipping_price()

    def apply_gift_discount(self):
        """Apply the best active PillGift discount based on total price."""
        if self.paid or self.status == 'd':
            self.gift_discount = None
            self.save()
            return None

        total = self.price_without_coupons_or_gifts()
        if total <= 0:
            self.gift_discount = None
            self.save()
            return None

        applicable_gifts = PillGift.objects.filter(
            is_active=True,
            min_order_value__lte=total
        ).filter(
            models.Q(max_order_value__isnull=True) | models.Q(max_order_value__gte=total)
        ).filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=timezone.now())
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
        ).order_by('-discount_value', '-id')

        if self.gift_discount and not self.gift_discount.is_available(total):
            self.gift_discount = None

        gift = applicable_gifts.first()
        if gift:
            self.gift_discount = gift
            self.save()
            return gift
        if not self.gift_discount:
            self.save()
        return None

    class Meta:
        verbose_name_plural = 'Bills'
        ordering = ['-date_added']

    def __str__(self):
        return f"Pill ID: {self.id} - Status: {self.get_status_display()} - Date: {self.date_added}"

class PillAddress(models.Model):
    pill = models.OneToOneField(Pill, on_delete=models.CASCADE, related_name='pilladdress')
    name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    pay_method = models.CharField(choices=PAYMENT_CHOICES, max_length=2, default="c")
    created_at = models.DateTimeField(default=timezone.now)
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.address}"

class PillStatusLog(models.Model):
    pill = models.ForeignKey(Pill, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(choices=PILL_STATUS_CHOICES, max_length=1)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at'] 

    def __str__(self):
        return f"{self.pill.id} - {self.get_status_display()} at {self.changed_at}"
    
class CouponDiscount(models.Model):
    coupon = models.CharField(max_length=100, blank=True, null=True, editable=False)
    discount_value = models.FloatField(null=True, blank=True)
    coupon_start = models.DateTimeField(null=True, blank=True)
    coupon_end = models.DateTimeField(null=True, blank=True)
    available_use_times = models.PositiveIntegerField(default=1)
    is_wheel_coupon = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    min_order_value = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.coupon:
            self.coupon = create_random_coupon()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.coupon

    class Meta:
        ordering = ['-created_at']

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

    class Meta:
        ordering = ['-date_added'] 

class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='discounts')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='discounts')
    discount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    discount_start = models.DateTimeField()
    discount_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

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
    class Meta:
        ordering = ['-date'] 

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
        ordering = ['-created_at']

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
        ordering = ['-created_at'] 

class SpinWheelDiscount(models.Model):
    name = models.CharField(max_length=100)
    discount_value = models.FloatField(
        default=0.0,
        help_text="Discount value for the coupon created upon winning"
    )
    probability = models.FloatField(
        default=0.1,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Probability of winning (0 to 1)"
    )
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    min_order_value = models.FloatField(
        default=0,
        help_text="Minimum order value to claim the prize"
    )
    max_winners = models.PositiveIntegerField(
        default=100,
        help_text="Maximum number of users who can win this discount"
    )
    created_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.name} (Winners: {self.winner_count()}/{self.max_winners})"

    class Meta:
        ordering = ['-created_at']
    def is_available(self):
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date and
            self.winner_count() < self.max_winners
        )

    def winner_count(self):
        return SpinWheelResult.objects.filter(spin_wheel=self, coupon__isnull=False).count()

class SpinWheelResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    spin_wheel = models.ForeignKey(SpinWheelDiscount, on_delete=models.CASCADE)
    coupon = models.ForeignKey(CouponDiscount, null=True, blank=True, on_delete=models.SET_NULL)
    spin_date_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'spin_wheel', 'spin_date_time']
        ordering = ['-spin_date_time']

    def __str__(self):
        return f"{self.user.username} spun {self.spin_wheel.name} on {self.spin_date_time}"

class SpinWheelSettings(models.Model):
    daily_spin_limit = models.PositiveIntegerField(
        default=1,
        help_text="Maximum spins per user per day"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Spin Wheel Settings"
        verbose_name_plural = "Spin Wheel Settings"

    def __str__(self):
        return f"Daily Spin Limit: {self.daily_spin_limit}"

    @classmethod
    def get_settings(cls):
        return cls.objects.first() or cls.objects.create()

class PillGift(models.Model):
    discount_value = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (0-100)"
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Start date the gift becomes available (null means always available until end_date)"
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End date of the gift (null means available indefinitely from start_date)"
    )
    is_active = models.BooleanField(default=True)
    min_order_value = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum order value to apply the gift"
    )
    max_order_value = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum order value to apply the gift (optional)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    class Meta:
        verbose_name = "Pill Gift"
        verbose_name_plural = "Pill Gifts"
        ordering = ['-created_at']

    def __str__(self):
        start_str = self.start_date.strftime("%Y-%m-%d") if self.start_date else "Any"
        end_str = self.end_date.strftime("%Y-%m-%d") if self.end_date else "Forever"
        return f"{self.discount_value}% Gift ({start_str} to {end_str})"

    def is_available(self, order_value):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        if order_value < self.min_order_value:
            return False
        if self.max_order_value and order_value > self.max_order_value:
            return False
        return True

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