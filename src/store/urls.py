from django.urls import path
from .views import (
    StoreRequestListCreateView, StoreRequestRetrieveUpdateDestroyView,
    ApproveStoreRequestView, RejectStoreRequestView,
    StoreListView, StoreRetrieveView,
    StoreReportingListCreateView, StoreReportingRetrieveUpdateView
)

urlpatterns = [
    # Store Requests
    path('store-requests/', StoreRequestListCreateView.as_view(), name='store-request-list'),
    path('store-requests/<int:pk>/', StoreRequestRetrieveUpdateDestroyView.as_view(), name='store-request-detail'),
    path('store-requests/<int:pk>/approve/', ApproveStoreRequestView.as_view(), name='approve-store-request'),
    path('store-requests/<int:pk>/reject/', RejectStoreRequestView.as_view(), name='reject-store-request'),
    
    # Stores
    path('stores/', StoreListView.as_view(), name='store-list'),
    path('stores/<int:pk>/', StoreRetrieveView.as_view(), name='store-detail'),
    
    # Store Reporting
    path('store-reports/', StoreReportingListCreateView.as_view(), name='store-report-list'),
    path('store-reports/<int:pk>/', StoreReportingRetrieveUpdateView.as_view(), name='store-report-detail'),
]