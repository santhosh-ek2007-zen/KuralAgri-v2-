"""
KuralAgri API URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "service": "kuralagri-backend",
        "version": "1.0.0"
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),

    # OpenAPI schema & Swagger documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API v1 routes
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/catalog/', include('catalog.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/marketplace/', include('marketplace.urls')),
    path('api/v1/matching/', include('matching.urls')),
    path('api/v1/intelligence/', include('intelligence.urls')),
    path('api/v1/finance/', include('finance.urls')),
    path('api/v1/logistics/', include('logistics.urls')),
    path('api/v1/quality/', include('quality.urls')),
    path('api/v1/settlement/', include('settlement.urls')),
    path('api/v1/admin/reset-demo/', __import__('common.views', fromlist=['DemoResetView']).DemoResetView.as_view(), name='reset-demo'),
]
