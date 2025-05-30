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