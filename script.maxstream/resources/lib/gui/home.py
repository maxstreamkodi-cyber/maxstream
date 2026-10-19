# -*- coding: utf-8 -*-
"""Home dashboard: Live TV / Movies / Series tiles, shortcuts and Continue watching."""
import threading

import xbmcgui

from .. import actions, net, playback
from ..common import L, home_prop, log_error
from .base import BACK_ACTIONS, SESSION, continue_entries, continue_item, create, fill
from .live import LiveWindow
from .vod import VodWindow

TILE_LIVE, TILE_MOVIES, TILE_SERIES, SETTINGS, DONATE = 101, 102, 103, 110, 111
SC_REPLAY, SC_GUIDE, SC_FAV, SC_SEARCH, SC_LISTS, SC_ACCOUNT = 201, 202, 203, 204, 205, 206
CONTINUE = 600


def fmt_count(value):
    return '{:,}'.format(value).replace(',', ' ')


class HomeWindow(xbmcgui.WindowXML):
    XML = 'script-maxstream-home.xml'

    def onInit(self):  # pylint: disable=invalid-name
        if not getattr(self, '_ready', False):
            self._ready = True
            if not SESSION.pl and not actions.playlist_add():
                self.close()
                return
            SESSION.reload()
            self.refresh_all()
            actions.offer_playback_tuning()
        else:
            self.refresh_continue()
            self.refresh_shortcuts()

    # ------------------------------------------------------------ data
    def refresh_all(self):
        self.setProperty('playlist', SESSION.pl['name'] if SESSION.pl else '')
        for key in ('live_sub', 'movie_sub', 'series_sub', 'expiry'):
            self.setProperty(key, '')
        self.refresh_shortcuts()
        self.refresh_continue()
        threading.Thread(target=self.load_counts).start()

    def load_counts(self):
        """Background: catalogue counts on the tiles and account expiry (may download)."""
        prov = SESSION.prov
        try:
            with SESSION.lock:
                live = prov.all_items('live')
                live_cats = len(prov.categories('live'))
            self.setProperty('live_sub', L(30500) % (fmt_count(len(live)), live_cats))
            self.setProperty('sc_201', L(30523) % fmt_count(len([c for c in live if c.get('catchup')])))
            with SESSION.lock:
                movies = len(prov.all_items('movie'))
            self.setProperty('movie_sub', L(30501) % fmt_count(movies))
            with SESSION.lock:
                series = len(prov.all_items('series'))
            self.setProperty('series_sub', L(30502) % fmt_count(series))
            info = prov.account_lines() if hasattr(prov, 'account_lines') else None
            if info:
                self.setProperty('expiry', L(30508) % info['exp'] if info.get('exp') else L(30052))
                self.setProperty('sc_206', info.get('status') or '')
        except net.NetError as err:
            log_error('home counts: %s' % err)
        except Exception as err:  # pylint: disable=broad-except
            log_error('home counts error: %r' % err)

    def refresh_shortcuts(self):
        favs = SESSION.favourites()
        self.setProperty('sc_202', L(30000))
        self.setProperty('sc_203', str(len(favs.entries)))
        self.setProperty('sc_204', L(30011))
        self.setProperty('sc_205', SESSION.pl['name'] if SESSION.pl else '')

    def refresh_continue(self):
        self.continue_entries = continue_entries(SESSION) if SESSION.pl else []
        fill(self.getControl(CONTINUE), [continue_item(e, s) for e, s in self.continue_entries])

    # ------------------------------------------------------------ navigation
    def open(self, cls, **attrs):
        win = create(cls, **attrs)
        win.doModal()
        del win

    def onAction(self, action):  # pylint: disable=invalid-name
        if action.getId() in BACK_ACTIONS:
            self.close()

    def onClick(self, control_id):  # pylint: disable=invalid-name
        if not SESSION.pl and control_id not in (SC_LISTS, SETTINGS, DONATE):
            if actions.playlist_add():
                SESSION.reload()
                self.refresh_all()
            return
        if control_id == DONATE:
            actions.donate()
        elif control_id == TILE_LIVE:
            self.open(LiveWindow)
        elif control_id in (TILE_MOVIES, TILE_SERIES):
            self.open(VodWindow, kind='movie' if control_id == TILE_MOVIES else 'series', mode='browse')
        elif control_id == SC_REPLAY:
            self.open(LiveWindow, catchup_mode=True)
        elif control_id == SC_GUIDE:
            self.open(LiveWindow, start_category='fav' if SESSION.favourites().all('live') else None)
        elif control_id == SC_FAV:
            self.open(VodWindow, mode='favourites')
        elif control_id == SC_SEARCH:
            query = xbmcgui.Dialog().input(L(30006)).strip()
            if query:
                self.open(VodWindow, mode='search', query=query)
        elif control_id == SC_LISTS:
            if actions.playlists_menu():
                SESSION.reload()
                if not SESSION.pl:
                    self.close()
                    return
                self.refresh_all()
        elif control_id == SC_ACCOUNT:
            actions.account()
        elif control_id == SETTINGS:
            if actions.settings_menu():
                SESSION.reload()
                self.refresh_all()
        elif control_id == CONTINUE:
            pos = self.getControl(CONTINUE).getSelectedPosition()
            if 0 <= pos < len(self.continue_entries):
                entry, _state = self.continue_entries[pos]
                li = SESSION.safe(playback.build, SESSION.pl, SESSION.prov, entry['kind'], entry['item'])
                if li is not None:
                    playback.start(li)


def open_home():
    if home_prop('gui_open') == '1':
        return
    home_prop('gui_open', '1')
    try:
        win = create(HomeWindow)
        win.doModal()
        del win
    finally:
        home_prop('gui_open', '')
