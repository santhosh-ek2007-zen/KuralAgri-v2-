"""
Django base settings for KuralAgri.
Shared across dev and prod. Environment-specific settings override in dev.py / prod.py.
"""
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR.parent / '.env')
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'insecure-dev-key-replace-me')

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ----- Application definition -----

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    # Project apps
    'common',
    'users',
    'catalog',
    'notifications',
    'marketplace',
    'matching',
    'intelligence',
    'finance',
    'logistics',
    'quality',
    'settlement',
    'seed',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ----- Database -----

DATABASES = {
    'default': dj_database_url.config(
        default='postgres://kuralagri:kuralagri_dev@localhost:5432/kuralagri',
        conn_max_age=600,
    )
}

# ----- Auth -----

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
]

# ----- Internationalization -----

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ----- Static files -----

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ----- REST Framework -----

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/min',
        'user': '100/min',
    },
    'COERCE_DECIMAL_TO_STRING': True,  # Keep money as strings in JSON to avoid float
}

# ----- JWT -----

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ----- CORS -----

CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# ----- OpenAPI / Spectacular -----

SPECTACULAR_SETTINGS = {
    'TITLE': 'KuralAgri API',
    'DESCRIPTION': 'Produce Destination, Pricing & Settlement Marketplace — SIH MVP',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# ----- Security -----

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ----- Feature flags -----

ENABLE_LIVE_MANDI = os.environ.get('ENABLE_LIVE_MANDI', 'false').lower() == 'true'
ENABLE_LIVE_WEATHER = os.environ.get('ENABLE_LIVE_WEATHER', 'false').lower() == 'true'
ENABLE_LIVE_ROUTING = os.environ.get('ENABLE_LIVE_ROUTING', 'false').lower() == 'true'
DEMO_MODE = os.environ.get('DEMO_MODE', 'true').lower() == 'true'

# ----- File upload limits -----

DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
