"""
Development settings for KuralAgri.
"""
from .base import *  # noqa: F401,F403

DEBUG = True

# In dev, allow all hosts
ALLOWED_HOSTS = ['*']

# Disable throttling in dev for easier testing
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []  # noqa: F405
CORS_ALLOW_ALL_ORIGINS = True

# Use console email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Log SQL queries in dev (optional — uncomment to debug)
# LOGGING = {
#     'version': 1,
#     'handlers': {'console': {'class': 'logging.StreamHandler'}},
#     'loggers': {
#         'django.db.backends': {'handlers': ['console'], 'level': 'DEBUG'},
#     },
# }
