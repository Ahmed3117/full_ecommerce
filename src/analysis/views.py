# views.py
from rest_framework.viewsets import ViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum, Count, Avg, F, Q, FloatField, Case, When, BooleanField, Subquery, OuterRef, IntegerField, ExpressionWrapper
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear,TruncDate
from accounts.models import GOVERNMENT_CHOICES, User
from analysis.serializers import CategoryAnalyticsSerializer, InventoryAlertSerializer, ProductAnalyticsSerializer, SalesTrendSerializer
from products.models import PILL_STATUS_CHOICES, Category, Discount, LovedProduct, Pill, PillItem, Product, ProductAvailability, Rating, SpecialProduct
from rest_framework import generics, filters
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from datetime import datetime


from django.db.models import Count, Sum, Q, F, Case, When, Value, IntegerField, Avg
from django.db.models.functions import Coalesce, TruncDay, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from django.utils import timezone
from django.db.models import OuterRef, Subquery

from store.models import Store, StoreRequest



class ProductAnalyticsFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(method='filter_by_sale_date')
    end_date = django_filters.DateFilter(method='filter_by_sale_date')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = django_filters.NumberFilter(field_name='category__id')
    is_low_stock = django_filters.BooleanFilter(method='filter_is_low_stock')
    class Meta:
        model = Product
        fields = ['category', 'brand', 'min_price', 'max_price', 'is_low_stock']

    def filter_by_sale_date(self, queryset, name, value):
        # This logic is now handled correctly within the subqueries in the view
        return queryset
    
    def filter_is_low_stock(self, queryset, name, value):
        """
        Filters the queryset based on the annotated 'is_low_stock' field.
        The annotation (total_available <= threshold) is performed in the view.
        """
        # The `is_low_stock` annotation is already added in the view's get_queryset.
        # This method will now correctly filter on that pre-calculated value.
        if value in (True, 'true', 'True', 1):
            return queryset.filter(is_low_stock=True)
        if value in (False, 'false', 'False', 0):
            return queryset.filter(is_low_stock=False)
        return queryset

class ProductPerformanceView(generics.ListAPIView):
    serializer_class = ProductAnalyticsSerializer
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = ProductAnalyticsFilter
    ordering_fields = ['total_sold', 'revenue', 'average_rating', 'total_available', 'price', 'name']
    search_fields = ['name']
    
    def get_queryset(self):
        # Use select_related for efficiency in the serializer (e.g., category.name)
        base_queryset = Product.objects.select_related('category', 'brand')

        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')
        low_stock_threshold = self.request.query_params.get('low_stock_threshold')

        # --- Subquery Definitions ---

        # 1. Subquery for total available stock
        avail_sq = Subquery(
            ProductAvailability.objects.filter(
                product=OuterRef('pk')
            ).values('product').annotate(total=Sum('quantity')).values('total')
        )

        # 2. Subquery for stock added within a date range
        added_filter = Q(product=OuterRef('pk'))
        if start_date_str and end_date_str:
            parsed_start = parse_date(start_date_str)
            parsed_end = parse_date(end_date_str)
            if parsed_start and parsed_end:
                end_of_day_exclusive = parsed_end + timedelta(days=1)
                added_filter &= Q(date_added__gte=parsed_start, date_added__lt=end_of_day_exclusive)
        
        added_sq = Subquery(
            ProductAvailability.objects.filter(added_filter)
            .values('product').annotate(total=Sum('quantity')).values('total')
        )

        # 3. Subquery for sales and revenue with correct date handling
        sales_filter = Q(product=OuterRef('pk'), status__in=['p', 'd'])
        if start_date_str and end_date_str:
            parsed_start = parse_date(start_date_str)
            parsed_end = parse_date(end_date_str)
            if parsed_start and parsed_end:
                end_of_day_exclusive = parsed_end + timedelta(days=1)
                sales_filter &= Q(date_sold__gte=parsed_start, date_sold__lt=end_of_day_exclusive)

        sold_items_sq = PillItem.objects.filter(sales_filter).values('product')
        
        total_sold_sq = sold_items_sq.annotate(total=Sum('quantity')).values('total')
        revenue_sq = sold_items_sq.annotate(
            total=Sum(F('quantity') * F('price_at_sale'))
        ).values('total')
        
        # 4. Subqueries for ratings
        ratings_sq = Rating.objects.filter(product=OuterRef('pk')).values('product')
        avg_rating_sq = ratings_sq.annotate(avg=Avg('star_number')).values('avg')
        total_ratings_sq = ratings_sq.annotate(count=Count('id')).values('count')

        # 5. Subquery for current discount
        now = timezone.now()
        current_discount_sq = Subquery(
            Discount.objects.filter(
                (Q(product=OuterRef('pk')) | Q(category=OuterRef('category'))),
                discount_start__lte=now,
                discount_end__gte=now,
                is_active=True
            ).order_by('-discount').values('discount')[:1] # Get the best discount
        )

        # --- Main Annotation ---
        queryset = base_queryset.annotate(
            total_available=Coalesce(avail_sq, 0, output_field=IntegerField()),
            total_added=Coalesce(added_sq, 0, output_field=IntegerField()),
            total_sold=Coalesce(total_sold_sq, 0, output_field=IntegerField()),
            revenue=Coalesce(revenue_sq, 0.0, output_field=FloatField()),
            average_rating=Coalesce(avg_rating_sq, 0.0, output_field=FloatField()),
            total_ratings=Coalesce(total_ratings_sq, 0, output_field=IntegerField()),
            current_discount=Coalesce(current_discount_sq, 0.0, output_field=FloatField()),
        ).annotate(
            price_after_discount=Case(
                When(current_discount__gt=0, then=F('price') * (1 - F('current_discount') / 100.0)),
                default=F('price'),
                output_field=FloatField()
            ),
            has_discount=Case(
                When(current_discount__gt=0, then=True),
                default=False,
                output_field=BooleanField()
            ),
            is_low_stock=Case(
                When(total_available__lte=F('threshold'), then=True),
                default=False,
                output_field=BooleanField()
            )
        )

        # Apply final filter for low stock threshold if requested
        if low_stock_threshold is not None:
            try:
                threshold_val = int(low_stock_threshold)
                queryset = queryset.filter(total_available__lte=threshold_val)
            except (ValueError, TypeError):
                pass
        
        return queryset


