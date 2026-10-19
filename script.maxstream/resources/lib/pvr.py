# -*- coding: utf-8 -*-
"""Synchronisation with Kodi's TV menu through PVR IPTV Simple Client.

MaxStream writes a local M3U (live channels of the active playlist) and keeps a
copy of the XMLTV guide, then registers them as an IPTV Simple instance
("MaxStream") so the channels appear in Kodi > TV with Kodi's own guide."""
import json
import os
import re
import time
from xml.sax.saxutils import escape

import xbmc
import xbmcvfs

from . import storage, ui
from .common import PROFILE, ensure_dir, get_bool, get_int, log, replace_file

PVR_ADDON = 'pvr.iptvsimple'
PVR_DIR = os.path.join(PROFILE, 'pvr')
M3U_PATH = os.path.join(PVR_DIR, 'channels.m3u')
EPG_PATH = os.path.join(PVR_DIR, 'epg.xml')
INSTANCE_NAME = 'MaxStream'


def enabled():
    return get_bool('pvr_sync', False)


def _attr(value):
    return str(value or '').replace('"', "'").replace('\n', ' ').strip()


def export_m3u(playlist, prov):
    """Write the active playlist's live channels to M3U_PATH. Returns the channel count."""
    cats = dict((c['id'], c['name']) for c in prov.categories('live'))
    hidden = set(c[0] for c in storage.hidden_categories(playlist['id']).data['live'])
    exclude_locked = get_bool('pvr_exclude_locked', True) and ui.parental_enabled()
    xtream = playlist.get('type') == 'xtream'
    lines = ['#EXTM3U']
    count = 0
    for ch in prov.all_items('live'):
        group = cats.get(ch.get('cat'), '')
        if ch.get('cat') in hidden or (exclude_locked and ui.is_adult(group)):
            continue
        url = prov.stream_url('live', ch['id'])
        if not url:
            continue
        attrs = [('tvg-id', ch.get('epg_id')), ('tvg-name', ch['name']), ('tvg-logo', ch.get('icon')),
                 ('tvg-chno', ch.get('num')), ('group-title', group)]
        if ch.get('catchup'):
            if xtream:
                attrs += [('catchup', 'xc'), ('catchup-days', ch.get('catchup_days') or 7)]
            else:
                attrs += [('catchup', ch.get('catchup_mode') or 'default'),
                          ('catchup-source', ch.get('catchup_source')),
                          ('catchup-days', ch.get('catchup_days') or 7)]
        text = ' '.join('%s="%s"' % (k, _attr(v)) for k, v in attrs if v not in (None, ''))
        lines.append('#EXTINF:-1 %s,%s' % (text, _attr(ch['name'])))
        lines.append(url)
        count += 1
    ensure_dir(PVR_DIR)
    tmp = M3U_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines) + '\n')
    replace_file(tmp, M3U_PATH)
    log('PVR export: %d channels' % count)
    return count


# ---------------------------------------------------------------- IPTV Simple instance
def _instance_dir():
    return xbmcvfs.translatePath('special://profile/addon_data/%s/' % PVR_ADDON)


def _setting(xml, sid):
    match = re.search(r'<setting id="%s"[^>]*>([^<]*)</setting>' % re.escape(sid), xml)
    return match.group(1) if match else ''


def _instance_file():
    """Our existing instance, else an unconfigured one to reuse, else the next free number."""
    folder = ensure_dir(_instance_dir())
    used, reusable = {}, None
    for name in os.listdir(folder):
        match = re.match(r'instance-settings-(\d+)\.xml$', name)
        if not match:
            continue
        with open(os.path.join(folder, name), encoding='utf-8', errors='replace') as handle:
            xml = handle.read()
        used[int(match.group(1))] = name
        if _setting(xml, 'kodi_addon_instance_name') == INSTANCE_NAME:
            return os.path.join(folder, name)
        if reusable is None and not _setting(xml, 'm3uPath') and not _setting(xml, 'm3uUrl'):
            reusable = name
    if reusable:
        return os.path.join(folder, reusable)
    num = 1
    while num in used:
        num += 1
    return os.path.join(folder, 'instance-settings-%d.xml' % num)


def write_instance():
    values = [
        ('kodi_addon_instance_name', INSTANCE_NAME),
        ('kodi_addon_instance_enabled', 'true'),
        ('m3uPathType', '0'),
        ('m3uPath', M3U_PATH),
        ('m3uRefreshMode', '1'),
        ('m3uRefreshIntervalMins', '60'),
        ('epgPathType', '0'),
        ('epgPath', EPG_PATH),
        ('epgTimeShift', str(get_int('epg_offset', 0))),
        ('logoFromEpg', '1'),
        ('catchupEnabled', 'true'),
    ]
    body = '\n'.join('    <setting id="%s">%s</setting>' % (k, escape(v)) for k, v in values)
    path = _instance_file()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('<settings version="2">\n%s\n</settings>\n' % body)
    replace_file(tmp, path)
    return path


def _rpc(method, **params):
    return xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}))


def restart_pvr_addon():
    _rpc('Addons.SetAddonEnabled', addonid=PVR_ADDON, enabled=False)
    time.sleep(1.5)
    _rpc('Addons.SetAddonEnabled', addonid=PVR_ADDON, enabled=True)
