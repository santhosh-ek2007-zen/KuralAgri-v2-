from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User, FPO
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    FPOSerializer
)
from common.audit import log_audit_event


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Audit log
        log_audit_event(
            action="AUTH_REGISTER",
            entity_type="User",
            entity_id=str(user.id),
            user=user,
            metadata={"phone": user.phone, "role": user.role},
            ip_address=get_client_ip(request)
        )

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = data['user']

        # Audit log
        log_audit_event(
            action="AUTH_LOGIN",
            entity_type="User",
            entity_id=str(user.id),
            user=user,
            metadata={"phone": user.phone, "role": user.role},
            ip_address=get_client_ip(request)
        )

        return Response({
            'user': UserSerializer(user).data,
            'access': data['access'],
            'refresh': data['refresh'],
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': {'code': 'BAD_REQUEST', 'message': 'Refresh token is required.'}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            log_audit_event(
                action="AUTH_LOGOUT",
                entity_type="User",
                entity_id=str(request.user.id),
                user=request.user,
                ip_address=get_client_ip(request)
            )

            return Response(status=status.HTTP_204_NO_CONTENT)
        except TokenError:
            return Response({'error': {'code': 'INVALID_TOKEN', 'message': 'Token is invalid or already blacklisted.'}}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class FPOListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = FPO.objects.all()
    serializer_class = FPOSerializer
