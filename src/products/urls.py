from django.urls import path
from .views import *
urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('subcategories/', SubCategoryListView.as_view(), name='subcategory-list'),
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/last10/', Last10ProductsListView.as_view(), name='last-10-products'),
    path('products/<int:id>/', ProductDetailView.as_view(), name='product-detail'),
    path('pills/init/', PillCreateView.as_view(), name='pill-create'),
    path('pills/<int:id>/apply-coupon/', PillCouponApplyView.as_view(), name='pill-apply-coupon'),
    path('pills/<int:pill_id>/address-info/', PillAddressCreateUpdateView.as_view(), name='pill-create-address'),
    path('pills/<int:id>/', PillDetailView.as_view(), name='pill-detail'),
    path('ratings/', CustomerRatingListCreateView.as_view(), name='customer-rating-list-create'),
    path('ratings/<int:pk>/', CustomerRatingDetailView.as_view(), name='customer-rating-detail'),
    path('user-pills/', UserPillsView.as_view(), name='user-pills'),
    path('colors/', getColors.as_view(), name='colors'),
    path('pay-requests/', PayRequestListCreateView.as_view(), name='pay-requests'),
    path('discounts/active/', ProductsWithActiveDiscountAPIView.as_view(), name='active-discounts'),
    path('loved-products/', LovedProductListCreateView.as_view(), name='loved-product-list-create'),
    path('loved-products/<int:pk>/', LovedProductRetrieveDestroyView.as_view(), name='loved-product-detail'),
    # Special Products
    path('special-products/active/', ActiveSpecialProductsView.as_view(), name='active-special-products'),
    # alerts
    path('alerts/stock/', StockAlertCreateView.as_view(), name='create-stock-alert'),
    path('alerts/price-drop/', PriceDropAlertCreateView.as_view(), name='create-price-drop-alert'),
    path('alerts/my-alerts/', UserActiveAlertsView.as_view(), name='user-alerts'),
    path('alerts/mark-notified/<str:alert_type>/<int:alert_id>/', MarkAlertAsNotifiedView.as_view(), name='mark-alert-notified'),
    # products suggestions
    path('products/new-arrivals/', NewArrivalsView.as_view(), name='new-arrivals'),
    path('products/best-sellers/', BestSellersView.as_view(), name='best-sellers'),
    path('products/frequently-bought-together/', FrequentlyBoughtTogetherView.as_view(), name='frequently-bought-together'),
    path('products/recommendations/', ProductRecommendationsView.as_view(), name='product-recommendations'),
    # spin the wheel
    path('spin-wheel/', SpinWheelView.as_view(), name='spin-wheel'),
    path('spin-wheel/history/', SpinWheelHistoryView.as_view(), name='spin-wheel-history'),

    #^ < ==========================dashboard urls========================== >
    path('dashboard/categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('dashboard/categories/<int:pk>/', CategoryRetrieveUpdateDestroyView.as_view(), name='category-detail'),
    path('dashboard/subcategories/', SubCategoryListCreateView.as_view(), name='subcategory-list-create'),
    path('dashboard/subcategories/<int:pk>/', SubCategoryRetrieveUpdateDestroyView.as_view(), name='subcategory-detail'),
    path('dashboard/brands/', BrandListCreateView.as_view(), name='brand-list-create'),
    path('dashboard/brands/<int:pk>/', BrandRetrieveUpdateDestroyView.as_view(), name='brand-detail'),
    path('dashboard/colors/', ColorListCreateView.as_view(), name='color-list-create'),
    path('dashboard/colors/<int:id>/', ColorRetrieveUpdateDestroyView.as_view(), name='color-retrieve-update-destroy'),
    path('dashboard/products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('dashboard/products-briefed/', ProductListBreifedView.as_view(), name='product-list-breifed'),
    path('dashboard/products/<int:pk>/', ProductRetrieveUpdateDestroyView.as_view(), name='product-detail'),
    path('dashboard/product-images/', ProductImageListCreateView.as_view(), name='product-image-list-create'),
    path('dashboard/product-images/bulk-upload/', ProductImageBulkCreateView.as_view(), name='product-image-bulk-upload'),
    path('dashboard/product-images/<int:pk>/', ProductImageDetailView.as_view(), name='product-image-detail'),
    path('dashboard/pills/', PillListCreateView.as_view(), name='pill-list-create'),
    path('dashboard/pills/<int:pk>/', PillRetrieveUpdateDestroyView.as_view(), name='pill-detail'),
    path('dashboard/coupons/', CouponListCreateView.as_view(), name='coupon-list-create'),
    path('dashboard/coupons/<int:pk>/', CouponRetrieveUpdateDestroyView.as_view(), name='coupon-detail'),
    path('dashboard/shipping/', ShippingListCreateView.as_view(), name='shipping-list-create'),
    path('dashboard/shipping/<int:pk>/', ShippingRetrieveUpdateDestroyView.as_view(), name='shipping-detail'),
    path('dashboard/ratings/', RatingListCreateView.as_view(), name='rating-list-create'),
    path('dashboard/ratings/<int:pk>/', RatingDetailView.as_view(), name='rating-detail'),
    path('dashboard/product-availabilities/', ProductAvailabilityListCreateView.as_view(), name='product-availability-list-create'),
    path('dashboard/product-availabilities/<int:pk>/', ProductAvailabilityDetailView.as_view(), name='product-availability-detail'),
    path('dashboard/products/<int:product_id>/availabilities/', ProductAvailabilitiesView.as_view(), name='product-availabilities'),
    path('dashboard/pay-requests/', AdminPayRequestCreateView.as_view(), name='admin-pay-request-create'),
    path('dashboard/pay-requests/<int:id>/apply/', ApplyPayRequestView.as_view(), name='apply-pay-request'),
    path('dashboard/discounts/', DiscountListCreateView.as_view(), name='discount-list-create'),
    path('dashboard/discounts/<int:pk>/', DiscountRetrieveUpdateDestroyView.as_view(), name='discount-detail'),
    path('dashboard/loved-products/', DashboardLovedProductListView.as_view(), name='dashboard-loved-product-list'),
    path('dashboard/loved-products/<int:pk>/', DashboardLovedProductDetailView.as_view(), name='dashboard-loved-product-detail'),
    path('dashboard/low-threshold-products/', LowThresholdProductsView.as_view(), name='low-threshold-products'),
    # Special Products
    path('dashboard/special-products/', SpecialProductListCreateView.as_view(), name='special-product-list'),
    path('dashboard/special-products/<int:pk>/', SpecialProductRetrieveUpdateDestroyView.as_view(), name='special-product-detail'),
    # Product Descriptions
    path('dashboard/product-descriptions/', ProductDescriptionListCreateView.as_view(), name='product-description-list'),
    path('dashboard/product-descriptions/bulk/', ProductDescriptionBulkCreateView.as_view(), name='product-description-bulk-create'),
    path('dashboard/product-descriptions/<int:pk>/', ProductDescriptionRetrieveUpdateDestroyView.as_view(), name='product-description-detail'),
]

