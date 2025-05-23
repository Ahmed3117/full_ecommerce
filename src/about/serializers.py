from rest_framework import serializers
from about.models import FAQ, About, AboutDescription, Count

class AboutDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutDescription
        fields = '__all__'


class AboutSerializer(serializers.ModelSerializer):
    descriptions = serializers.SerializerMethodField()

    class Meta:
        model = About
        fields = [
            'id', 'title', 'subtitle', 'description', 'image','email',
            'phone1', 'phone2', 'whatsapp_number',
            'facebook_link', 'telegram_link', 'instagram_link',
            'youtube_link', 'tiktok_link',
            'descriptions'
        ]

    def get_descriptions(self, obj):
        descriptions = obj.descriptions.filter(is_active=True).order_by('order')
        return AboutDescriptionSerializer(descriptions, many=True).data

#------------- Counts -------------#    
class CountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Count
        fields = ['id', 'subscribers_count', 'doctors_count', 'students_count']
#------------- FAQ -------------#

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'
