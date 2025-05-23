from rest_framework import serializers
from collections import defaultdict
from urllib.parse import urljoin
from django.utils import timezone
from accounts.models import User
from .models import Category, CouponDiscount, Discount, LovedProduct, PayRequest, PillAddress, PillItem, PillStatusLog, PriceDropAlert, ProductDescription, Shipping, SpecialProduct, SpinWheelDiscount, SpinWheelResult, StockAlert, SubCategory, Brand, Product, ProductImage, ProductAvailability, Rating, Color,Pill



class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()  # Add a field for the category name

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'category', 'category_name']  # Include category_name in the response

    def get_category_name(self, obj):
        # Return the name of the related category
        return obj.category.name
    
class CategorySerializer(serializers.ModelSerializer):
    subcategories = SubCategorySerializer(many=True, read_only=True)  # Nested subcategories

    class Meta:
        model = Category
        fields = ['id', 'name', 'image','subcategories']

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
        # Handle both single and bulk creation
        if isinstance(data, list):
            return [super().to_internal_value(item) for item in data]
        return super().to_internal_value(data)

class BulkProductDescriptionSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        descriptions = [ProductDescription(**item) for item in validated_data]
        return ProductDescription.objects.bulk_create(descriptions)


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
        allow_null=True,  # Allow null values
        required=False    # Make the field optional
    )
    size = serializers.CharField(
        allow_null=True,  # Allow null values
        required=False    # Make the field optional
    )
    product_name = serializers.SerializerMethodField()
    native_price = serializers.FloatField()

    class Meta:
        model = ProductAvailability
        fields = ['id', 'product', 'product_name', 'size', 'color', 'quantity','native_price']

    def get_product_name(self, obj):
        return obj.product.name

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Only serialize color if it exists
        if instance.color:
            representation['color'] = ColorSerializer(instance.color).data
        else:
            representation['color'] = None  # Explicitly set color to null if it doesn't exist
        return representation

class ProductAvailabilityBreifedSerializer(serializers.Serializer):
    size = serializers.CharField()
    color = serializers.CharField()
    quantity = serializers.IntegerField()
    is_low_stock = serializers.BooleanField()

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

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image']

class ProductImageBulkUploadSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    images = serializers.ListField(
        child=serializers.ImageField(),  # Each item in the list is an ImageField
        allow_empty=False,  # Ensure at least one image is provided
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

    # Add direct fields for category, sub_category, and brand
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
            'has_discount','current_discount', 'discount_expiry', 'main_image', 'images', 'number_of_ratings', 'average_rating',
            'total_quantity', 'available_colors', 'available_sizes', 'availabilities','descriptions','threshold', 'is_low_stock','is_important'
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
        # Group availabilities by size and color, and sum the quantities
        grouped_availabilities = defaultdict(int)
        for availability in obj.availabilities.all():
            key = (availability.size, availability.color.id if availability.color else None, availability.color.name if availability.color else None)
            grouped_availabilities[key] += availability.quantity

        # Convert the grouped data into the desired format
        result = [
            {
                "size": size,
                "color_id": color_id,  # Include color_id
                "color": color_name,   # Include color name
                "quantity": quantity
            }
            for (size, color_id, color_name), quantity in grouped_availabilities.items()
        ]
        return result

    def get_discounted_price(self, obj):
        return obj.discounted_price()

    def get_current_discount(self, obj):
        # Get the best active discount (product or category)
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
        # Get the expiry date of the current discount
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
        return obj.total_quantity() <= obj.threshold
    
class ProductBreifedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']

class CouponCodeField(serializers.Field):
    """
    Custom field to handle coupon code as a string and convert it to the CouponDiscount instance.
    """
    def to_internal_value(self, data):
        # Look up the CouponDiscount instance by coupon code
        try:
            return CouponDiscount.objects.get(coupon=data)
        except CouponDiscount.DoesNotExist:
            raise serializers.ValidationError("Coupon does not exist.")

    def to_representation(self, value):
        # Return the coupon code for representation
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

class PillCouponApplySerializer(serializers.ModelSerializer):
    coupon = CouponCodeField()  # Use the custom field for coupon

    class Meta:
        model = Pill
        fields = ['id', 'coupon', 'price_without_coupons', 'coupon_discount', 'price_after_coupon_discount', 'final_price']
        read_only_fields = ['id', 'price_without_coupons', 'coupon_discount', 'price_after_coupon_discount', 'final_price']

class PillAddressCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PillAddress
        fields = ['id', 'pill', 'name', 'email', 'phone', 'address', 'government','pay_method']
        read_only_fields = ['id', 'pill']

class CouponDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponDiscount
        fields = ['coupon', 'discount_value', 'coupon_start', 'coupon_end', 'available_use_times']

class PillAddressSerializer(serializers.ModelSerializer):
    government = serializers.SerializerMethodField()

    class Meta:
        model = PillAddress
        fields = ['name', 'email', 'phone', 'address', 'government']

    def get_government(self, obj):
        return obj.get_government_display()

class ShippingSerializer(serializers.ModelSerializer):
    government_name = serializers.SerializerMethodField()

    class Meta:
        model = Shipping
        fields = ['id','government', 'government_name', 'shipping_price']

    def get_government_name(self, obj):
        return obj.get_government_display()

class PillItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    color = ColorSerializer(read_only=True)

    class Meta:
        model = PillItem
        fields = ['id', 'product', 'quantity', 'size', 'color']

class PillItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PillItem
        fields = ['product', 'quantity', 'size', 'color']

class PillCreateSerializer(serializers.ModelSerializer):
    items = PillItemCreateSerializer(many=True)  # Nested serializer for PillItem
    user_name = serializers.SerializerMethodField() 
    user_username = serializers.SerializerMethodField()  
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Pill
        fields = ['id', 'user', 'user_name', 'user_username', 'items', 'status', 'date_added', 'paid']
        read_only_fields = ['id','status', 'date_added', 'paid']

    def get_user_name(self, obj):
        return obj.user.name

    def get_user_username(self, obj):
        return obj.user.username

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        pill = Pill.objects.create(**validated_data)
        
        # Use bulk_create for better performance
        pill_items = [
            PillItem(
                product=item['product'],
                quantity=item['quantity'],
                size=item.get('size'),
                color=item.get('color')
            ) for item in items_data
        ]
        created_items = PillItem.objects.bulk_create(pill_items)
        pill.items.set(created_items)
        
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

class PillDetailSerializer(serializers.ModelSerializer):
    items = PillItemSerializer(many=True, read_only=True)  # Updated to use PillItemSerializer
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
        """
        Calculate the shipping price dynamically based on the PillAddress.
        """
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
    last_price = serializers.FloatField(required=False)  # Made optional
    
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
    class Meta:
        model = SpinWheelDiscount
        fields = ['id', 'name', 'probability', 'daily_spin_limit', 
                 'min_order_value', 'start_date', 'end_date']

class SpinWheelResultSerializer(serializers.ModelSerializer):
    coupon = CouponDiscountSerializer(read_only=True)
    
    class Meta:
        model = SpinWheelResult
        fields = ['id', 'won', 'coupon', 'spin_date', 'used', 'used_date']


