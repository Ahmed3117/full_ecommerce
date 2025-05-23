from django.contrib.auth.models import AbstractUser
from django.db import models

GOVERNMENT_CHOICES = [
    ('1', 'Cairo'),
    ('2', 'Alexandria'),
    ('3', 'Kafr El Sheikh'),
    ('4', 'Dakahlia'),
    ('5', 'Sharqia'),
    ('6', 'Gharbia'),
    ('7', 'Monufia'),
    ('8', 'Qalyubia'),
    ('9', 'Giza'),
    ('10', 'Beni Suef'),
    ('11', 'Fayoum'),
    ('12', 'Minya'),
    ('13', 'Assiut'),
    ('14', 'Sohag'),
    ('15', 'Qena'),
    ('16', 'Luxor'),
    ('17', 'Aswan'),
    ('18', 'Red Sea'),
    ('19', 'Beheira'),
    ('20', 'Ismailia'),
    ('21', 'Suez'),
    ('22', 'Port Said'),
    ('23', 'Damietta'),
    ('24', 'Matruh'),
    ('25', 'New Valley'),
    ('26', 'North Sinai'),
    ('27', 'South Sinai'),
]

USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('store', 'Store'),
    ]
    
YEAR_CHOICES = [
        ('first-secondary', 'First Secondary'),
        ('second-secondary', 'Second Secondary'),
        ('third-secondary', 'Third Secondary'),
    ]

class User(AbstractUser):
    name = models.CharField(max_length=100)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    email = models.EmailField(blank=True, null=True, max_length=254)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES,default="student", null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    year = models.CharField(
        max_length=20, 
        choices=YEAR_CHOICES, 
        null=True, 
        blank=True,
        help_text="Only applicable for students"
    )

    def __str__(self):
        return self.name if self.name else self.username


class StudentData(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'}
    )
    year = models.CharField(
        max_length=20, 
        choices=YEAR_CHOICES, 
        null=True, 
        blank=True
    )
    
    def __str__(self):
        return f"{self.user.name}'s student data"


class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=150)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    address = models.CharField(max_length=255)
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.address}"

    def save(self, *args, **kwargs):
        # If this address is being set as default
        if self.is_default:
            # Get all other addresses for this user
            other_addresses = UserAddress.objects.filter(user=self.user)
            
            # If this is an existing instance, exclude it from the update
            if self.pk:
                other_addresses = other_addresses.exclude(pk=self.pk)
            
            # Update all other addresses to not be default
            other_addresses.update(is_default=False)
        
        # If this is the first address being created for the user, set it as default
        elif not UserAddress.objects.filter(user=self.user).exists():
            self.is_default = True
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'User Addresses'
        ordering = ['-is_default', '-created_at']








