import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from common.models import BaseModel


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('The phone number must be set')
        phone = phone.strip()
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model keyed on 10-digit Indian phone number.
    Roles: FARMER, FPO, BUYER, ADMIN.
    """
    ROLE_CHOICES = [
        ('FARMER', 'Farmer'),
        ('FPO', 'FPO Administrator'),
        ('BUYER', 'Bulk Buyer'),
        ('ADMIN', 'Platform Administrator'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, db_index=True)
    email = models.EmailField(blank=True, null=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='FARMER', db_index=True)
    language = models.CharField(max_length=10, default='en')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['full_name', 'role']

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.phone}) - {self.role}"


class FPO(BaseModel):
    """
    Farmer Producer Organisation aggregating member farmers.
    """
    name = models.CharField(max_length=150, unique=True)
    registration_number = models.CharField(max_length=50, blank=True)
    district = models.CharField(max_length=100)
    members_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.district})"


class FarmerProfile(BaseModel):
    """
    Profile extension for FARMER and FPO member users.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    village = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    fpo = models.ForeignKey(FPO, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    self_delivery_capable = models.BooleanField(default=False)
    completed_orders = models.PositiveIntegerField(default=0)
    current_tier = models.ForeignKey('catalog.AdvanceTier', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['user__full_name']

    def __str__(self):
        return f"FarmerProfile({self.user.full_name}, {self.village}, {self.district})"


class BuyerProfile(BaseModel):
    """
    Profile extension for BUYER users.
    """
    BUYER_TYPE_CHOICES = [
        ('PREMIUM', 'Premium Buyer'),
        ('SECONDARY', 'Secondary Buyer'),
        ('PROCESSOR', 'Food Processor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    organisation = models.CharField(max_length=150)
    buyer_type = models.CharField(max_length=20, choices=BUYER_TYPE_CHOICES, default='PREMIUM')
    accepted_grades = models.JSONField(default=list)  # e.g., ["A"] or ["A", "B"] or ["B", "C"]
    daily_capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))
    indicative_price_per_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    district = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        ordering = ['organisation']

    def __str__(self):
        return f"{self.organisation} ({self.buyer_type}) - {self.district}"
