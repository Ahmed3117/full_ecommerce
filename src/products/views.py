from datetime import timedelta
import random
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, F, Count, Q
from rest_framework import generics, status
from rest_framework import filters as rest_filters  # Rename this import
from django_filters.rest_framework import DjangoFilterBackend
from collections import defaultdict
from products.permissions import IsOwner, IsOwnerOrReadOnly
from .models import Category, Color, CouponDiscount, PillAddress, ProductAvailability, ProductImage, ProductSales, Rating, Shipping, SubCategory, Brand, Product,Pill
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from .serializers import *
from .filters import CategoryFilter, CouponDiscountFilter, PillFilter, ProductFilter
from .models import prepare_whatsapp_message


#^ < ==========================customer endpoints========================== >

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
        return SpecialProduct.objects.filter(
            is_active=True
        ).order_by('-order')[:10] 

class PillCreateView(generics.CreateAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillCreateSerializer
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def perform_create(self, serializer):
        # If 'user' is not in the request data, set it to the request.user
        if 'user' not in serializer.validated_data:
            serializer.validated_data['user'] = self.request.user
        serializer.save()

class PillCouponApplyView(generics.UpdateAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillCouponApplySerializer
    lookup_field = 'id'

    def perform_update(self, serializer):
        # Get the coupon instance from the validated data
        coupon = serializer.validated_data.get('coupon')

        # Get the pill instance
        pill = self.get_object()

        # Check if the pill already has a coupon
        if pill.coupon:
            return Response({"error": "This pill already has a coupon applied."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the coupon is valid (within start and end dates)
        if not self.is_coupon_valid(coupon):
            return Response({"error": "Coupon is not valid or expired."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the coupon is available based on available_use_times
        if not self.is_coupon_available(coupon):
            return Response({"error": "Coupon is not available."}, status=status.HTTP_400_BAD_REQUEST)

        # Apply the coupon to the pill
        pill = serializer.save(coupon=coupon)

        # Calculate the coupon discount as a percentage
        coupon_discount_amount = (coupon.discount_value / 100) * pill.price_without_coupons()

        # Update the pill's coupon discount field
        pill.coupon_discount = coupon_discount_amount
        pill.save()

        # Decrement the available_use_times of the coupon
        coupon.available_use_times -= 1
        coupon.save()

        # Return the updated pill data
        return Response(self.get_pill_data(pill), status=status.HTTP_200_OK)

    def is_coupon_valid(self, coupon):
        """
        Check if the coupon is valid based on its start and end dates.
        """
        now = timezone.now()
        return coupon.coupon_start <= now <= coupon.coupon_end

    def is_coupon_available(self, coupon):
        """
        Check if the coupon is available based on available_use_times.
        """
        return coupon.available_use_times > 0

    def get_pill_data(self, pill):
        """
        Return the updated pill data with price calculations.
        """
        return {
            "id": pill.id,
            "coupon": pill.coupon.coupon if pill.coupon else None,
            "price_without_coupons": pill.price_without_coupons(),
            "coupon_discount": pill.coupon_discount,
            "price_after_coupon_discount": pill.price_after_coupon_discount(),
            "final_price": pill.final_price(),
        }

class PillAddressCreateUpdateView(generics.CreateAPIView, generics.UpdateAPIView):
    queryset = PillAddress.objects.all()
    serializer_class = PillAddressCreateSerializer

    def get_object(self):
        """
        Get the PillAddress instance associated with the pill_id.
        """
        pill_id = self.kwargs.get('pill_id')
        try:
            pill = Pill.objects.get(id=pill_id)
            return PillAddress.objects.get(pill=pill)
        except Pill.DoesNotExist:
            return None
        except PillAddress.DoesNotExist:
            return None

    def perform_create(self, serializer):
        pill_id = self.kwargs.get('pill_id')
        try:
            pill = Pill.objects.get(id=pill_id)
            # Save the PillAddress with the associated Pill
            serializer.save(pill=pill)

            # Update the Pill's status to 'w' (waiting)
            pill.status = 'w'
            pill.save()

        except Pill.DoesNotExist:
            return Response({"error": "Pill does not exist."}, status=status.HTTP_404_NOT_FOUND)

    def perform_update(self, serializer):
        pill_id = self.kwargs.get('pill_id')
        try:
            pill = Pill.objects.get(id=pill_id)
            # Update the PillAddress
            serializer.save(pill=pill)

            # Optionally, you can update the Pill's status to 'w' (waiting) if needed
            pill.status = 'w'
            pill.save()

        except Pill.DoesNotExist:
            return Response({"error": "Pill does not exist."}, status=status.HTTP_404_NOT_FOUND)

class PillDetailView(generics.RetrieveAPIView):
    queryset = Pill.objects.all()
    serializer_class = PillDetailSerializer
    lookup_field = 'id'
    
class CustomerRatingListCreateView(generics.ListCreateAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Allow users to see only their own ratings
        return Rating.objects.filter(user=self.request.user)

class CustomerRatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    
class UserPillsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the authenticated user
        user = request.user
        # Retrieve all pills for the user
        pills = Pill.objects.filter(user=user)
        # Serialize the data
        serializer = PillDetailSerializer(pills, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class getColors(generics.ListAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer


class PayRequestListCreateView(generics.ListCreateAPIView):
    queryset = PayRequest.objects.all()
    serializer_class = PayRequestSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # To handle file uploads
    filter_backends = [DjangoFilterBackend, rest_filters.SearchFilter]
    filterset_fields = ['is_applied', 'pill__pill_number', 'pill__user__name', 'pill__pilladdress__email', 'pill__pilladdress__phone', 'pill__pilladdress__government']
    search_fields = ['pill__pill_number', 'pill__user__name', 'pill__pilladdress__email', 'pill__pilladdress__phone', 'pill__pilladdress__government']

    def perform_create(self, serializer):
        # Ensure the user is the owner of the pill
        pill_id = self.request.data.get('pill')
        try:
            pill = Pill.objects.get(id=pill_id, user=self.request.user)
            # Check if the pill is already paid
            if pill.paid:
                raise serializers.ValidationError("This pill is already paid.")
            serializer.save(pill=pill)
        except Pill.DoesNotExist:
            raise serializers.ValidationError("Pill does not exist or you do not have permission to create a payment request for this pill.")


class ProductsWithActiveDiscountAPIView(APIView):
    def get(self, request):
        now = timezone.now()

        # Get all product-level discounts that are currently active
        product_discounts = Discount.objects.filter(
            is_active=True,
            discount_start__lte=now,
            discount_end__gte=now,
            product__isnull=False
        ).values_list('product_id', flat=True)

        # Get all category-level discounts that are currently active
        category_discounts = Discount.objects.filter(
            is_active=True,
            discount_start__lte=now,
            discount_end__gte=now,
            category__isnull=False
        ).values_list('category_id', flat=True)

        # Filter products that either have a direct discount or a discount via their category
        products = Product.objects.filter(
            Q(id__in=product_discounts) |
            Q(category_id__in=category_discounts)
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

        # Check if product exists
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product is already in stock
        if product.total_quantity() > 0:
            return Response(
                {"error": "Product is already in stock"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for existing alert
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

        # Check if product exists
        product = get_object_or_404(Product, id=product_id)
        
        # Get or create the alert
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
        # Get back-in-stock alerts where product is now available
        back_in_stock_alerts = StockAlert.objects.filter(
            user=request.user,
            is_notified=False
        ).select_related('product').annotate(
            available_quantity=Sum('product__availabilities__quantity')
        ).filter(
            available_quantity__gt=0
        )

        # Get price drop alerts where current price is lower than alert price
        price_drop_alerts = PriceDropAlert.objects.filter(
            user=request.user,
            is_notified=False
        ).select_related('product').filter(
            product__price__lt=F('last_price')
        )

        # Serialize the data
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
                recent_sales=Sum('sales__quantity')
            ).order_by('-recent_sold')

        return queryset


class FrequentlyBoughtTogetherView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        product_id = self.request.query_params.get('product_id')
        if not product_id:
            return Product.objects.none()

        # Get products frequently bought with the specified product
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

        # 1. Similar products (same category/subcategory/brand)
        if current_product_id:
            current_product = get_object_or_404(Product, id=current_product_id)
            similar_products = Product.objects.filter(
                Q(category=current_product.category) |
                Q(sub_category=current_product.sub_category) |
                Q(brand=current_product.brand)
            ).exclude(id=current_product_id).distinct()
            recommendations.extend(list(similar_products))

        # 2. Products from loved items (using correct related_name)
        loved_products = Product.objects.filter(
            lovedproduct__user=user
        ).exclude(id__in=[p.id for p in recommendations]).distinct()
        recommendations.extend(list(loved_products))

        # 3. Previously purchased products
        purchased_products = Product.objects.filter(
            sales__pill__user=user
        ).exclude(id__in=[p.id for p in recommendations]).distinct()
        recommendations.extend(list(purchased_products))

        # Remove duplicates and limit results
        seen = set()
        unique_recommendations = []
        for product in recommendations:
            if product.id not in seen:
                seen.add(product.id)
                unique_recommendations.append(product)
            if len(unique_recommendations) >= 12:  # Limit to 12 products
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

        # Check daily spins
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

        # Check daily limit
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

        # Determine if user wins
        won = random.random() < spin_wheel.probability
        coupon = spin_wheel.coupon if won else None

        # Record result
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
        return SpinWheelResult.objects.filter(
            user=self.request.user
        ).order_by('-spin_date')


#^ < ==========================Dashboard endpoints========================== >

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

        # Save each image
        product_images = [
            ProductImage(product=product, image=image)
            for image in images
        ]
        ProductImage.objects.bulk_create(product_images)

        return Response(
            {"message": "Images uploaded successfully."},
            status=status.HTTP_201_CREATED,
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
            # Use a custom serializer for bulk operations
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
        # Use PillCreateSerializer for POST (create) requests
        if self.request.method == 'POST':
            return PillCreateSerializer
        # Use PillDetailSerializer for GET (list) requests
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
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # Group availabilities by size and color, and sum the quantities
        grouped_availabilities = defaultdict(int)
        for availability in product.availabilities.all():
            color_id = availability.color.id if availability.color else None
            color_name = availability.color.name if availability.color else None
            key = (availability.size, color_id, color_name)
            grouped_availabilities[key] += availability.quantity

        # Convert the grouped data into the desired format
        result = [
            {
                "size": size,
                "color": {
                    "id": color_id,
                    "name": color_name
                },
                "quantity": quantity
            }
            for (size, color_id, color_name), quantity in grouped_availabilities.items()
        ]

        # Serialize the result
        serializer = ProductAvailabilityBreifedSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AdminPayRequestCreateView(generics.CreateAPIView):
    queryset = PayRequest.objects.all()
    serializer_class = PayRequestSerializer
    permission_classes = [IsAdminUser]  
    parser_classes = [MultiPartParser, FormParser] 

    def perform_create(self, serializer):
        # Ensure the pill exists
        pill_id = self.request.data.get('pill')
        try:
            pill = Pill.objects.get(id=pill_id)
            # Check if the pill is already paid
            if pill.paid:
                raise serializers.ValidationError("This pill is already paid.")
            # Create the PayRequest with is_applied=True
            serializer.save(pill=pill, is_applied=True)
        except Pill.DoesNotExist:
            raise serializers.ValidationError("Pill does not exist.")
    
class ApplyPayRequestView(generics.UpdateAPIView):
    queryset = PayRequest.objects.all()
    serializer_class = PayRequestSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        # Get the PayRequest instance
        pay_request = self.get_object()

        # Check if the PayRequest is already applied
        if pay_request.is_applied:
            return Response({"error": "This payment request has already been applied."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the associated Pill is already paid
        pill = pay_request.pill
        if pill.paid:
            return Response({"error": "This pill is already paid."}, status=status.HTTP_400_BAD_REQUEST)

        # Update the PayRequest to mark it as applied
        pay_request.is_applied = True
        pay_request.save()

        # Update the associated Pill to mark it as paid
        pill.paid = True
        pill.status = 'p'
        pill.save()
        if pill.pilladdress:
            prepare_whatsapp_message(pill.pilladdress.phone, pill)

        # Return the updated PayRequest
        serializer = self.get_serializer(pay_request)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DashboardLovedProductListView(generics.ListAPIView):
    queryset = LovedProduct.objects.all()
    serializer_class = LovedProductSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'product']

class DashboardLovedProductDetailView(generics.RetrieveDestroyAPIView):
    queryset = LovedProduct.objects.all()
    serializer_class = LovedProductSerializer
    permission_classes = [IsAdminUser]


class LowThresholdProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return Product.objects.annotate(
            available_quantity=Sum('availabilities__quantity')
        ).filter(
            available_quantity__lte=F('threshold')
        ).distinct()







