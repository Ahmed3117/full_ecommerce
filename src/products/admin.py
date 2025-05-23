
from django.contrib import admin
from .models import (
    Category, PayRequest, PillItem, PriceDropAlert, ProductSales, SpinWheelDiscount, SpinWheelResult, StockAlert, SubCategory, Brand, Product, ProductImage, 
    Color, ProductAvailability, Rating, Shipping, Pill, Discount,
    CouponDiscount, PillAddress
)

# Inline models
class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductAvailabilityInline(admin.TabularInline):
    model = ProductAvailability
    extra = 1

class RatingInline(admin.TabularInline):
    model = Rating
    extra = 1
    
# Category admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [SubCategoryInline]

# SubCategory admin
@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)
    list_filter = ('category',)

# Brand admin
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Product admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'sub_category', 'brand', 'price', 'date_added')
    search_fields = ('name', 'description')
    list_filter = ('category', 'sub_category', 'brand', 'date_added')
    inlines = [ProductImageInline, ProductAvailabilityInline, RatingInline]
    readonly_fields = ('price_after_product_discount', 'price_after_category_discount', 'average_rating', 'total_quantity')

    

admin.site.register(PillItem)



@admin.register(ProductSales)
class ProductSalesAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'size', 'color', 'price_at_sale', 'date_sold', 'pill')
    list_filter = ('date_sold', 'size', 'color')
    search_fields = ('product__name', 'pill__pill_number')
    date_hierarchy = 'date_sold'
    readonly_fields = ('date_sold',)

# ProductImage admin
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')
    search_fields = ('product__name',)

# Color admin
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# ProductAvailability admin
@admin.register(ProductAvailability)
class ProductAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'color', 'quantity')
    list_filter = ('size', 'color')
    search_fields = ('product__name', 'color__name')

# Rating admin
@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'star_number', 'review', 'date_added')
    search_fields = ('product__name', 'user__username', 'review')
    list_filter = ('star_number', 'date_added')

# Shipping admin
@admin.register(Shipping)
class ShippingAdmin(admin.ModelAdmin):
    list_display = ('government', 'shipping_price')
    list_filter = ('government',)
    search_fields = ('government',)

# Pill admin
from django.contrib import admin
from .models import Pill, CouponDiscount

@admin.register(Pill)
class PillAdmin(admin.ModelAdmin):
    list_display = (
        'status', 'paid', 'date_added',
        'price_without_coupons', 'coupon_discount', 'price_after_coupon_discount',
        'shipping_price', 'final_price'
    )
    list_filter = ('status', 'paid', 'date_added')
    search_fields = ('pilladdress__name', 'pilladdress__email')
    readonly_fields = (
        'price_without_coupons', 'coupon_discount', 'price_after_coupon_discount',
        'shipping_price', 'final_price'
    )

    # Custom method to display the coupon discount in the list_display
    def coupon_discount(self, obj):
        return obj.coupon_discount()
    coupon_discount.short_description = 'Coupon Discount'

    # Custom method to display the price without coupons in the list_display
    def price_without_coupons(self, obj):
        return obj.price_without_coupons()
    price_without_coupons.short_description = 'Price Without Coupons'

    # Custom method to display the price after coupon discount in the list_display
    def price_after_coupon_discount(self, obj):
        return obj.price_after_coupon_discount()
    price_after_coupon_discount.short_description = 'Price After Coupon Discount'

    # Custom method to display the shipping price in the list_display
    def shipping_price(self, obj):
        return obj.shipping_price()
    shipping_price.short_description = 'Shipping Price'

    # Custom method to display the final price in the list_display
    def final_price(self, obj):
        return obj.final_price()
    final_price.short_description = 'Final Price'
# Discount admin
@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('category', 'product', 'discount', 'discount_start', 'discount_end')
    list_filter = ('discount_start', 'discount_end')
    search_fields = ('category__name', 'product__name')

# CouponDiscount admin
@admin.register(CouponDiscount)
class CouponDiscountAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'discount_value', 'coupon_start', 'coupon_end')
    readonly_fields = ('coupon',)
    list_filter = ('coupon_start', 'coupon_end')

# PillAddress admin
@admin.register(PillAddress)
class PillAddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'address', 'government')
    search_fields = ('name', 'email', 'address')


@admin.register(PayRequest)
class PayRequestAdmin(admin.ModelAdmin):
    list_display = ['pill', 'date', 'is_applied']
    list_filter = ['is_applied']
    search_fields = ['pill__pill_number', 'pill__user__name', 'pill__pilladdress__email', 'pill__pilladdress__phone']



@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'email', 'created_at', 'is_notified')
    list_filter = ('is_notified', 'created_at')
    search_fields = ('product__name', 'user__username', 'email')
    raw_id_fields = ('product', 'user')
    date_hierarchy = 'created_at'

@admin.register(PriceDropAlert)
class PriceDropAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'email', 'last_price', 'created_at', 'is_notified')
    list_filter = ('is_notified', 'created_at')
    search_fields = ('product__name', 'user__username', 'email')
    raw_id_fields = ('product', 'user')
    date_hierarchy = 'created_at'


@admin.register(SpinWheelDiscount)
class SpinWheelDiscountAdmin(admin.ModelAdmin):
    list_display = ['name', 'coupon', 'probability', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'coupon__coupon']

@admin.register(SpinWheelResult)
class SpinWheelResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'spin_wheel', 'won', 'used', 'spin_date']
    list_filter = ['won', 'used', 'spin_wheel']
    search_fields = ['user__username', 'spin_wheel__name']




