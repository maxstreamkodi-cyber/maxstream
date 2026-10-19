# -*- coding: utf-8 -*-
"""TV guide / catch-up dialog for one channel: days on the left, programmes on the right."""
import time

import xbmcgui

from .. import playback
from ..common import L, epg_offset, fmt_day, fmt_time, notify
from .base import BACK_ACTIONS, MOVE_ACTIONS, SESSION, fill

DAYS, PROGS = 100, 200


def day_key(ts):
    return time.strftime('%Y-%m-%d', time.localtime(ts + epg_offset()))


def channel_programmes(prov, channel):
    key = 'guide_%s' % channel['id']
    progs = prov.cache.get(key, 600)
    if progs is None:
        progs = prov.channel_programmes(channel)
        prov.cache.set(key, progs)
    return progs


class GuideDialog(xbmcgui.WindowXMLDialog):
    XML = 'script-maxstream-guide.xml'
    channel = None
    catchup = False

    def onInit(self):  # pylint: disable=invalid-name
        session = SESSION
        self.setProperty('title', self.channel.get('name', ''))
        self.setProperty('subtitle', L(30003) if self.catchup else L(30015))
        self.setProperty('logo', self.channel.get('icon') or '')
        progs = session.safe(channel_programmes, session.prov, self.channel) or []
        now = time.time()
        if self.catchup:
            progs = [p for p in progs if p['stop'] <= now and p.get('archive')]
        self.progs = progs
        days = []
        for prog in progs:
            key = day_key(prog['start'])
            if not days or days[-1][0] != key:
                days.append((key, prog['start']))
        if self.catchup:
            days.reverse()
        self.days = days
        if not days:
            notify(L(30069))
            self.close()
            return
        today = day_key(now)
        items = []
        start_index = 0
        for idx, (key, ts) in enumerate(days):
            label = L(30529) if key == today else fmt_day(ts)
            items.append(xbmcgui.ListItem(label=label, offscreen=True))
            if key == today:
                start_index = idx
        fill(self.getControl(DAYS), items, start_index)
        self.current_day = None
        self.show_day(start_index, focus_now=True)

    def show_day(self, index, focus_now=False):
        if index == self.current_day or index < 0 or index >= len(self.days):
            return
        self.current_day = index
        key = self.days[index][0]
        now = time.time()
        self.day_progs = [p for p in self.progs if day_key(p['start']) == key]
        if self.catchup:
            self.day_progs.reverse()
        items, select = [], 0
        for idx, prog in enumerate(self.day_progs):
            li = xbmcgui.ListItem(label=prog['title'], label2='%s - %s' % (fmt_time(prog['start']), fmt_time(prog['stop'])),
                                  offscreen=True)
            if prog['start'] <= now < prog['stop']:
                status = 'live'
                select = idx
            elif prog['stop'] <= now:
                status = 'replay' if prog.get('archive') else 'past'
            else:
                status = 'future'
            li.setProperty('status', status)
            li.setProperty('desc', prog.get('desc') or '')
            items.append(li)
        fill(self.getControl(PROGS), items, select if focus_now else 0)

    def onAction(self, action):  # pylint: disable=invalid-name
        if action.getId() in BACK_ACTIONS:
            self.close()
            return
        if action.getId() in MOVE_ACTIONS and self.getFocusId() == DAYS:
            self.show_day(self.getControl(DAYS).getSelectedPosition())

    def onClick(self, control_id):  # pylint: disable=invalid-name
        if control_id == DAYS:
            self.show_day(self.getControl(DAYS).getSelectedPosition())
            self.setFocusId(PROGS)
            return
        if control_id != PROGS:
            return
        pos = self.getControl(PROGS).getSelectedPosition()
        if pos < 0 or pos >= len(self.day_progs):
            return
        prog = self.day_progs[pos]
        now = time.time()
        session = SESSION
        if prog.get('archive') and prog['stop'] <= now:
            li = playback.build_catchup(session.pl, session.prov, self.channel, prog['start'], prog['stop'],
                                        prog.get('server_start', ''), prog['title'])
        elif prog['start'] <= now < prog['stop']:
            li = session.safe(playback.build, session.pl, session.prov, 'live', self.channel)
        else:
            return
        if li is not None:
            self.close()
            playback.start(li)
