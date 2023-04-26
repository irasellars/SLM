from logging import Filter
from django.conf import settings
from django.core import serializers
from django.contrib.gis.geos import Point
import json
from PIL import Image, ExifTags
import numpy as np
from math import sqrt, atan2, cos, sin
from datetime import datetime, date, timedelta
from dateutil import parser as date_parser


PROTOCOL = getattr(settings, 'SLM_HTTP_PROTOCOL', None)
GPS_EPOCH = date(year=1980, month=1, day=6)


def dddmmssss_to_decimal(dddmmssss):
    if dddmmssss is not None:
        if isinstance(dddmmssss, str):
            dddmmssss = float(dddmmssss)
        dddmmssss /= 10000
        degrees = int(dddmmssss)
        minutes = (dddmmssss - degrees) * 100
        seconds = float((minutes - int(minutes)) * 100)
        return degrees + int(minutes)/60 + seconds/3600
    return None


def decimal_to_dddmmssss(dec):
    if dec is not None:
        if isinstance(dec, str):
            dec = float(dec)
        degrees = int(dec)
        minutes = (dec - degrees) * 60
        seconds = float(minutes - int(minutes)) * 60
        return degrees*10000 + int(minutes)*100 + seconds
    return None


def dddmmss_ss_parts(dec):
    """
    Return (degrees, minutes, seconds) from decimal degrees
    :param dec: Decimal degrees lat or lon
    :return:
    """
    if dec is not None:
        if isinstance(dec, str):
            dec = float(dec)
        degrees = int(dec)
        minutes = (dec - degrees) * 60
        seconds = float(minutes - int(minutes)) * 60
        return degrees, abs(int(minutes)), abs(seconds)
    return None, None, None


def set_protocol(request):
    global PROTOCOL
    if not PROTOCOL:
        PROTOCOL = 'https' if request.is_secure() else 'http'


def get_protocol():
    global PROTOCOL
    if PROTOCOL is not None:
        return PROTOCOL
    return (
        'https'
        if getattr(settings, 'SECURE_SSL_REDIRECT', False) else
        'http'
    )


def build_absolute_url(path, request=None):
    if path.startswith('mailto:'):
        return path
    if request:
        return request.build_absolute_uri(path)
    return f'{get_url()}/{path.lstrip("/")}'


def get_url():
    from django.contrib.sites.models import Site
    return f'{get_protocol()}://{Site.objects.get_current().domain}'


def from_email():
    from django.contrib.sites.models import Site
    return getattr(
        settings,
        'DEFAULT_FROM_EMAIL',
        f'noreply@{Site.objects.get_current().domain}'
    )


def clear_caches():
    from slm.models import Site
    from slm.models import User
    User.is_moderator.cache_clear()
    Site.is_moderator.cache_clear()


class SquelchStackTraces(Filter):

    def filter(self, record):
        record.exc_info = None
        return super().filter(record)


def to_bool(bool_str):
    if bool_str is None:
        return None
    if isinstance(bool_str, str):
        return not bool_str.lower() in ['0', 'no', 'false']
    return bool(bool_str)


def to_snake_case(string):
    snake = string
    if string:
        snake = string[0].lower()
        new = False
        for char in string[1:]:
            if char == ' ':
                new = True
            elif char.isupper() or new:
                snake += f'_{char.lower()}'
                new = False
            elif char.isalnum():
                snake += char
    return snake


def date_to_str(date_obj):
    if date_obj:
        return f'{date_obj.year}-{date_obj.month:02}-{date_obj.day:02}'
    return ''


def gps_week(date_obj=datetime.now()):
    """
    Return GPS week number for a given datetime, date or date string
    :param date_obj: Date object, datetime object or date string
    :return: 2-tuple: GPS week number, GPS day of week
    :raises ValueError: If date_obj is earlier than the GPS epoch
    """
    # todo move this to igs_tools
    if date_obj is None:
        date_obj = datetime.now().date()
    if isinstance(date_obj, str):
        date_obj = date_parser.parse(date_obj)
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    delta = date_obj - GPS_EPOCH
    if delta.days >= 0:
        return delta.days // 7, delta.days % 7
    raise ValueError(
        f'{date_obj} is earlier than the GPS epoch {GPS_EPOCH}.'
    )


