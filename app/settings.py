"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 2.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'k=k(0d)&vr&_d4lemzqv1s-xep%*-d8njhq=*s&91*sk70@x&#'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Allow all origins for cors.
CORS_ORIGIN_ALLOW_ALL=True

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'djoser',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',

    # add CORS (Cross-Origin Resource Sharing) headers to responses.
    'corsheaders',

    'address',
    'blockchain',
    'order',
    'otp',
    'spauser',
    'spaprofile',
    'trade',
    'reporting',
    'wallet',
]

MIDDLEWARE = [
    # corsheaders needs to be on top.
    'corsheaders.middleware.CorsMiddleware',

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
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

WSGI_APPLICATION = 'app.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}

DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.postgresql',
       'NAME': 'postgres',
       'USER': 'postgres',
       'PASSWORD': 'locald3v',
       'HOST': 'db'
   }
}

AUTH_USER_MODEL = 'spauser.SpaUser'

REST_SESSION_LOGIN = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

REST_FRAMEWORK = {
    'DEFAULT_PERMMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'otp.permissions.IsOtpVerified',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

DJOSER = {
    'SEND_ACTIVATION_EMAIL': False,
    'PASSWORD_RESET_CONFIRM_URL': '#/password/reset/confirm/{uid}/{token}',
    'ACTIVATION_URL': '#/activate/{uid}/{token}',
    'SET_PASSWORD_RETYPE': False,
    'LOGOUT_ON_PASSWORD_CHANGE': True,
    'PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND': False,
}

JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(minutes=15),
    'JWT_ALLOW_REFRESH': True,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(hours=12),
    'JWT_GET_USER_SECRET_KEY': 'spauser.models.jwt_get_secret_key',
    'JWT_PAYLOAD_HANDLER': 'spauser.utils.jwt_otp_payload',
}

ADDRESSAPI = {
    'protocol': 'http',
    'domain': 'addressapi',
    'port': 8001,
}

COINS = {
    'BTC': {
        'name': 'bitcoin',
        'server': 'bitcoin:8332',
        'rpcauth': 'AFwy9VfUcNWouMG1ufW3EgtavyFJhUJhCRxVnBEBr4t4DeBHCu:qcWFdSLXGPZdzReV3ee7miEXqizoPCVmhDZvgX1oLSZ49WVoyx',
        'bip44_index': 0,
        'account_index': 0,
    },
    'XTN': {
        'name': 'bitcoin_testnet3',
        'server': 'bitcoin-testnet3:18332',
        'rpcauth': 'bitcointest:testbitcoin',
        'bip44_index': 1,
        'account_index': 0,
    },
    'LTC': {
        'name': 'litecoin',
        'server': 'litecoin:9332',
        'rpcauth': '4MYPO8lKknVfS3RCDNJ3apoUCR7MYRaJHjBZsNYMvbhMTfPMud:lHS9MTG6SM7ayDaSJtQ4o6odaTfZSdHyNrZWUHgvDSBlqlbsVO',
        'bip44_index': 2,
        'account_index': 0,
    },
    'XLT': {
        'name': 'litecoin_testnet4',
        'server': 'litecoin-testnet4:19332',
        'rpcauth': 'litecointest:litecointest',
        'bip44_index': 1,
        'account_index': 2,
    },
    'DOGE': {
        'name': 'dogecoin',
        'server': 'dogecoin:22555',
        'rpcauth': 'dogecoin:dogecoin',
        'bip44_index': 3,
        'account_index': 0,
    },
    'XDT': {
        'name': 'dogecoin_testnet3',
        'server': 'dogecoin-testnet3:44555',
        'rpcauth': 'dogecointest:testdogecoin',
        'bip44_index': 1,
        'account_index': 3,
    },
}

CRYPTOPAIRS = {
    # bitcoin testnet / litecoin testnet
    'XTN-XLT': {
        'base': 'XTN',
        'quote': 'XLT',
        'listed': True,
    },
    # bitcoin testnet / dogecoin testnet
    'XTN-XDT': {
        'base': 'XTN',
        'quote': 'XDT',
        'listed': True,
    },
    # litecoin testnet / dogecoin testnet
    'XLT-XDT': {
        'base': 'XLT',
        'quote': 'XDT',
        'listed': True,
    },

    'BTC-LTC': {
        'base': 'BTC',
        'quote': 'LTC',
        'listed': False,
    },
    'BTC-DOGE': {
        'base': 'BTC',
        'quote': 'DOGE',
        'listed': False,
    },
    'LTC-DOGE': {
        'base': 'LTC',
        'quote': 'DOGE',
        'listed': False,
    },
}
