# -*- coding: utf-8 -*-
"""Kodi playback tuning for IPTV streams.

Kodi's default stream buffer is 20 MB (a few seconds of a 4K movie), so when an
IPTV server stalls for a moment the picture freezes. MaxStream can raise the
cache (Settings > Services > Caching, set through JSON-RPC) and add network
retries in advancedsettings.xml so a dropped connection is resumed instead of
ending the video early."""
import json
import os
import re

import xbmc
import xbmcvfs

from .common import PROFILE, log, read_json, write_json

READ_FACTORS = (2000, 1000, 800, 400)  # 20x, 10x, 8x, 4x (Kodi stores x * 100)
FLAGS_FILE = os.path.join(PROFILE, 'flags.json')
NETWORK_BLOCK = ('    <network>\n'
                 '        <curlclienttimeout>20</curlclienttimeout>\n'
                 '        <curlretries>5</curlretries>\n'
                 '    </network>\n')


def rpc(method, **params):
    raw = xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}))
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


def get_setting(setting):
    result = rpc('Settings.GetSettingValue', setting=setting).get('result')
    return result.get('value') if isinstance(result, dict) else None


def set_setting(setting, value):
    return rpc('Settings.SetSettingValue', setting=setting, value=value).get('result') is True


def total_ram_mb():
    match = re.search(r'(\d+)', xbmc.getInfoLabel('System.Memory(total)') or '')
    return int(match.group(1)) if match else 0


def recommended_memory():
    ram = total_ram_mb()
    if ram >= 3500:
        return 256
    if ram >= 1500:
        return 128
    return 64


def needs_tuning():
    memory = get_setting('filecache.memorysize')
    return memory is not None and int(memory) < 64


def already_asked():
    return bool((read_json(FLAGS_FILE, {}) or {}).get('cache_prompted'))


def mark_asked():
    flags = read_json(FLAGS_FILE, {}) or {}
    flags['cache_prompted'] = True
    write_json(FLAGS_FILE, flags)


def write_network_settings():
    """Add curl retries to advancedsettings.xml (taken into account after a Kodi restart)."""
    path = xbmcvfs.translatePath('special://profile/advancedsettings.xml')
    if not os.path.exists(path):
        content = '<advancedsettings version="1.0">\n%s</advancedsettings>\n' % NETWORK_BLOCK
    else:
        with open(path, encoding='utf-8', errors='replace') as handle:
            content = handle.read()
        if '<network>' in content or '</advancedsettings>' not in content:
            return False
        content = content.replace('</advancedsettings>', NETWORK_BLOCK + '</advancedsettings>', 1)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(content)
    return True


def apply():
    """Returns (memory MB, read factor x, network settings written) or None if Kodi refused."""
    wanted = recommended_memory()
    memory = next((m for m in (256, 192, 128, 96, 64) if m <= wanted and set_setting('filecache.memorysize', m)), None)
    if memory is None:
        return None
    factor = next((f for f in READ_FACTORS if set_setting('filecache.readfactor', f)), 400)
    if get_setting('filecache.buffermode') == 3:  # "no buffer"
        set_setting('filecache.buffermode', 4)
    network = write_network_settings()
    log('playback tuning: cache %d MB, read factor %d, network %s' % (memory, factor, network), xbmc.LOGINFO)
    return memory, factor // 100, network
