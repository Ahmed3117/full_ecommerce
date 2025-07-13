from datetime import timedelta
import random
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, F, Count, Q, Case, When, IntegerField
from django.db import transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework import filters as rest_filters
from rest_framework.filters import OrderingFilter
from accounts.pagination import CustomPageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from .serializers import *
from .filters import CategoryFilter, CouponDiscountFilter, PillFilter, ProductFilter, SpinWheelResultFilter
from .models import (
    Category, Color, CouponDiscount, PillAddress, ProductAvailability,
    ProductImage, Rating, Shipping, SubCategory, Brand, Product, Pill,
    SpinWheelDiscount, SpinWheelResult
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
    filterset_fields = ['category','category__type']

class BrandListView(generics.ListAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    pagination_class = None

class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    search_fields = ['name', ]
 
class TeacherListView(generics.ListAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['subject']
    search_fields = ['name', 'subject__name']

class TeacherDetailView(generics.RetrieveAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

    def get(self, request, *args, **kwargs):
        teacher = self.get_object()
        serializer = self.get_serializer(teacher, context={'request': request})
        return Response(serializer.data)

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'category__name', 'brand__name','subject__name' , 'teacher__name', 'description']


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'

class Last10ProductsListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter

class ActiveSpecialProductsView(generics.ListAPIView):
    serializer_class = SpecialProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return SpecialProduct.objects.filter(is_active=True).order_by('-order')
    
class ActiveBestProductsView(generics.ListAPIView):
    serializer_class = BestProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return BestProduct.objects.filter(is_active=True).order_by('-order')



class CombinedProductsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        # Get limit parameter with default of 10
        limit = int(request.query_params.get('limit', 10))
        
        # Prepare response data
        data = {
            'last_products': self.get_last_products(limit),
            'important_products': self.get_important_products(limit),
            'first_year_products': self.get_year_products('first-secondary', limit),
            'second_year_products': self.get_year_products('second-secondary', limit),
            'third_year_products': self.get_year_products('third-secondary', limit),
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    def get_last_products(self, limit):
        queryset = Product.objects.all().order_by('-id')[:limit]
        serializer = ProductSerializer(queryset, many=True, context={'request': self.request})
        return serializer.data
    
    def get_important_products(self, limit):
        queryset = Product.objects.filter(
            is_important=True
        ).order_by('-date_added')[:limit]
        serializer = ProductSerializer(queryset, many=True, context={'request': self.request})
        return serializer.data
    
    def get_year_products(self, year, limit):
        queryset = Product.objects.filter(
            year=year
        ).order_by('-date_added')[:limit]
        serializer = ProductSerializer(queryset, many=True, context={'request': self.request})
        return serializer.data

class SpecialBestProductsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        # Get limit parameter with default of 10
        limit = int(request.query_params.get('limit', 10))
        
        # Prepare response data
        data = {
            'special_products': self.get_special_products(limit),
            'best_products': self.get_best_products(limit),
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    def get_special_products(self, limit):
        # Get the special products with their related product data
        special_products = SpecialProduct.objects.filter(
            is_active=True
        ).order_by('-order')[:limit].select_related('product')
        
        # Serialize with additional fields
        result = []
        for sp in special_products:
            product_data = ProductSerializer(sp.product, context={'request': self.request}).data
            result.append({
                'order': sp.order,
                'special_image': self.get_special_image_url(sp),
                **product_data
            })
        return result
    
    def get_special_image_url(self, special_product):
        if special_product.special_image and hasattr(special_product.special_image, 'url'):
            if hasattr(self, 'request'):
                return self.request.build_absolute_uri(special_product.special_image.url)
            return special_product.special_image.url
        return None
    
    def get_best_products(self, limit):
        # Get the best products with their related product data
        best_products = BestProduct.objects.filter(
            is_active=True
        ).order_by('-order')[:limit].select_related('product')
        
        # Serialize with additional fields
        result = []
        for bp in best_products:
            product_data = ProductSerializer(bp.product, context={'request': self.request}).data
            result.append({
                'order': bp.order,
                **product_data
            })
        return result


class TeacherProductsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, teacher_id, *args, **kwargs):
        try:
            teacher = Teacher.objects.get(pk=teacher_id)
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Teacher not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get limit parameter with default of 10
        limit = int(request.query_params.get('limit', 10))
        
        # Prepare response data
        data = {
            'teacher': TeacherSerializer(teacher, context={'request': request}).data,
            'important_books': self.get_important_books(teacher, limit),
            'important_products': self.get_important_products(teacher, limit),
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    def get_important_books(self, teacher, limit):
        queryset = Product.objects.filter(
            teacher=teacher,
            is_important=True,
            type='book'
        ).order_by('-date_added')[:limit]
        serializer = ProductSerializer(queryset, many=True, context={'request': self.request})
        return serializer.data
    
    def get_important_products(self, teacher, limit):
        queryset = Product.objects.filter(
            teacher=teacher,
            is_important=True,
            type='product'
        ).order_by('-date_added')[:limit]
        serializer = ProductSerializer(queryset, many=True, context={'request': self.request})
        return serializer.data

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
            # Check for existing item with the exact same attributes
            existing_item = PillItem.objects.filter(
                user=user,
                product=product,
                size=size,
                color=color,
                status__isnull=True
            ).first()

            if existing_item:
                # If same exact item exists, combine quantities
                combined_quantity = existing_item.quantity + quantity
                try:
                    temp_data = {
                        'product': product.id,
                        'size': size,
                        'color': color.id if color else None,
                        'quantity': combined_quantity
                    }
                    # Create a new serializer instance for validation
                    validation_serializer = self.get_serializer(data=temp_data)
                    validation_serializer.is_valid(raise_exception=True)
                except serializers.ValidationError as e:
                    raise serializers.ValidationError(e.detail)

                existing_item.quantity = combined_quantity
                existing_item.save()
                serializer.instance = existing_item
            else:
                # Create new item
                serializer.save(user=user, status=None)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)



class PillItemUpdateView(generics.UpdateAPIView):
    serializer_class = PillItemCreateUpdateSerializer
    permission_classes = [IsAuthenticated]
    queryset = PillItem.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

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

class PillCreateView(generics.CreateAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        pill = serializer.save(user=self.request.user, status='i')
        pill.apply_gift_discount()  # Explicit call (also handled in save)

class PillCouponApplyView(generics.UpdateAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillCouponApplySerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        pill = serializer.save()
        pill.apply_gift_discount()  # Re-apply gift after coupon update




class PillAddressCreateUpdateView(generics.CreateAPIView, generics.UpdateAPIView):
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
        pill.save()  # Triggers apply_gift_discount in Pill.save

    def perform_update(self, serializer):
        pill_id = self.kwargs.get('pill_id')
        pill = get_object_or_404(Pill, id=pill_id, user=self.request.user)
        serializer.save(pill=pill)
        pill.status = 'w'
        pill.save()  # Triggers apply_gift_discount in Pill.save

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

class ProductAvailabilitiesView(generics.ListAPIView):
    serializer_class = ProductAvailabilitySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductAvailability.objects.filter(product_id=product_id)

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
        # Get products with paid/delivered items
        queryset = Product.objects.annotate(
            total_sold=Sum(
                Case(
                    When(
                        pill_items__status__in=['p', 'd'],
                        then='pill_items__quantity'
                    ),
                    default=0,
                    output_field=IntegerField()
                )
            )
        ).filter(
            total_sold__gt=0
        ).order_by('-total_sold')
        
        # Apply date filter if provided
        days = self.request.query_params.get('days', None)
        if days:
            date_threshold = timezone.now() - timedelta(days=int(days))
            queryset = queryset.annotate(
                recent_sold=Sum(
                    Case(
                        When(
                            pill_items__status__in=['p', 'd'],
                            pill_items__date_sold__gte=date_threshold,
                            then='pill_items__quantity'
                        ),
                        default=0,
                        output_field=IntegerField()
                    )
                )
            ).filter(
                recent_sold__gt=0
            ).order_by('-recent_sold')
        
        return queryset

class FrequentlyBoughtTogetherView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        product_id = self.request.query_params.get('product_id')
        if not product_id:
            return Product.objects.none()
        
        # Get pills that contain the requested product
        pill_ids = PillItem.objects.filter(
            product_id=product_id,
            status__in=['p', 'd']
        ).values_list('pill_id', flat=True)
        
        # Find other products in those pills
        frequent_products = Product.objects.filter(
            pill_items__pill_id__in=pill_ids,
            pill_items__status__in=['p', 'd']
        ).exclude(
            id=product_id
        ).annotate(
            co_purchase_count=Count('pill_items__id')
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
                Q(brand=current_product.brand) |
                Q(subject=current_product.subject) |
                Q(teacher=current_product.teacher)
            ).exclude(id=current_product_id).distinct()
            recommendations.extend(list(similar_products))
        
        # Loved products
        loved_products = Product.objects.filter(
            lovedproduct__user=user
        ).exclude(id__in=[p.id for p in recommendations]).distinct()
        recommendations.extend(list(loved_products))
        
        # Purchased products (using PillItem now)
        purchased_products = Product.objects.filter(
            pill_items__user=user,
            pill_items__status__in=['p', 'd']
        ).exclude(id__in=[p.id for p in recommendations]).distinct()
        recommendations.extend(list(purchased_products))
        
        # Deduplicate
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
        spin_wheels = SpinWheelDiscount.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        if not spin_wheels.exists():
            return Response(
                {"error": "No active spin wheels available"},
                status=status.HTTP_404_NOT_FOUND
            )
        settings = SpinWheelSettings.get_settings()
        today = now.date()
        spins_today = SpinWheelResult.objects.filter(
            user=request.user,
            spin_date_time__date=today
        ).count()
        remaining_spins = max(0, settings.daily_spin_limit - spins_today)
        serializer = SpinWheelDiscountSerializer(spin_wheels, many=True)
        return Response({
            "spin_wheels": serializer.data,
            "daily_spin_limit": settings.daily_spin_limit,
            "remaining_spins": remaining_spins
        })

    def post(self, request):
        now = timezone.now()
        settings = SpinWheelSettings.get_settings()
        today = now.date()

        # Check daily spin limit
        spins_today = SpinWheelResult.objects.filter(
            user=request.user,
            spin_date_time__date=today
        ).count()
        if spins_today >= settings.daily_spin_limit:
            return Response(
                {"error": "Daily spin limit reached"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has already won today
        won_today = SpinWheelResult.objects.filter(
            user=request.user,
            spin_date_time__date=today,
            coupon__isnull=False
        ).exists()
        if won_today:
            return Response(
                {"error": "You can only win once per day"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get available spin wheels
        available_spin_wheels = SpinWheelDiscount.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).annotate(
            current_winners=Count('spinwheelresult', filter=Q(spinwheelresult__coupon__isnull=False))
        ).filter(
            current_winners__lt=F('max_winners')
        )
        if not available_spin_wheels.exists():
            return Response(
                {"error": "No available spin wheels with remaining winner slots"},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            # Select a spin wheel based on probabilities
            total_probability = sum(wheel.probability for wheel in available_spin_wheels)
            if total_probability == 0:
                selected_wheel = random.choice(available_spin_wheels)
            else:
                weights = [wheel.probability / total_probability for wheel in available_spin_wheels]
                selected_wheel = random.choices(available_spin_wheels, weights=weights, k=1)[0]

            # Create spin result
            result = SpinWheelResult.objects.create(
                user=request.user,
                spin_wheel=selected_wheel
            )

            # Determine if user wins
            won = random.random() < selected_wheel.probability
            coupon = None
            if won:
                coupon = CouponDiscount.objects.create(
                    discount_value=selected_wheel.discount_value,
                    coupon_start=now,
                    coupon_end=now + timedelta(days=30),
                    available_use_times=1,
                    is_wheel_coupon=True,
                    user=request.user,
                    min_order_value=selected_wheel.min_order_value
                )
                result.coupon = coupon
                result.save()

        return Response({
            'id': result.id,
            'user': result.user.id,
            'spin_wheel': SpinWheelDiscountSerializer(selected_wheel).data,
            'coupon': CouponDiscountSerializer(coupon).data if coupon else None,
            'spin_date_time': result.spin_date_time,
            'won': won
        })

class SpinWheelHistoryView(generics.ListAPIView):
    serializer_class = SpinWheelResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SpinWheelResultFilter

    def get_queryset(self):
        return SpinWheelResult.objects.filter(user=self.request.user).order_by('-spin_date_time')
    
class UserSpinWheelCouponsView(generics.ListAPIView):
    serializer_class = CouponDiscountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CouponDiscount.objects.filter(
            is_wheel_coupon=True,
            user=self.request.user
        ).order_by('-coupon_start')


# Admin Endpoints

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CategoryFilter
    # permission_classes = [IsAdminUser]

class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # permission_classes = [IsAdminUser]

class SubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category','category__type']
    # permission_classes = [IsAdminUser]

class SubCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    # permission_classes = [IsAdminUser]

class BrandListCreateView(generics.ListCreateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    # permission_classes = [IsAdminUser]

class BrandRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    # permission_classes = [IsAdminUser]

class SubjectListCreateView(generics.ListCreateAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    search_fields = ['name']
    # permission_classes = [IsAdminUser]

class SubjectRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    # permission_classes = [IsAdminUser]
    

class TeacherListCreateView(generics.ListCreateAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['subject']
    search_fields = ['name', 'subject__name']
    # permission_classes = [IsAdminUser]

class TeacherRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    # permission_classes = [IsAdminUser]
    

class ColorListCreateView(generics.ListCreateAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    # permission_classes = [IsAdminUser]

class ColorRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    # permission_classes = [IsAdminUser]
    lookup_field = 'id'

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'category__name', 'brand__name', 'description']
    pagination_class = CustomPageNumberPagination
    # permission_classes = [IsAdminUser]

class ProductListBreifedView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductBreifedSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'category__name', 'brand__name', 'description']
    # permission_classes = [IsAdminUser]

class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [IsAdminUser]

class ProductImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    filterset_fields = ['product']
    # permission_classes = [IsAdminUser]

class ProductImageBulkCreateView(generics.CreateAPIView):
    # permission_classes = [IsAdminUser]

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
    # permission_classes = [IsAdminUser]

class ProductDescriptionListCreateView(generics.ListCreateAPIView):
    queryset = ProductDescription.objects.all()
    serializer_class = ProductDescriptionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product']
    # permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST' and isinstance(self.request.data, list):
            return ProductDescriptionCreateSerializer
        return ProductDescriptionSerializer

class ProductDescriptionBulkCreateView(generics.CreateAPIView):
    queryset = ProductDescription.objects.all()
    # permission_classes = [IsAdminUser]

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
    # permission_classes = [IsAdminUser]

class SpecialProductListCreateView(generics.ListCreateAPIView):
    queryset = SpecialProduct.objects.all()
    serializer_class = SpecialProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['is_active', 'product']
    search_fields = ['product__name', 'product__category__name', 'product__brand__name']
    ordering_fields = ['order', 'created_at']
    # permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save()

class SpecialProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SpecialProduct.objects.all()
    serializer_class = SpecialProductSerializer
    # permission_classes = [IsAdminUser]

class BestProductListCreateView(generics.ListCreateAPIView):
    queryset = BestProduct.objects.all()
    serializer_class = BestProductSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['is_active', 'product']
    search_fields = ['product__name', 'product__category__name', 'product__brand__name']
    ordering_fields = ['order', 'created_at']
    # permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save()

class BestProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BestProduct.objects.all()
    serializer_class = BestProductSerializer
    # permission_classes = [IsAdminUser]

from rest_framework import filters

class CustomPillFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        pill_id = request.query_params.get('pill')
        if pill_id is not None:
            # First validate that the pill exists
            if Pill.objects.filter(id=pill_id).exists():
                return queryset.filter(pill__id=pill_id)
            else:
                # Return empty queryset if pill doesn't exist
                return queryset.none()
        return queryset


class PillItemListCreateView(generics.ListCreateAPIView):
    queryset = PillItem.objects.select_related(
        'user', 'product', 'color', 'pill'
    ).prefetch_related('product__images')
    serializer_class = AdminPillItemSerializer
    filter_backends = [CustomPillFilterBackend, OrderingFilter]
    ordering_fields = ['date_added', 'quantity']
    ordering = ['-date_added']
    

class PillItemRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PillItem.objects.select_related(
        'user', 'product', 'color', 'pill'
    )
    serializer_class = AdminPillItemSerializer
    lookup_field = 'pk'

    def perform_destroy(self, instance):
        if instance.pill and instance.pill.status in ['p', 'd']:
            raise serializers.ValidationError("Cannot delete items from paid/delivered pills")
        instance.delete()

class LovedProductListCreateView(generics.ListCreateAPIView):
    queryset = LovedProduct.objects.select_related(
        'user', 'product'
    ).prefetch_related('product__images')
    serializer_class = AdminLovedProductSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'user': ['exact'],
        'product': ['exact'],
        'created_at': ['gte', 'lte', 'exact']
    }
    ordering_fields = ['created_at']
    ordering = ['-created_at']

class LovedProductRetrieveDestroyView(generics.RetrieveDestroyAPIView):
    queryset = LovedProduct.objects.select_related('user', 'product')
    serializer_class = AdminLovedProductSerializer
    lookup_field = 'pk'

class PillListCreateView(generics.ListCreateAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillCreateSerializer
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_class = PillFilter
    search_fields = ['pilladdress__phone', 'pilladdress__government', 'pilladdress__name', 'user__name', 'user__username', 'pill_number','user__phone','user__parent_phone']
    # permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PillCreateSerializer
        return PillDetailSerializer

class PillRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillDetailSerializer
    # permission_classes = [IsAdminUser]

class DiscountListCreateView(generics.ListCreateAPIView):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    # permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'category', 'is_active']

class DiscountRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    # permission_classes = [IsAdminUser]

class CouponListCreateView(generics.ListCreateAPIView):
    queryset = CouponDiscount.objects.all()
    serializer_class = CouponDiscountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CouponDiscountFilter
    # permission_classes = [IsAdminUser]

class CouponRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CouponDiscount.objects.all()
    serializer_class = CouponDiscountSerializer
    # permission_classes = [IsAdminUser]

class ShippingListCreateView(generics.ListCreateAPIView):
    queryset = Shipping.objects.all()
    serializer_class = ShippingSerializer
    filterset_fields = ['government']
    # permission_classes = [IsAdminUser]

class ShippingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Shipping.objects.all()
    serializer_class = ShippingSerializer
    # permission_classes = [IsAdminUser]

class RatingListCreateView(generics.ListCreateAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    filterset_fields = ['product']
    # permission_classes = [IsAdminUser]

class RatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    # permission_classes = [IsAdminUser]

class ProductAvailabilityListCreateView(generics.ListCreateAPIView):
    queryset = ProductAvailability.objects.all()
    serializer_class = ProductAvailabilitySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'color', 'size']

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        size = request.data.get('size')
        color_id = request.data.get('color')
        new_quantity = request.data.get('quantity', 0)
        
        try:
            new_quantity = int(new_quantity)
        except (ValueError, TypeError):
            return Response(
                {'quantity': 'Quantity must be a valid integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        existing_availability = ProductAvailability.objects.filter(
            product_id=product_id,
            size=size,
            color_id=color_id
        ).first()
        
        if existing_availability:
            # Calculate the new total quantity
            total_quantity = existing_availability.quantity + new_quantity
            
            # Update the existing instance directly
            existing_availability.quantity = total_quantity
            
            # Update other fields if provided
            if 'native_price' in request.data:
                existing_availability.native_price = request.data['native_price']
            
            existing_availability.save()
            
            serializer = self.get_serializer(existing_availability)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # If no existing availability, create new one
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ProductAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductAvailability.objects.all()
    serializer_class = ProductAvailabilitySerializer
    # permission_classes = [IsAdminUser]

class SpinWheelDiscountListCreateView(generics.ListCreateAPIView):
    queryset = SpinWheelDiscount.objects.all()
    serializer_class = SpinWheelDiscountSerializer
    # permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'start_date', 'end_date']

    def perform_create(self, serializer):
        serializer.save()

class SpinWheelDiscountRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SpinWheelDiscount.objects.all()
    serializer_class = SpinWheelDiscountSerializer
    # permission_classes = [IsAdminUser]

class SpinWheelSettingsView(APIView):
    # permission_classes = [IsAdminUser]

    def get(self, request):
        settings = SpinWheelSettings.get_settings()
        serializer = SpinWheelSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        settings = SpinWheelSettings.get_settings()
        serializer = SpinWheelSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PillGiftListCreateView(generics.ListCreateAPIView):
    queryset = PillGift.objects.all()
    serializer_class = PillGiftSerializer
    # permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'start_date', 'end_date']

class PillGiftRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PillGift.objects.all()
    serializer_class = PillGiftSerializer
    # permission_classes = [IsAdminUser]

class AdminPayRequestCreateView(generics.CreateAPIView):
    queryset = PayRequest.objects.all()
    serializer_class = PayRequestSerializer
    # permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        pill_id = self.request.data.get('pill')
        try:
            pill = Pill.objects.get(id=pill_id)
            if pill.paid:
                raise serializers.ValidationError("This pill is already paid.")
            serializer.save(pill=pill)
        except Pill.DoesNotExist:
            raise serializers.ValidationError("Pill does not exist.")
        
class ApplyPayRequestView(APIView):
    # permission_classes = [IsAdminUser]

    def post(self, request, id):
        pay_request = get_object_or_404(PayRequest, id=id)
        if pay_request.is_applied:
            return Response(
                {"error": "Pay request already applied"},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            pay_request.is_applied = True
            pay_request.save()
            pill = pay_request.pill
            pill.paid = True
            pill.status = 'p'
            pill.save()
        return Response({"status": "Pay request applied successfully"}, status=status.HTTP_200_OK)




