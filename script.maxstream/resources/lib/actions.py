# -*- coding: utf-8 -*-
"""Dialog-based actions shared by the interface and the settings buttons:
playlists, account, TV guide update, cache, hidden categories, parental lock,
Kodi TV synchronisation."""
import os

import xbmc
import xbmcgui

from . import net, pvr, storage, tuning
from .common import (ADDON_NAME, ADDON_VERSION, L, accent, get_bool, grey, has_addon, home_prop, log_error,
                     notify, open_settings, set_setting)
from .provider import get_provider, parse_xtream_link

KIND_LABEL = {'live': 30000, 'movie': 30001, 'series': 30002, 'episode': 30080}
TYPE_LABEL = {'xtream': 30030, 'm3u': 30031, 'm3u_file': 30032}


def active():
    playlist = storage.active_playlist()
    return (playlist, get_provider(playlist)) if playlist else (None, None)


# ---------------------------------------------------------------- playlists
def _ask_xtream(pl):
    dialog = xbmcgui.Dialog()
    server = dialog.input(L(30034), defaultt=pl.get('server') or 'http://').strip()
    if not server or server == 'http://':
        return None
    user = dialog.input(L(30035), defaultt=pl.get('username', '')).strip()
    if not user:
        return None
    pwd = dialog.input(L(30036), defaultt=pl.get('password', ''), option=xbmcgui.ALPHANUM_HIDE_INPUT).strip()
    if not pwd:
        return None
    creds = parse_xtream_link(server)
    if creds:
        server = creds[0]
    pl.update({'type': 'xtream', 'server': server, 'username': user, 'password': pwd})
    return pl


def validate(pl):
    """Download the catalogue once, with a progress dialog. Returns error text or None."""
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, L(30039))
    try:
        prov = get_provider(pl)
        prov.refresh()
        prov.check()
        progress.update(40, L(30082))
        for pct, kind in ((55, 'live'), (75, 'movie'), (90, 'series')):
            prov.categories(kind)
            prov.all_items(kind)
            progress.update(pct, L(30082))
            if progress.iscanceled():
                return L(30093)
        return None
    except net.NetError as err:
        return str(err)
    except Exception as err:  # pylint: disable=broad-except
        log_error('validation error: %r' % err)
        return str(err)
    finally:
        progress.close()


def playlist_add(_params=None):
    dialog = xbmcgui.Dialog()
    choice = dialog.select(L(30029), [L(30030), L(30031), L(30032)])
    if choice < 0:
        return False
    pl = {'id': storage.new_id()}
    if choice == 0:
        if _ask_xtream(pl) is None:
            return False
        default_name = pl['server'].split('://', 1)[-1].split('/')[0].split(':')[0]
    elif choice == 1:
        url = dialog.input(L(30037)).strip()
        if not url:
            return False
        creds = parse_xtream_link(url)
        if creds and dialog.yesno(ADDON_NAME, L(30064)):
            pl.update({'type': 'xtream', 'server': creds[0], 'username': creds[1], 'password': creds[2]})
        else:
            pl.update({'type': 'm3u', 'm3u_url': url, 'epg_url': dialog.input(L(30038)).strip()})
        default_name = url.split('://', 1)[-1].split('/')[0].split(':')[0]
    else:
        path = dialog.browse(1, L(30032), 'files', '.m3u|.m3u8|.txt')
        if not path:
            return False
        pl.update({'type': 'm3u_file', 'm3u_path': path, 'epg_url': dialog.input(L(30038)).strip()})
        default_name = os.path.splitext(os.path.basename(path.rstrip('/\\')))[0]
    pl['name'] = dialog.input(L(30033), defaultt=default_name).strip() or default_name
    error = validate(pl)
    if error:
        storage.Cache(pl['id']).clear(keep=())
        dialog.ok(ADDON_NAME, L(30041) % error)
        return False
    storage.add_playlist(pl)
    home_prop('epg_kick', '1')
    notify(L(30040))
    return True


