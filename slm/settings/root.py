"""
Django settings for SLM.

Generated by 'django-admin startproject' using Django 3.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
from pathlib import Path
from django.contrib.messages import constants as message_constants
from slm.settings import is_defined, set_default
from split_settings.tools import include

set_default('DEBUG', False)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
set_default('BASE_DIR', Path(__file__).resolve().parent.parent)
set_default('SITE_DIR', BASE_DIR)
set_default('DJANGO_DEBUG_TOOLBAR', False)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

if is_defined('ALLOWED_HOSTS') and ALLOWED_HOSTS:
    set_default('DEFAULT_FROM_EMAIL', f'noreply@{ALLOWED_HOSTS[0]}')

# Application definition

# django.contrib.___ gives us useful tools for authentication, etc.
INSTALLED_APPS = [
    'slm.map',
    'slm',
    'crispy_forms',
    'crispy_bootstrap5',
    'ckeditor_uploader',
    'ckeditor',
    'polymorphic',
    'rest_framework',
    'render_static',
    'django_filters',
    'compressor',
    'widget_tweaks',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder'
)

# this statement was added during creation of custom user model
AUTH_USER_MODEL = 'slm.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'slm.middleware.SetLastVisitMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'slm.settings.urls'

WSGI_APPLICATION = 'sites.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

# Following two statements added to assist with handling of static files
STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

include('internationalization.py')
include('slm.py')
include('secrets.py')
include('logging.py')
include('templates.py')
include('static_templates.py')
include('routines.py')
include('auth.py')
include('rest.py')
include('debug.py')
include('uploads.py')
include('ckeditor.py')
#include('security.py')
include('validation.py')


set_default('SITE_ID', 1)

set_default('STATIC_ROOT', SITE_DIR / 'static')

COMPRESS_OFFLINE = True
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL

#Path(STATIC_ROOT).mkdir(parents=True, exist_ok=True)
#Path(MEDIA_ROOT).mkdir(parents=True, exist_ok=True)

MESSAGE_LEVEL = message_constants.DEBUG if DEBUG else message_constants.INFO