class CategoryPerformanceView(generics.ListAPIView):
    serializer_class = CategoryAnalyticsSerializer

    def get_queryset(self):
        # Subquery for total available quantity
        avail_sq = Subquery(
            Product.objects.filter(
                category=OuterRef('pk')
            ).values('category').annotate(
                total=Sum('availabilities__quantity')
            ).values('total')
        )

        # Base subquery for sold items
        sold_items = PillItem.objects.filter(
            product__category=OuterRef('pk'),
            status__in=['p', 'd']
        )
        
        # Subquery for total sales quantity
        sales_sq = Subquery(
            sold_items.values('product__category').annotate(
                total=Sum('quantity')
            ).values('total')
        )

        # Subquery for total revenue
        revenue_sq = Subquery(
            sold_items.values('product__category').annotate(
                total=Sum(F('quantity') * F('price_at_sale'))
            ).values('total')
        )

        return Category.objects.annotate(
            total_products=Count('products', distinct=True),
            total_available_quantity=Coalesce(avail_sq, 0, output_field=IntegerField()),
            total_sales=Coalesce(sales_sq, 0, output_field=IntegerField()),
            revenue=Coalesce(revenue_sq, 0.0, output_field=FloatField())
        ).order_by('-revenue')

######################### New Consolidated Views #########################


class SalesDashboardView(APIView):
    """
    Consolidated sales dashboard endpoint with multiple metrics
    """
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Base query for sold items (paid or delivered)
        sold_items = PillItem.objects.filter(
            Q(status='p') | Q(status='d'),
            date_sold__range=[start_date, end_date]
        )
        
        # 1. Sales Trends (Daily)
        daily_sales = sold_items.annotate(
            day=TruncDay('date_sold')
        ).values('day').annotate(
            total_sales=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price_at_sale')),
            total_cost=Sum(F('quantity') * F('native_price_at_sale'))
        ).order_by('day')
        
        # 2. Product Performance
        product_sales = sold_items.values(
            'product__id', 'product__name'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price_at_sale')),
            total_cost=Sum(F('quantity') * F('native_price_at_sale')),
            avg_price=Avg('price_at_sale')
        ).order_by('-total_revenue')
        
        # 3. Inventory Metrics
        inventory_cost = ProductAvailability.objects.filter(
            date_added__range=[start_date, end_date]
        ).aggregate(
            total_cost=Sum(F('quantity') * F('native_price'))
        )['total_cost'] or 0
        
        # 4. Financial Summary
        sales_revenue = sold_items.aggregate(
            total_revenue=Sum(F('quantity') * F('price_at_sale'))
        )['total_revenue'] or 0
        
        cogs = sold_items.aggregate(
            total_cost=Sum(F('quantity') * F('native_price_at_sale'))
        )['total_cost'] or 0
        
        profit = sales_revenue - cogs
        margin = (profit / sales_revenue * 100) if sales_revenue else 0
        
        return Response({
            'time_period': {'start_date': start_date, 'end_date': end_date},
            'daily_sales': list(daily_sales),
            'product_performance': list(product_sales),
            'financial_summary': {
                'sales_revenue': sales_revenue,
                'cost_of_goods_sold': cogs,
                'gross_profit': profit,
                'gross_margin': margin,
                'inventory_cost': inventory_cost
            }
        })