def playlist_edit(pid):
    pl = storage.get_playlist(pid)
    if not pl:
        return False
    dialog = xbmcgui.Dialog()
    changed = False
    while True:
        if pl.get('type') == 'xtream':
            fields = [('name', 30033), ('server', 30034), ('username', 30035), ('password', 30036)]
        elif pl.get('type') == 'm3u':
            fields = [('name', 30033), ('m3u_url', 30037), ('epg_url', 30038)]
        else:
            fields = [('name', 30033), ('m3u_path', 30032), ('epg_url', 30038)]
        labels = []
        for field, label_id in fields:
            value = pl.get(field, '')
            if field == 'password':
                value = '*' * len(value)
            labels.append('%s: %s' % (L(label_id), grey(value)))
        idx = dialog.select('%s - %s' % (L(30043), pl['name']), labels)
        if idx < 0:
            break
        field = fields[idx][0]
        if field == 'm3u_path':
            value = dialog.browse(1, L(30032), 'files', '.m3u|.m3u8|.txt', defaultt=pl.get(field, ''))
        else:
            option = xbmcgui.ALPHANUM_HIDE_INPUT if field == 'password' else 0
            value = dialog.input(L(fields[idx][1]), defaultt=pl.get(field, ''), option=option).strip()
        if value or field == 'epg_url':
            pl[field] = value
            changed = True
    if changed:
        storage.update_playlist(pl)
        get_provider(pl).refresh()
        home_prop('epg_kick', '1')
        notify(L(30076))
    return changed


def playlist_delete(pid):
    pl = storage.get_playlist(pid)
    if pl and xbmcgui.Dialog().yesno(ADDON_NAME, L(30045) % pl['name']):
        storage.delete_playlist(pl['id'])
        return True
    return False


def playlist_refresh(pid=None):
    pl = storage.get_playlist(pid) if pid else storage.active_playlist()
    if not pl:
        return False
    error = validate(pl)
    if error:
        notify(L(30041) % error)
        return False
    home_prop('epg_kick', '1')
    notify(L(30076))
    return True


def playlist_select(pid):
    storage.set_active(pid)
    home_prop('epg_kick', '1')
    notify('%s: %s' % (L(30046), storage.active_playlist()['name']))
    return True


def playlists_menu(_params=None):
    """Pick / manage playlists. Returns True when something changed."""
    current = storage.active_playlist()
    items = storage.playlists()
    labels = []
    for pl in items:
        label = '%s  %s' % (pl['name'], grey(L(TYPE_LABEL.get(pl.get('type'), 30031))))
        if current and pl['id'] == current['id']:
            label = '[B]%s[/B]  %s' % (label, accent(L(30046)))
        labels.append(label)
    labels.append(accent('+ ' + L(30010)))
    idx = xbmcgui.Dialog().select(L(30008), labels)
    if idx < 0:
        return False
    if idx == len(items):
        return playlist_add()
    pl = items[idx]
    choice = xbmcgui.Dialog().contextmenu([L(30042), L(30043), L(30013), L(30044)])
    if choice == 0:
        return playlist_select(pl['id'])
    if choice == 1:
        return playlist_edit(pl['id'])
    if choice == 2:
        return playlist_refresh(pl['id'])
    if choice == 3:
        return playlist_delete(pl['id'])
    return False


