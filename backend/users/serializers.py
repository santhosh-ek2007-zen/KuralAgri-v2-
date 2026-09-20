import re
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, FPO, FarmerProfile, BuyerProfile
from notifications.models import Notification


class FPOSerializer(serializers.ModelSerializer):
    class Meta:
        model = FPO
        fields = ['id', 'name', 'registration_number', 'district', 'members_count']


class FarmerProfileSerializer(serializers.ModelSerializer):
    fpo_name = serializers.CharField(source='fpo.name', read_only=True)
    tier_name = serializers.CharField(source='current_tier.__str__', read_only=True)

    class Meta:
        model = FarmerProfile
        fields = [
            'id',
            'village',
            'district',
            'latitude',
            'longitude',
            'fpo',
            'fpo_name',
            'self_delivery_capable',
            'completed_orders',
            'current_tier',
            'tier_name'
        ]


class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = [
            'id',
            'organisation',
            'buyer_type',
            'accepted_grades',
            'daily_capacity_kg',
            'district',
            'latitude',
            'longitude',
        ]


class UserSerializer(serializers.ModelSerializer):
    farmer_profile = FarmerProfileSerializer(read_only=True)
    buyer_profile = BuyerProfileSerializer(read_only=True)
    unread_notifications_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'email',
            'full_name',
            'role',
            'language',
            'farmer_profile',
            'buyer_profile',
            'unread_notifications_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_unread_notifications_count(self, obj):
        return Notification.objects.filter(user=obj, is_read=False).count()


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    language = serializers.CharField(max_length=10, default='en', required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    profile = serializers.DictField(required=False, default=dict)

    def validate_phone(self, value):
        digits = re.sub(r'\D', '', value)
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        if len(digits) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        if User.objects.filter(phone=digits).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return digits

    def validate_password(self, value):
        if not re.search(r'[A-Za-z]', value) or not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one letter and one number.")
        return value

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        role = validated_data['role']

        with transaction.atomic():
            user = User.objects.create_user(**validated_data)

            if role in ('FARMER', 'FPO'):
                fpo_id = profile_data.get('fpo_id')
                fpo_obj = FPO.objects.filter(id=fpo_id).first() if fpo_id else None
                FarmerProfile.objects.create(
                    user=user,
                    village=profile_data.get('village', 'Unknown'),
                    district=profile_data.get('district', 'Theni'),
                    latitude=Decimal(str(profile_data.get('latitude', '9.9457'))),
                    longitude=Decimal(str(profile_data.get('longitude', '77.4779'))),
                    fpo=fpo_obj,
                    self_delivery_capable=profile_data.get('self_delivery_capable', False),
                )
            elif role == 'BUYER':
                BuyerProfile.objects.create(
                    user=user,
                    organisation=profile_data.get('organisation', user.full_name),
                    buyer_type=profile_data.get('buyer_type', 'PREMIUM'),
                    accepted_grades=profile_data.get('accepted_grades', ['A']),
                    daily_capacity_kg=Decimal(str(profile_data.get('daily_capacity_kg', '1000.00'))),
                    district=profile_data.get('district', 'Theni'),
                    latitude=Decimal(str(profile_data.get('latitude', '9.9457'))),
                    longitude=Decimal(str(profile_data.get('longitude', '77.4779'))),
                )

            return user


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = re.sub(r'\D', '', attrs.get('phone', ''))
        if len(phone) == 12 and phone.startswith('91'):
            phone = phone[2:]
        password = attrs.get('password')

        user = authenticate(username=phone, password=password)
        if not user:
            raise serializers.ValidationError({"detail": "Invalid phone number or password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "This account is disabled."})

        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
