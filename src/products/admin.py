from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Category, SubCategory, Brand, Product, ProductImage, ProductDescription,
    Color, ProductAvailability, Shipping, PillItem, Pill, PillAddress,
    PillStatusLog, CouponDiscount, Rating, Discount, PayRequest, LovedProduct,
    StockAlert, PriceDropAlert, SpecialProduct, SpinWheelDiscount,
    SpinWheelResult, SpinWheelSettings, PillGift
)

class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_image_preview')
    search_fields = ('name',)
    inlines = [SubCategoryInline]

    @admin.display(description='Image')
    def get_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"

# FIX: Added a dedicated admin for SubCategory with search_fields
@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name', 'category__name')
    autocomplete_fields = ('category',)
    list_filter = ('category',)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_logo_preview')
    search_fields = ('name',)

    @admin.display(description='Logo')
    def get_logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" />', obj.logo.url)
        return "No Logo"

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductDescriptionInline(admin.TabularInline):
    model = ProductDescription
    extra = 1

class ProductAvailabilityInline(admin.TabularInline):
    model = ProductAvailability
    extra = 1
    autocomplete_fields = ['color']

class DiscountInline(admin.TabularInline):
    model = Discount
    extra = 0
    fields = ('discount', 'discount_start', 'discount_end', 'is_active')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_base_image_preview', 'category', 'price', 'get_total_quantity', 'average_rating', 'is_important', 'date_added')
    list_filter = ('category', 'brand', 'is_important', 'date_added')
    search_fields = ('name', 'description')
    autocomplete_fields = ('category', 'sub_category', 'brand')
    readonly_fields = ('average_rating', 'number_of_ratings', 'get_total_quantity')
    inlines = [ProductImageInline, ProductDescriptionInline, ProductAvailabilityInline, DiscountInline]
    list_select_related = ('category', 'brand')

    @admin.display(description='Image')
    def get_base_image_preview(self, obj):
        if obj.base_image:
            return format_html('<img src="{}" width="50" height="50" />', obj.base_image.url)
        return "No Image"
    
    @admin.display(description='Total Quantity', ordering='total_quantity')
    def get_total_quantity(self, obj):
        return obj.total_quantity()


@admin.register(ProductAvailability)
class ProductAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        'product', 
        'size', 
        'color', 
        'quantity', 
        'native_price', 
        'date_added'
    )
    list_filter = (
        'product__category', 
        'color', 
        'size', 
        'date_added'
    )
    search_fields = (
        'product__name', 
        'color__name', 
        'size'
    )
    readonly_fields = ('date_added',)
    ordering = ('-date_added',)
    date_hierarchy = 'date_added'

    autocomplete_fields = ['product', 'color']
    list_select_related = ['product', 'color']

    def get_queryset(self, request):
        # Optimize queryset by selecting related objects
        qs = super().get_queryset(request)
        return qs.select_related('product', 'color')

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'degree')
    search_fields = ('name', 'degree')

class PillAddressInline(admin.StackedInline):
    model = PillAddress
    can_delete = False

class PillStatusLogInline(admin.TabularInline):
    model = PillStatusLog
    extra = 0
    readonly_fields = ('status', 'changed_at')
    can_delete = False

# class PillItemInline(admin.TabularInline):
#     model = PillItem
#     extra = 0
#     autocomplete_fields = ('product', 'color')
#     readonly_fields = ('price_at_sale', 'native_price_at_sale', 'date_sold')
    
@admin.register(Pill)
class PillAdmin(admin.ModelAdmin):
    list_display = ('pill_number', 'user', 'status', 'final_price_display', 'paid', 'date_added')
    list_filter = ('status', 'paid', 'date_added')
    search_fields = ('pill_number', 'user__username', 'pilladdress__phone', 'pilladdress__name')
    autocomplete_fields = ('user', 'coupon', 'gift_discount')
    readonly_fields = ('pill_number', 'date_added', 'final_price_display')
    inlines = [PillAddressInline, PillStatusLogInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items__product', 'pilladdress').select_related('user', 'coupon', 'gift_discount')

    @admin.display(description='Final Price')
    def final_price_display(self, obj):
        return obj.final_price()

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'discount', 'discount_start', 'discount_end', 'is_active', 'is_currently_active')
    list_filter = ('is_active', 'category')
    search_fields = ('product__name', 'category__name')
    autocomplete_fields = ('product', 'category')

@admin.register(CouponDiscount)
class CouponDiscountAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'discount_value', 'available_use_times', 'is_wheel_coupon', 'coupon_start', 'coupon_end')
    search_fields = ('coupon', 'user__username')
    readonly_fields = ('coupon',)
    autocomplete_fields = ['user']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'star_number', 'date_added')
    list_filter = ('star_number', 'date_added')
    search_fields = ('product__name', 'user__username', 'review')
    autocomplete_fields = ['product', 'user']

@admin.register(Shipping)
class ShippingAdmin(admin.ModelAdmin):
    list_display = ('get_government_display', 'shipping_price')
    list_editable = ('shipping_price',)

@admin.register(PayRequest)
class PayRequestAdmin(admin.ModelAdmin):
    list_display = ('pill', 'date', 'is_applied', 'get_image_preview')
    list_filter = ('is_applied', 'date')
    search_fields = ('pill__pill_number',)
    autocomplete_fields = ['pill']
    actions = ['mark_as_applied']

    @admin.display(description='Image')
    def get_image_preview(self, obj):
        if obj.image:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" width="100"/></a>', obj.image.url)
        return "No Image"

    @admin.action(description='Mark selected requests as applied')
    def mark_as_applied(self, request, queryset):
        queryset.update(is_applied=True)

@admin.register(SpecialProduct)
class SpecialProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'order', 'is_active', 'created_at', 'get_image_preview')
    list_filter = ('is_active',)
    search_fields = ('product__name',)
    autocomplete_fields = ['product']
    list_editable = ('order', 'is_active')

    @admin.display(description='Special Image')
    def get_image_preview(self, obj):
        if obj.special_image:
            return format_html('<img src="{}" width="50" height="50" />', obj.special_image.url)
        return "No Image"

@admin.register(PillGift)
class PillGiftAdmin(admin.ModelAdmin):
    list_display = ('discount_value', 'min_order_value', 'max_order_value', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('discount_value',)

@admin.register(SpinWheelDiscount)
class SpinWheelDiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_value', 'probability', 'is_active', 'start_date', 'end_date', 'max_winners')
    list_filter = ('is_active',)

@admin.register(LovedProduct)
class LovedProductAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    autocomplete_fields = ('user', 'product')
    search_fields = ('user__username', 'product__name')

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'product', 'is_notified', 'created_at')
    list_filter = ('is_notified',)
    autocomplete_fields = ('user', 'product')
    search_fields = ('user__username', 'email', 'product__name')

admin.site.register(ProductImage)
admin.site.register(ProductDescription)
admin.site.register(PillItem)
admin.site.register(PillAddress)
admin.site.register(PillStatusLog)
admin.site.register(PriceDropAlert)
admin.site.register(SpinWheelResult)
admin.site.register(SpinWheelSettings)