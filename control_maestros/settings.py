from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-1jnsz#&ybd0gsi(fc8*krwv865u2h5-=4s3+pv!0njfrz7%q1e'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '10.6.17.187']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'colorfield',
    'gestion_escolar',	
    'import_export',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'gestion_escolar.middleware.LoginRequiredMiddleware',  # Middleware personalizado
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'control_maestros.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'gestion_escolar.context_processors.notifications_processor',
                'gestion_escolar.context_processors.active_theme_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'control_maestros.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Mexico_City'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


import os
import json

# Agrega esta línea para configurar archivos estáticos
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'gestion_escolar/static'),
]

LOGIN_URL = '/login/'

# Media files (user uploaded files)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Google Sheets API Configuration
# ADVERTENCIA DE SEGURIDAD: Las credenciales de la API de Google Sheets son un secreto
# y NO deben ser versionadas en un repositorio público.
# Se recomienda cargarlas desde un archivo local que esté en .gitignore.

# Ruta al archivo de credenciales local (debe estar en .gitignore)
LOCAL_SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'service_account_local.json')

GOOGLE_SHEETS_CREDENTIALS = {}
if os.path.exists(LOCAL_SERVICE_ACCOUNT_FILE):
    try:
        with open(LOCAL_SERVICE_ACCOUNT_FILE, 'r') as f:
            GOOGLE_SHEETS_CREDENTIALS = json.load(f)
    except Exception as e:
        pass # Opcional: loggear el error sin imprimir en consola
else:
    pass # Opcional: loggear la advertencia sin imprimir en consola

# Cargar IDs desde variables de entorno (o directamente si no son sensibles)
# Si GOOGLE_SHEET_ID y GOOGLE_SHEET_WORKSHEET_NAME no son secretos, pueden estar aquí directamente.
# Si son sensibles, se recomienda cargarlos también desde variables de entorno.
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '1Svs7eClLiHezipj9RnV_Q8yNuxJbxew--OqKemOeoSs') # Usar valor por defecto si no está en .env
GOOGLE_SHEET_WORKSHEET_NAME = os.getenv('GOOGLE_SHEET_WORKSHEET_NAME', 'DatosVacancias') # Usar valor por defecto si no está en .env