class ProductInventoryView(APIView):
    """
    Consolidated product inventory analysis
    """
    def get(self, request):
        # 1. Low stock products
        total_quantity = ProductAvailability.objects.filter(
            product=OuterRef('pk')
        ).values('product').annotate(
            total=Sum('quantity')
        ).values('total')
        
        low_stock = Product.objects.annotate(
            current_quantity=Subquery(total_quantity)
        ).filter(
            current_quantity__lte=F('threshold')
        ).values('id', 'name', 'threshold', 'current_quantity')
        
        # 2. Special products count
        special_count = SpecialProduct.objects.filter(is_active=True).count()
        important_count = Product.objects.filter(is_important=True).count()
        
        # 4. Most loved products
        loved_products = LovedProduct.objects.values(
            'product__id', 'product__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response({
            'low_stock_products': list(low_stock),
            'special_products': {
                'important_count': important_count,
                'special_count': special_count
            },
            'most_loved_products': list(loved_products)
        })

class OrderAnalysisView(APIView):
    """
    Consolidated order and pill analysis
    """
    def get(self, request):
        # 1. Pill status counts
        pill_status = Pill.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        status_counts = {status[0]: 0 for status in PILL_STATUS_CHOICES}
        for item in pill_status:
            status_counts[item['status']] = item['count']
        
        # 2. Pill items status counts
        item_status = PillItem.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        item_status_counts = {status[0]: 0 for status in PILL_STATUS_CHOICES}
        for item in item_status:
            item_status_counts[item['status']] = item['count']
        
        # 3. Best sellers
        best_sellers = PillItem.objects.filter(
            Q(status='p') | Q(status='d')
        ).values(
            'product__id', 'product__name'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price_at_sale'))
        ).order_by('-total_sold')[:10]
        
        return Response({
            'pill_status_counts': status_counts,
            'pill_item_status_counts': item_status_counts,
            'best_selling_products': list(best_sellers)
        })

class CustomerActivityView(APIView):
    """
    Customer and government activity analysis
    """
    def get(self, request):
        # 1. User type breakdown
        user_types = User.objects.values('user_type').annotate(
            count=Count('id')
        )
        
        # 2. Active vs inactive users
        active_users = User.objects.filter(
            pills__isnull=False
        ).distinct().count()
        total_users = User.objects.count()
        
        # 3. Government activity
        gov_activity = Pill.objects.filter(
            pilladdress__isnull=False
        ).values(
            'pilladdress__government'
        ).annotate(
            pill_count=Count('id'),
            user_count=Count('user', distinct=True)
        ).order_by('-pill_count')
        
        gov_map = {code: name for code, name in GOVERNMENT_CHOICES}
        formatted_gov = []
        for item in gov_activity:
            gov_code = item['pilladdress__government']
            formatted_gov.append({
                'government_code': gov_code,
                'government_name': gov_map.get(gov_code, 'Unknown'),
                'pill_count': item['pill_count'],
                'user_count': item['user_count']
            })
        
        return Response({
            'user_types': list(user_types),
            'user_activity': {
                'active_users': active_users,
                'inactive_users': total_users - active_users,
                'total_users': total_users
            },
            'government_activity': formatted_gov
        })

class StoreAnalyticsView(APIView):
    """
    Store-related analytics
    """
    def get(self, request):
        # 1. Store requests
        store_requests = StoreRequest.objects.values('status').annotate(
            count=Count('id')
        )
        
        request_counts = {status: 0 for status, _ in StoreRequest.STATUS_CHOICES}
        for item in store_requests:
            request_counts[item['status']] = item['count']
        
        # 2. Stores by government
        stores_by_gov = Store.objects.values('government').annotate(
            count=Count('id')
        )
        
        # Create mapping from code to name and vice versa
        gov_code_to_name = {code: name for code, name in GOVERNMENT_CHOICES}
        gov_name_to_code = {name: code for code, name in GOVERNMENT_CHOICES}
        
        formatted_gov = []
        for item in stores_by_gov:
            gov_code = item['government']
            gov_name = gov_code_to_name.get(gov_code, 'Unknown')
            
            formatted_gov.append({
                'government_code': gov_code,  # Keep the original code (e.g., '1')
                'government_name': gov_name,  # Full name (e.g., 'Cairo')
                'store_count': item['count']
            })
        
        # Sort by government name alphabetically
        formatted_gov.sort(key=lambda x: x['government_name'])
        
        return Response({
            'store_requests': request_counts,
            'stores_by_government': formatted_gov,
            'total_stores': Store.objects.count()
        })



