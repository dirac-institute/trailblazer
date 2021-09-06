"""
Django settings for trail project.

Generated by 'django-admin startproject' using Django 3.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import os

from . import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Path above BASE_DIR (where, e.g., manage.py for the project lives)
REPO_DIR = Path(__file__).resolve().parent.parent.parent


STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


TRAILBLAZER_ENV = os.environ.get("TRAILBLAZER_ENVIRONMENT", default="local")
TRAILBLAZER_CONFIG_DIR = Path(os.environ.get("TRAILBLAZER_CONFIG",
                                             default=BASE_DIR / "config/"))
siteConfig = config.Config.fromYaml(TRAILBLAZER_CONFIG_DIR / "site.yaml")

# avoids problematic Windows file permissions when loading default YAMLs by
# instantiating from existing hardcoded defaults...
if TRAILBLAZER_ENV == "local":
    secrets = config.SecretsConfig()
    SMALL_THUMB_ROOT = os.path.abspath(siteConfig.thumbnails.small_root)
    LARGE_THUMB_ROOT = os.path.abspath(siteConfig.thumbnails.large_root)
    DATA_ROOT = os.path.abspath(siteConfig.data_root)
else:
    secrets = config.SecretsConfig.fromYaml(config.get_secrets_filepath())
    SMALL_THUMB_ROOT = siteConfig.thumbnails.small_root
    LARGE_THUMB_ROOT = siteConfig.thumbnails.large_root
    DATA_ROOT = siteConfig.data_root


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secrets.secret_key


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = siteConfig.debug


ALLOWED_HOSTS = []


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gallery',
    'upload',
    'query',
    'trail',
]


loggingConf = config.Config.fromYaml(TRAILBLAZER_CONFIG_DIR / "logging.yaml")
LOGGING = loggingConf.asDict()


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'trail.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['trail/templates/'],
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


WSGI_APPLICATION = 'trail.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {"default": secrets.db.asDict(capitalizeKeys=True)}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/
ADMIN_MEDIA_PREFIX = '/media/'
