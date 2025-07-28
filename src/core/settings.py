"""
Django settings for core project.
Django 5.1.2
"""

from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import os

#^ Load environment variables from .env file
load_dotenv(override=True) 

#^ Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

#^ SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

#^ SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG')

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '13.39.129.66', '192.168.1.6', '*']


#^ Application definition 

INSTALLED_APPS = [ 
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #* Libs
    'corsheaders',
    'django_filters',
    'rest_framework',
    'rest_framework.authtoken',  # Added for Token authentication
    'rest_framework_api_key',
    'rest_framework_simplejwt',
    'storages',
    #* Apps
    'accounts',
    'about',
    'products',
    'store',
    'analysis',

]

AUTH_USER_MODEL ='accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

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

WSGI_APPLICATION = 'core.wsgi.application'


#^ DATABASES
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('DATABASE_NAME'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
"""

#^ Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


#^ Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


#^ < ==========================Static Files========================== >
STATIC_URL = 'static/'
#STATICFILES_DIRS = os.path.join(BASE_DIR, 'static')
STATIC_ROOT = 'static/'

#^ < ==========================Media Files========================== >
MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_NUMBER_FIELDS=50000


#^ < ==========================Email========================== >
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'platraincloud@gmail.com'
EMAIL_HOST_PASSWORD = 'meczfpooichwkudl'

#^ < ==========================CACHES CONFIG========================== >

# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',  
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }


#^ < ==========================REST FRAMEWORK SETTINGS========================== >

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',    # For anonymous users
        'rest_framework.throttling.UserRateThrottle',    # For authenticated users
    ],

    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/day',   # Limit anonymous users to 10 requests per day
        'user': '3000/hour' # Limit authenticated users to 1000 requests per hour
    },

    'DEFAULT_PAGINATION_CLASS': 'accounts.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 100,
}




# ^ < ==========================AUTHENTICATION CONFIG========================== >

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=3),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=3),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": "Bearer",
    "AUTH_HEADER_NAME": "HTTP_AUTH",
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
}

# ^ < ==========================CORS ORIGIN CONFIG========================== >

# Update CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'Authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'auth',  
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Add these for preflight requests
CORS_PREFLIGHT_MAX_AGE = 86400

# ^ < ==========================WHATSAPP CONFIG========================== >

#* WHATSAPP CREDENTIALS
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_ID = os.getenv('WHATSAPP_ID')

# ^ < ==========================AWS CONFIG========================== >

"""
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
AWS_S3_CUSTOM_DOMAIN = "%s.s3.amazonaws.com" % AWS_STORAGE_BUCKET_NAME
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_HEADERS = None
AWS_S3_VERIFY = True
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
"""

# ^ < ==========================Khazenly CONFIG========================== >
# Khazenly API Configuration - with debug prints
KHAZENLY_BASE_URL = os.getenv('KHAZENLY_BASE_URL', 'https://khazenly4--test.sandbox.my.site.com')
KHAZENLY_CLIENT_ID = os.getenv('KHAZENLY_CLIENT_ID', '')
KHAZENLY_CLIENT_SECRET = os.getenv('KHAZENLY_CLIENT_SECRET', '')
KHAZENLY_STORE_NAME = os.getenv('KHAZENLY_STORE_NAME', '')
KHAZENLY_AUTHORIZATION_CODE = os.getenv('KHAZENLY_AUTHORIZATION_CODE', '')
KHAZENLY_REFRESH_TOKEN = os.getenv('KHAZENLY_REFRESH_TOKEN', '') 

# Khazenly Webhook Configuration
KHAZENLY_WEBHOOK_SECRET = os.getenv('KHAZENLY_WEBHOOK_SECRET', '')  # Will be provided by Khazenly


# Fawaterak Configuration - with fallbacks and validation
# Site URL
SITE_URL = os.getenv('SITE_URL', 'https://api2.bookefay.com')
SUCCESS_URL = os.getenv('SUCCESS_URL', 'https://bookefay.com/profile/orders')
FAIL_URL = os.getenv('FAIL_URL', 'https://bookefay.com/profile')
PENDING_URL = os.getenv('PENDING_URL', 'https://bookefay.com')
FAWATERAK_API_KEY = os.getenv('FAWATERAK_API_KEY', '1bdd1c4da30c752efc4e8bd523973e484d8f1c50714cff0b97')
FAWATERAK_PROVIDER_KEY = os.getenv('FAWATERAK_PROVIDER_KEY', 'FAWATERAK.7136')
FAWATERAK_BASE_URL = os.getenv('FAWATERAK_BASE_URL', 'https://app.fawaterk.com/api/v2')
FAWATERAK_WEBHOOK_URL = os.getenv('FAWATERAK_WEBHOOK_URL', f'{SITE_URL}/api/payment/webhook/fawaterak/')
FAWATERAK_USERNAME = os.getenv('FAWATERAK_USERNAME', 'mohamedaymab26@gmail.com')
FAWATERAK_PASSWORD = os.getenv('FAWATERAK_PASSWORD', '1234')

# Validate critical settings
if not FAWATERAK_API_KEY:
    import warnings
    warnings.warn("FAWATERAK_API_KEY is not set in environment variables!")

print(f"🔧 Fawaterak API Key loaded: {FAWATERAK_API_KEY[:20] if FAWATERAK_API_KEY else 'NOT SET'}...")
print(f"🔧 Fawaterak Base URL: {FAWATERAK_BASE_URL}")
print(f"🔧 Site URL: {SITE_URL}")
print(f"🔧 Site URL: {SUCCESS_URL}")
print(f"🔧 Site URL: {FAIL_URL}")
print(f"🔧 Site URL: {PENDING_URL}")

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'khazenly_debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
    },
}
