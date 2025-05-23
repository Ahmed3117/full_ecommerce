from django.contrib import admin

from about.models import FAQ

# Register your models here.
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('title', 'description')
        }),
        ('Media', {
            'fields': ('file', 'video_url')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )



