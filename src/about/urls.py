from django.urls import path
from .views import *
urlpatterns = [
    path('', SingletonAboutAPIView.as_view(), name='singleton-about'),
    # counts
    path('count/', CountView.as_view(), name='count'),
    # AboutDescription
    path('about-descriptions/', AboutDescriptionListCreateAPIView.as_view(), name='about-description-list-create'),
    path('about-descriptions/<int:pk>/', AboutDescriptionRetrieveUpdateDestroyAPIView.as_view(), name='about-description-detail'),
    # FAQs
    path('faqs/', FAQListCreateAPIView.as_view(), name='faq-list-create'),
    path('faqs/<int:pk>/', FAQRetrieveUpdateDestroyAPIView.as_view(), name='faq-detail'),
    path('faqs_list/', FAQListAPIView.as_view(), name='faq-list-create'), #for customers
]

