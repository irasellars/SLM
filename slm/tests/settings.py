from pathlib import Path

from slm.settings import resource
from split_settings.tools import include

#2023/11/10 ira.sellars Add DEBUG, ALLOWED_HOST, GDAL and DATABASE
DEBUG = True
ALLOWED_HOSTS = []

SITE_DIR = Path(__file__).resolve().parent / 'tmp'

GDAL_LIBRARY_PATH = 'C:/django/SLM/venv_slm/Lib/site-packages/osgeo/gdal304.dll'
GEOS_LIBRARY_PATH = 'C:/django/SLM/venv_slm/Lib/site-packages/osgeo/geos_c.dll'

include(resource('slm.settings', 'root.py'))

#2023/11/10 ira.sellars Test locally
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'OPTIONS':{
            'options':'-c search_path=ncnslm'
        },
        'NAME': 'ilspgdb',
        'USER': 'ncnslm',
        'PASSWORD': 'ncnslm',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

SLM_PRELOAD_SCHEMAS = False

#2023/11/10 ira.sellars Need these too 
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False