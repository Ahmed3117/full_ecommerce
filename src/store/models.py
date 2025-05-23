from django.db import models
from django.core.validators import FileExtensionValidator

from accounts.models import User

class StoreRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('refused', 'Refused'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='store_requests'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    image = models.ImageField(
        upload_to='store_requests/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    government = models.CharField(max_length=100)
    address = models.TextField()
    phone1 = models.CharField(max_length=20)
    phone2 = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField()
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    facebook_link = models.URLField(null=True, blank=True)
    telegram_link = models.URLField(null=True, blank=True)
    instagram_link = models.URLField(null=True, blank=True)
    youtube_link = models.URLField(null=True, blank=True)
    tiktok_link = models.URLField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    refuse_reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Store Request from {self.first_name} {self.last_name}"


class Store(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'store'},
        related_name='store'
    )
    name = models.CharField(max_length=100)
    image = models.ImageField(
        upload_to='stores/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    government = models.CharField(max_length=100)
    address = models.TextField()
    phone1 = models.CharField(max_length=20)
    phone2 = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField()
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    facebook_link = models.URLField(null=True, blank=True)
    telegram_link = models.URLField(null=True, blank=True)
    instagram_link = models.URLField(null=True, blank=True)
    youtube_link = models.URLField(null=True, blank=True)
    tiktok_link = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.name


class StoreReporting(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='store_reports'
    )
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False)

    def __str__(self):
        return f"Report on {self.store.name} by {self.user.username}"