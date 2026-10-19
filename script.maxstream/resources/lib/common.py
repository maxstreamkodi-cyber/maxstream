# -*- coding: utf-8 -*-
"""Shared helpers: add-on info, settings, logging, JSON files, formatting."""
import json
import os
import time
import unicodedata

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'script.maxstream'
ADDON = xbmcaddon.Addon(ADDON_ID)

ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

ICON = os.path.join(ADDON_PATH, 'icon.png')
FANART = os.path.join(ADDON_PATH, 'fanart.jpg')

DEFAULT_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
DONATE_URL = 'https://paypal.me/MaxStreamKodi/5EUR'
DEFAULT_ADULT_KEYWORDS = 'adult,xxx,18+,+18,porn,for adults,adultes'


def reload_addon():
    """Settings are cached per Addon instance; long-running code calls this."""
    global ADDON
    ADDON = xbmcaddon.Addon(ADDON_ID)


def L(string_id):
    text = ADDON.getLocalizedString(string_id)
    return text if text else 'string %d' % string_id


def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def log_error(msg):
    log(msg, xbmc.LOGERROR)


# ---------------------------------------------------------------- settings
def get_setting(setting_id, default=''):
    try:
        value = ADDON.getSetting(setting_id)
    except Exception:  # pylint: disable=broad-except
        value = ''
    return value if value not in ('', None) else default


def get_bool(setting_id, default=False):
    value = get_setting(setting_id, None)
    if value is None:
        return default
    return str(value).lower() == 'true'


def get_int(setting_id, default=0):
    try:
        return int(float(get_setting(setting_id, default)))
    except (TypeError, ValueError):
        return default


def set_setting(setting_id, value):
    ADDON.setSetting(setting_id, value)


def open_settings():
    ADDON.openSettings()


# ---------------------------------------------------------------- ui bits
def notify(message, heading=None, icon=None, ms=4000):
    xbmcgui.Dialog().notification(heading or ADDON_NAME, message, icon or ICON, ms)


def has_addon(addon_id):
    return bool(xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id))


def home_prop(key, value=None):
    win = xbmcgui.Window(10000)
    key = '%s.%s' % (ADDON_ID, key)
    if value is None:
        return win.getProperty(key)
    win.setProperty(key, value)
    return value


# ---------------------------------------------------------------- files
def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    return path


def replace_file(src, dst):
    for _ in range(10):
        try:
            os.replace(src, dst)
            return
        except OSError:
            time.sleep(0.3)
    os.replace(src, dst)


def read_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return default


def write_json(path, data):
    ensure_dir(os.path.dirname(path))
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False)
    replace_file(tmp, path)


# ---------------------------------------------------------------- formatting
def epg_offset():
    return get_int('epg_offset', 0) * 3600


def fmt_time(ts):
    t = time.localtime(ts + epg_offset())
    if get_bool('time_24h', True):
        return time.strftime('%H:%M', t)
    return time.strftime('%I:%M %p', t).lstrip('0')


def fmt_day(ts):
    return time.strftime('%a %d/%m', time.localtime(ts + epg_offset()))


def fmt_duration(seconds):
    seconds = int(seconds or 0)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return '%d:%02d:%02d' % (hours, minutes, secs)
    return '%d:%02d' % (minutes, secs)


def fold(text):
    """Lower-case and strip accents, for searching."""
    text = unicodedata.normalize('NFKD', text or '')
    return ''.join(c for c in text if not unicodedata.combining(c)).lower()


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def grey(text):
    return '[COLOR FF9E9E9E]%s[/COLOR]' % text


def accent(text):
    return '[COLOR FF29B6F6]%s[/COLOR]' % text
