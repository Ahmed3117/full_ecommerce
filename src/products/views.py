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
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'color', 'size']

class ProductAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductAvailability.objects.all()
    serializer_class = ProductAvailabilitySerializer
    permission_classes = [IsAdminUser]

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