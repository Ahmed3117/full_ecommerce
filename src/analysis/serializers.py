
from rest_framework import serializers

from products.models import Category, Product

class ProductAnalyticsSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    total_available = serializers.IntegerField()
    total_added = serializers.IntegerField() 
    total_sold = serializers.IntegerField()
    revenue = serializers.FloatField()
    average_rating = serializers.FloatField()
    total_ratings = serializers.IntegerField()
    has_discount = serializers.BooleanField()
    current_discount = serializers.FloatField()
    price_after_discount = serializers.FloatField()
    threshold = serializers.IntegerField()
    is_low_stock = serializers.SerializerMethodField()
    def get_category_name(self, obj):
        return obj.category.name if obj.category else "No Category"
    def get_is_low_stock(self, obj):
        return obj.total_quantity() <= obj.threshold
    
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category_name', 'total_available', 'total_added',
            'total_sold', 'revenue', 'average_rating', 'total_ratings',
            'price', 'has_discount', 'current_discount', 'price_after_discount','threshold', 'is_low_stock',
            'date_added'
        ]

class CategoryAnalyticsSerializer(serializers.ModelSerializer):
    total_products = serializers.IntegerField()
    total_sales = serializers.IntegerField()
    revenue = serializers.FloatField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'total_products', 'total_sales', 'revenue']

class InventoryAlertSerializer(serializers.ModelSerializer):
    total_available = serializers.IntegerField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'total_available', 'category']


class SalesTrendSerializer(serializers.Serializer):
    total_sales = serializers.IntegerField()
    revenue = serializers.FloatField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()





