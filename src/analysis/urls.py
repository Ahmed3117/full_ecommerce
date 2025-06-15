from django.urls import path
from .views import CustomerActivityView, OrderAnalysisView, ProductInventoryView, ProductPerformanceView, CategoryPerformanceView, SalesDashboardView, StoreAnalyticsView


urlpatterns = [
    path('products/', ProductPerformanceView.as_view(), name='product-analytics'),
    path('categories/', CategoryPerformanceView.as_view(), name='category-analytics'),
    # Sales Analysis
    path('sales-dashboard/', SalesDashboardView.as_view(), name='sales-dashboard'),
    path('product-inventory/', ProductInventoryView.as_view(), name='product-inventory'),
    path('order-analysis/', OrderAnalysisView.as_view(), name='order-analysis'),
    path('customer-activity/', CustomerActivityView.as_view(), name='customer-activity'),
    path('store-analytics/', StoreAnalyticsView.as_view(), name='store-analytics'),

]