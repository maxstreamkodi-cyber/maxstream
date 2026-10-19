# -*- coding: utf-8 -*-
"""Poster grid: Movies, Series, Favourites and Search results.
Left: sections / categories. Right: posters. Top: sort buttons + search."""
import threading

import xbmcgui

from .. import actions, playback, storage, ui
from ..common import L, fold, get_int
from .base import (BACK_ACTIONS, CONTEXT_ACTIONS, MOVE_ACTIONS, SESSION, Busy, adult_filter, create, fill,
                   hidden_ids, poster_item)

BACK, SORT_RECENT, SORT_AZ, SORT_RATING, SEARCH, CATS, GRID = 90, 301, 302, 303, 304, 100, 200
SORT_KEYS = {SORT_RECENT: 'recent', SORT_AZ: 'az', SORT_RATING: 'rating'}
NEW_COUNT = 40


class VodWindow(xbmcgui.WindowXML):
    XML = 'script-maxstream-vod.xml'
    kind = 'movie'          # movie | series (browse mode)
    mode = 'browse'         # browse | favourites | search
    query = ''

    def onInit(self):  # pylint: disable=invalid-name
        if not getattr(self, '_ready', False):
            self._ready = True
            self._timer = None
            self.sections, self.items = [], []
            self.section_index = -1
            self.sort = {0: '', 1: 'az', 2: 'az', 3: 'recent'}.get(get_int('sort_order', 0), '')
            with Busy():
                self.build_sections()
            fill(self.getControl(CATS), self.section_items(), 0)
            self.select_section(0)
            self.setFocusId(GRID if self.items else CATS)
        else:
            pos = self.getControl(GRID).getSelectedPosition() if self.items else 0
            fill(self.getControl(CATS), self.section_items(), self.section_index)
            self.render(max(0, pos))

    # ------------------------------------------------------------ sections
    def build_sections(self):
        session = SESSION
        prov = session.prov
        sections = []
        if self.mode == 'favourites':
            self.setProperty('title', L(30004))
            favs = session.favourites()
            for kind, label in (('movie', 30001), ('series', 30002), ('live', 30000)):
                sections.append({'id': kind, 'name': L(label), 'kind': kind,
                                 'items': [e['item'] for e in favs.all(kind)]})
        elif self.mode == 'search':
            self.setProperty('title', L(30071) % self.query)
            for kind, label in (('movie', 30524), ('series', 30525), ('live', 30523)):
                found = adult_filter(prov, kind, session.safe(prov.search, kind, self.query) or [])
                sections.append({'id': kind, 'name': L(label) % len(found), 'kind': kind, 'items': found})
        else:
            kind = self.kind
            self.setProperty('title', L(30001 if kind == 'movie' else 30002))
            everything = session.safe(prov.all_items, kind) or []
            visible = adult_filter(prov, kind, everything)
            newest = sorted(visible, key=lambda i: i.get('added', 0), reverse=True)[:NEW_COUNT]
            self.new_ids = set(i['id'] for i in newest)
            sections.append({'id': 'all', 'name': L(30011), 'kind': kind, 'items': visible})
            favs = [e['item'] for e in session.favourites().all(kind)]
            sections.append({'id': 'fav', 'name': L(30004), 'kind': kind, 'items': favs})
            sections.append({'id': 'recent_added', 'name': L(30086), 'kind': kind, 'items': newest})
            hidden = hidden_ids(session, kind)
            by_cat = {}
            for item in everything:
                by_cat.setdefault(item.get('cat'), []).append(item)
            for cat in session.safe(prov.categories, kind) or []:
                items = by_cat.get(cat['id'])
                if not items or cat['id'] in hidden:
                    continue
                if ui.is_adult(cat['name']) and ui.hide_locked():
                    continue
                sections.append({'id': cat['id'], 'name': cat['name'], 'kind': kind, 'items': items, 'category': True})
        if not hasattr(self, 'new_ids'):
            self.new_ids = set()
        self.sections = sections

    def section_items(self):
        out = []
        for sec in self.sections:
            label = sec['name']
            if sec.get('category') and ui.is_adult(sec['name']) and not ui.is_unlocked():
                label = '%s  [%s]' % (label, L(30078))
            count = '' if self.mode == 'search' else str(len(sec['items']))
            out.append(xbmcgui.ListItem(label=label, label2=count, offscreen=True))
        return out

    def select_section(self, index, interactive=False):
        if index < 0 or index >= len(self.sections):
            return
        sec = self.sections[index]
        self.section_index = index
        if sec.get('category') and ui.is_adult(sec['name']) and not ui.is_unlocked():
            if not interactive or not ui.unlock(sec['name']):
                self.items = []
                self.render(0, empty=L(30527))
                return
            fill(self.getControl(CATS), self.section_items(), index)
        self.items = list(sec['items'])
        self.render(0)

    def schedule_section(self):
        if self._timer:
            self._timer.cancel()
        index = self.getControl(CATS).getSelectedPosition()
        if index == self.section_index:
            return
        self._timer = threading.Timer(0.35, self.select_section, [index])
        self._timer.start()

    # ------------------------------------------------------------ grid
    def sorted_items(self):
        items = self.items
        if self.sort == 'az':
            return sorted(items, key=lambda i: fold(i.get('name')))
        if self.sort == 'recent':
            return sorted(items, key=lambda i: i.get('added', 0), reverse=True)
        if self.sort == 'rating':
            return sorted(items, key=lambda i: i.get('rating', 0), reverse=True)
        return items

    def render(self, select=0, empty=None):
        self.view = self.sorted_items()
        sec = self.sections[self.section_index] if 0 <= self.section_index < len(self.sections) else None
        kind = sec['kind'] if sec else self.kind
        resume = SESSION.resume()
        lis = []
        for item in self.view:
            state = resume.get(storage.item_key(kind, item['id'])) if kind == 'movie' else None
            lis.append(poster_item(kind, item, state, item['id'] in self.new_ids and kind == self.kind))
        fill(self.getControl(GRID), lis, select)
        self.setProperty('sort', self.sort)
        if sec:
            self.setProperty('subtitle', '%s · %s' % (sec['name'], L(30501 if kind != 'series' else 30502) % len(self.view)))
        self.setProperty('empty_text', empty or ('' if lis else L(30062)))

    def current(self):
        pos = self.getControl(GRID).getSelectedPosition()
        if not getattr(self, 'view', None) or not 0 <= pos < len(self.view):
            return None, None
        return self.sections[self.section_index]['kind'], self.view[pos]

    def open_item(self):
        kind, item = self.current()
        if item is None:
            return
        if kind == 'live':
            li = SESSION.safe(playback.build, SESSION.pl, SESSION.prov, 'live', item)
            if li is not None:
                playback.start(li)
            return
        from .detail import DetailWindow
        siblings = [i for i in self.view if i.get('cat') == item.get('cat') and i['id'] != item['id']][:20]
        win = create(DetailWindow, kind=kind, item=item, siblings=siblings)
        win.doModal()
        del win

    def toggle_fav(self, kind, item):
        favs = SESSION.favourites()
        if favs.contains(kind, item['id']):
            favs.remove(kind, item['id'])
        else:
            favs.add(kind, playback.slim(item), front=False)
        if self.mode == 'favourites' or self.sections[self.section_index]['id'] == 'fav':
            self.sections[self.section_index]['items'] = [e['item'] for e in favs.all(kind)]
            self.select_section(self.section_index)

    def context_menu(self):
        kind, item = self.current()
        if item is None:
            return
        fav = SESSION.favourites().contains(kind, item['id'])
        idx = xbmcgui.Dialog().contextmenu([L(30017) if fav else L(30016)])
        if idx == 0:
            self.toggle_fav(kind, item)

    def category_menu(self):
        sec = self.sections[self.getControl(CATS).getSelectedPosition()]
        if not sec.get('category'):
            return
        if xbmcgui.Dialog().contextmenu([L(30018)]) == 0:
            actions.hide_category(sec['kind'], sec['id'], sec['name'])
            self.sections.remove(sec)
            fill(self.getControl(CATS), self.section_items(), 0)
            self.select_section(0)

    def search(self):
        query = xbmcgui.Dialog().input(L(30006)).strip()
        if not query:
            return
        win = create(VodWindow, mode='search', query=query)
        win.doModal()
        del win

    # ------------------------------------------------------------ events
    def onAction(self, action):  # pylint: disable=invalid-name
        action_id = action.getId()
        focus = self.getFocusId()
        if action_id in BACK_ACTIONS:
            if self._timer:
                self._timer.cancel()
            self.close()
        elif action_id in CONTEXT_ACTIONS:
            if focus == GRID:
                self.context_menu()
            elif focus == CATS:
                self.category_menu()
        elif action_id in MOVE_ACTIONS and focus == CATS:
            self.schedule_section()

    def onClick(self, control_id):  # pylint: disable=invalid-name
        if control_id == BACK:
            self.close()
        elif control_id == CATS:
            if self._timer:
                self._timer.cancel()
            index = self.getControl(CATS).getSelectedPosition()
            if index != self.section_index or not self.items:
                self.select_section(index, interactive=True)
            if self.items:
                self.setFocusId(GRID)
        elif control_id == GRID:
            self.open_item()
        elif control_id in SORT_KEYS:
            key = SORT_KEYS[control_id]
            self.sort = '' if self.sort == key else key
            self.render(0)
        elif control_id == SEARCH:
            self.search()
