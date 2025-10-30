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
    'gestion_escolar',	
    'import_export',
]

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

# Agrega esta línea para configurar archivos estáticos
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'gestion_escolar/static'),
]

LOGIN_URL = '/login/'

# Media files (user uploaded files)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Google Sheets API Configuration
GOOGLE_SHEETS_CREDENTIALS = {}
  "type": "service_account",
  "project_id": "integracionappvacanciasdjango",
  "private_key_id": "c35fdd98e3ed8dfae53e9128e840e4a07fde2c49",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDSvl4RtX8wdyQZ\nG2Nfa8CCiCt6M/C1qtF8lXkrsV3ZPOMYgIQpGtqsmesiSRZM/X/kKWvuuErq3FJn\n6I63ED2Vd1uZVLRNc+4E1rVsyaDyNxg0wuRKNdJI7y4o+K5Imapg5L/dbF85u6nq\nLYnUGryda8Paf6gROSGUCI1q37iF2c1aHRnEsp3sS/HILW1JK/2PsD9LUgKvjOit\n+0vnDAFrwID6F6DfeBuTDj5ffdzKLUI3Z+wM72iE1KiUUZHeFZ9e95AWXBbJljzN\nXWDg7xmP1KlQvdTFpvZuzhyQ/EG+Ew34YaoHWMyEYJdD/+gLYAennWOttPDg0CkL\nIzesRKExAgMBAAECggEATzyWX/Au10kkgHAkx97arfmG51aaHaQRSddljMEOeTyE\nYlUH2/Cl4Zmpp+V1BhOWP3I3i7UtLesS7NCqwDfR/921ygvoEusQxi74XePdqNSA\nPG4+qYxc+WE8qNj/pnpobi/z18wEbc+ajlr65I389u9q3z96MKebcW5ZxaJCXcic\nwuCcBZJ6Nq/6v0vbQ43qwCdnuHQGKQ3hGuN3AYjqyxVqKqgcH+Apip5aYOjtY8di\nmeTCdLkgGDtu/PpKTCLOMi85C0AU5GJVdgz1jZu8GDSaw5Y0TC3XZuxrpi70xdwm\n2zMC9vx0RoduheM9/lLBkxB2gBl3pZWkUty/tTdjJQKBgQDwNSQX3SG3FHRu6m8b\nUWiT1zMGslpEAcLVsxtc1B+/KPGayK7U4mOE39btI6oiCgSCv0/B2iEoDMaXRJcK\nVL+YTlFrNyf4jy7ARx0lkCnOX/4uCu2nVVM1F/yWMsv1AHVOOM38x2UPZ7w8tmXt\nLKW0+gpE7/x4Hy3r56Q46s28xwKBgQDgmVPnS8O6VYnjmNixSMwQYh9IiThr6vM5\nXCyI0tKII3420qA8XlyfezAzZKnuQLz0xe0rtdP9EhG2QZ4CHTRNA/rwLvMfMILq\nXYVa5zQBBOGzwbmyTVhnTxHpPvZ+qaN59eSWB64OQxMcwUJL47JLDeHP9Dul8uVy\ni1Mq6P6KRwKBgD1MEk3UrEnf+mZjhL7f42P2wpqu4MICAQovjof9yawqcp0hIRxK\nOUMrK9mQBFZzX/tNfrjlRRjHSdZINpL4VXw0YCqQBK81OqTugM2ZIFH9xQtS1pqg\n937RBC///nQjDcxMSqR67ZskybBki1Ye0pqARCabZz3wFvPgRNQRdzb5AoGAemFR\npJBWACwnzEo2mLMv7iVpIl8SzUriaPjek1c8vE2KslimUv6fvY6kPvy000uXKlDG\n4LBc6GJ2IDc037YGD4kBrOoIM5B9ZTK8PUIJxhxg10/R3WPjrbcZ7VwPeAj7OLNR\ncKaSotbNjTeI5k0Vk2vnBSbxcYUenQFpudHnEHUCgYEAzq6wm5k7OMUyF1Q2ilUQ\nIpU8Z1ronkt5g4RYYQaffcUEjq609bXUUUKldyRIx/O71ESih2x9q9JGFweY9m/7\nfuRyYbM5c3+Pd0avd1xUA+7O5pFwGoGN4cnXkr5I1i/e7MkgRjA5QtgCB6aneM+z\nVaDSKGY3U1idYnI1do3bDnE=\n-----END PRIVATE KEY-----\n",
  "client_email": "escritor-datos-sheets@integracionappvacanciasdjango.iam.gserviceaccount.com",
  "client_id": "113277394261463832867",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/escritor-datos-sheets%40integracionappvacanciasdjango.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
GOOGLE_SHEET_ID = '1Svs7eClLiHezipj9RnV_Q8yNuxJbxew--OqKemOeoSs'
GOOGLE_SHEET_WORKSHEET_NAME = 'DatosVacancias'
