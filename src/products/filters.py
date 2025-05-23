
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
        
        
        
        
        