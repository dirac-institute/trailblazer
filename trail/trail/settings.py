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


TRAILBLAZER_ENV = os.environ.get("TRAILBLAZER_ENV", default="local")
TRAILBLAZER_CONFIG_DIR = Path(os.environ.get("TRAILBLAZER_CONFIG_DIR",
                                             default=BASE_DIR / "config/"))


siteConfig = config.Config.fromYaml(TRAILBLAZER_CONFIG_DIR / "site.yaml")
loggingConfig = config.Config.fromYaml(TRAILBLAZER_CONFIG_DIR / "logging.yaml")


# avoids problematic Windows file permissions when loading default YAMLs by
# instantiating from existing hardcoded defaults...
if TRAILBLAZER_ENV == "local":
    secrets = config.SecretsConfig()
    if "db" in siteConfig:
        secrets.db.name = siteConfig.resolveAbsFromOrigin(siteConfig.db.name)
else:
    secrets = config.SecretsConfig.fromYaml(config.get_secrets_filepath())

SMALL_THUMB_ROOT = siteConfig.resolveAbsFromOrigin(siteConfig.thumbnails.small_root)
LARGE_THUMB_ROOT = siteConfig.resolveAbsFromOrigin(siteConfig.thumbnails.large_root)
DATA_ROOT = siteConfig.resolveAbsFromOrigin(siteConfig.data_root)


API_DOC_TITLE = siteConfig.api_doc.title
API_DOC_DEFAULT_VER = siteConfig.api_doc.version
API_DOC_DESCRIPTION = siteConfig.api_doc.description
API_DOC_CONTACT_EMAIL = siteConfig.api_doc.contact_email
API_DOC_LICENSE_NAME = siteConfig.api_doc.license.name
API_DOC_LICENSE_URL = siteConfig.api_doc.license.url

STATIC_ROOT = DATA_ROOT
STATIC_URL = '/static/'

MEDIA_ROOT = SMALL_THUMB_ROOT
MEDIA_URL = '/media/'

# ASTROMETRY_KEY = siteConfig.astrometry_net.key
# ASTROMETRY_TIMEOUT = siteConfig.astrometry_net.timeout
ASTROMETRY_KEY = ""
ASTROMETRY_TIMEOUT = ""

if "gallery_image_count" in siteConfig:
    GALLERY_IMAGE_COUNT = siteConfig.gallery_image_count
else:
    GALLERY_IMAGE_COUNT = 12


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
    'drf_yasg',
]


LOGGING = loggingConfig.asDict()

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