def date_from_gps_week(gps_week, day_of_week=0):
    """
    Return a date object for a given GPS week number and day of week
    :param gps_week: GPS week number
    :param day_of_week: GPS day of week, 0-6
    :return: Date object
    """
    # todo move this to igs_tools
    return GPS_EPOCH + timedelta(days=gps_week*7 + day_of_week)


def day_of_year(date_obj=datetime.now()):
    """
    Return the day of the year for the given object representing a date.

    :param date_obj: Date object, datetime object or date string
    :return: integer day of year
    """
    # todo move this to igs_tools
    if isinstance(date_obj, str):
        date_obj = date_parser.parse(date_obj)
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    return (date_obj - date(date_obj.year, 1, 1) + timedelta(days=1)).days


def http_accepts(accepted_types, mimetype):
    if '*/*' in accepted_types:
        return True
    if mimetype in accepted_types:
        return True
    typ, sub_type = mimetype.split('/')
    if f'{typ}/*' in accepted_types:
        return True
    if f'*/{sub_type}' in accepted_types:
        return True
    return False


class _Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        '''
        elif len(args) > 0:
            config = { }
            for idx, arg in enumerate(args):
                config[idx] = arg
            raise ValueError( self.__class__.__name__ + ' can only be initialized with a configuration once!', config )
        '''

        return cls._instances[cls]

    @classmethod
    def is_instantiated(cls, typ):
        return typ in cls._instances

    @classmethod
    def destroy(cls, typ):
        if typ in cls._instances:
            del cls._instances[typ]


class Singleton(_Singleton('SingletonMeta', (object,), {})):
    pass


class SectionEncoder(json.JSONEncoder):

    def default(self, obj):
        from django.db.models import Model, Manager, QuerySet
        from slm.models import SiteSection, Equipment, Manufacturer
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if isinstance(obj, SiteSection):
            return {
                field: getattr(obj, field) for field in obj.site_log_fields()
            }
        if isinstance(obj, Equipment):
            return {
                field: getattr(obj, field) for field in [
                    'model',
                    'manufacturer'
                ]
            }
        if isinstance(obj, Manufacturer):
            return {
                field: getattr(obj, field) for field in ['name']
            }

        if isinstance(obj, Model):
            # catch-all
            return json.loads(serializers.serialize('json', [obj]))[0]

        if isinstance(obj, (Manager, QuerySet)):
            return [related for related in obj.all()]

        if isinstance(obj, Point):
            return obj.coords
        return json.JSONEncoder.default(self, obj)


def get_exif_tags(file_path):
    # not all images have exif, (e.g. gifs)
    image_exif = getattr(Image.open(file_path), '_getexif', lambda: None)()
    if image_exif:
        exif = {
            ExifTags.TAGS[k]: v for k, v in image_exif.items()
            if k in ExifTags.TAGS and type(v) is not bytes
        }
        return exif
    return {}


def xyz2llh(xyz):
    a_e = 6378.1366e3  # meters
    f_e = 1 / 298.25642  # IERS2000 standards
    radians2degree = 45 / atan2(1, 1)

    xyz_array = np.array(xyz) / a_e
    (x, y, z) = (xyz_array[0], xyz_array[1], xyz_array[2])
    e2 = f_e *(2 - f_e)
    z2 = z**2
    p2 = x**2 + y**2
    p = sqrt(p2)
    r = sqrt(p2 + z2)
    mu = atan2(z * (1 - f_e + e2 / r), p)
    phi = atan2(
        z * (1 - f_e) + e2 * (sin(mu))**3,
        (1 - f_e) * (p - e2 * (cos(mu))**3)
    )
    lat = phi * radians2degree
    lon = atan2(y, x) * radians2degree
    if lon < 0:
        lon = lon + 360
    h = a_e * (p * cos(phi) + z * sin(phi) - sqrt(1 - e2 * (sin(phi))**2))

    return lat, lon, h