# ---------------------------------------------------------------- account & maintenance
def account(_params=None):
    playlist, prov = active()
    if not playlist:
        return
    lines = ['[B]%s[/B]  %s' % (L(30033), playlist.get('name', ''))]
    try:
        info = prov.account_lines()
    except net.NetError as err:
        info = None
        lines.append(L(30041) % err)
    if info:
        status = info['status']
        lines += [
            '[B]%s[/B]  %s' % (L(30035), info['username']),
            '[B]%s[/B]  %s' % (L(30050), accent(status) if status == 'Active' else status),
            '[B]%s[/B]  %s' % (L(30051), info['exp'] or L(30052)),
            '[B]%s[/B]  %s' % (L(30055), L(30091) if info['trial'] else L(30092)),
            '[B]%s[/B]  %s / %s' % (L(30053), info['active'], info['max']),
            '[B]%s[/B]  %s' % (L(30056), info['created']),
            '[B]%s[/B]  %s' % (L(30057), info['timezone']),
            '[B]%s[/B]  %s' % (L(30034), info['server']),
        ]
    else:
        lines.append('[B]M3U[/B]  %s' % (playlist.get('m3u_url') or playlist.get('m3u_path') or ''))
    try:
        lines += ['', '[B]%s[/B]  %d   [B]%s[/B]  %d   [B]%s[/B]  %d' % (
            L(30000), len(prov.all_items('live')), L(30001), len(prov.all_items('movie')),
            L(30002), len(prov.all_items('series')))]
    except net.NetError:
        pass
    chans, progs = prov.epg.stats()
    age = prov.epg.age()
    lines.append('[B]EPG[/B]  %d / %d  %s' % (chans, progs, ('(%dh)' % (age // 3600)) if age is not None else ''))
    lines += ['', grey('%s %s' % (ADDON_NAME, ADDON_VERSION))]
    xbmcgui.Dialog().textviewer(L(30007), '\n'.join(lines))


def epg_update(_params=None):
    playlist, prov = active()
    if not playlist:
        return False
    try:
        urls = prov.epg_urls()
    except net.NetError as err:
        notify(L(30041) % err)
        return False
    if not urls:
        notify(L(30090))
        return False
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, L(30063))

    def update(pct, message):
        progress.update(max(0, min(100, pct)), '%s\n%s' % (L(30063), message))
        return not progress.iscanceled()
    try:
        count = prov.epg.update(urls, update, keep_first=pvr.EPG_PATH if pvr.enabled() else None)
    except net.NetError as err:
        count = -1
        notify(L(30041) % err)
    finally:
        progress.close()
    if count > 0:
        notify(L(30061) % count)
        return True
    if count == 0:
        notify(L(30090))
    return False


def clear_cache(_params=None):
    storage.clear_all_cache()
    notify(L(30060))


def hide_category(kind, cat_id, name):
    playlist = storage.active_playlist()
    store = storage.hidden_categories(playlist['id'])
    if cat_id not in [e[0] for e in store.data[kind]]:
        store.data[kind].append([cat_id, name])
        store.save()
    notify(L(30067))


def manage_hidden(_params=None):
    playlist = storage.active_playlist()
    if not playlist:
        return False
    store = storage.hidden_categories(playlist['id'])
    rows = []
    for kind in ('live', 'movie', 'series'):
        for cat_id, name in store.data[kind]:
            rows.append((kind, cat_id, '%s: %s' % (L(KIND_LABEL[kind]), name)))
    if not rows:
        xbmcgui.Dialog().ok(ADDON_NAME, L(30066))
        return False
    selected = xbmcgui.Dialog().multiselect(L(30065), [r[2] for r in rows])
    if not selected:
        return False
    for idx in selected:
        kind, cat_id, _label = rows[idx]
        store.data[kind] = [e for e in store.data[kind] if e[0] != cat_id]
    store.save()
    return True


def lock(_params=None):
    home_prop('unlocked', '')
    notify(L(30078))


# ---------------------------------------------------------------- Kodi TV menu
def pvr_sync(_params=None):
    """Export channels + guide and register them in PVR IPTV Simple Client."""
    playlist, prov = active()
    if not playlist:
        return False
    dialog = xbmcgui.Dialog()
    if not has_addon(pvr.PVR_ADDON):
        if not dialog.yesno(ADDON_NAME, L(30604)):
            return False
        xbmc.executebuiltin('InstallAddon(%s)' % pvr.PVR_ADDON, True)
        if not has_addon(pvr.PVR_ADDON):
            dialog.ok(ADDON_NAME, L(30605))
            return False
    set_setting('pvr_sync', 'true')
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, L(30606))
    try:
        count = pvr.export_m3u(playlist, prov)
        urls = prov.epg_urls() if get_bool('epg_enabled', True) else []
        if urls:
            progress.update(30, L(30063))
            prov.epg.update(urls, lambda pct, msg: progress.update(30 + int(pct * 0.6), L(30063)) or True,
                            keep_first=pvr.EPG_PATH)
        progress.update(95, L(30606))
        pvr.write_instance()
        pvr.restart_pvr_addon()
    except net.NetError as err:
        progress.close()
        notify(L(30041) % err)
        return False
    finally:
        progress.close()
    dialog.ok(ADDON_NAME, L(30607) % count)
    return True


def optimise_playback(_params=None):
    result = tuning.apply()
    if result is None:
        xbmcgui.Dialog().ok(ADDON_NAME, L(30623))
        return False
    memory, factor, _network = result
    xbmcgui.Dialog().ok(ADDON_NAME, L(30622) % (memory, factor))
    return True


def offer_playback_tuning():
    """Asked once, the first time the interface opens with Kodi's default 20 MB buffer."""
    if tuning.already_asked() or not tuning.needs_tuning():
        return
    tuning.mark_asked()
    if xbmcgui.Dialog().yesno(ADDON_NAME, L(30620)):
        optimise_playback()


def donate(_params=None):
    from .gui.donate import show_donate
    show_donate()


def settings_menu():
    """Gear button of the home screen. Returns True when the catalogue may have changed."""
    entries = [(30009, open_settings), (30621, optimise_playback), (30603, pvr_sync), (30014, epg_update),
               (30122, manage_hidden), (30126, clear_cache), (30630, donate)]
    idx = xbmcgui.Dialog().contextmenu([L(e[0]) for e in entries])
    if idx < 0:
        return False
    result = entries[idx][1]()
    return bool(result) or entries[idx][0] in (30009, 30122, 30126)


ACTIONS = {
    'playlist_add': playlist_add, 'playlists': playlists_menu, 'manage_hidden': manage_hidden,
    'clear_cache': clear_cache, 'epg_update': epg_update, 'lock': lock, 'pvr_sync': pvr_sync,
    'account': account, 'optimise_playback': optimise_playback, 'donate': donate,
}
