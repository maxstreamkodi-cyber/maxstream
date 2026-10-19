# -*- coding: utf-8 -*-
"""Video info tags and parental control."""
import xbmcgui

from .common import DEFAULT_ADULT_KEYWORDS, L, get_bool, get_setting, home_prop, notify

def set_info(li, info):
    tag = li.getVideoInfoTag()
    if info.get('mediatype'):
        tag.setMediaType(info['mediatype'])
    if info.get('title'):
        tag.setTitle(info['title'])
    if info.get('plot'):
        tag.setPlot(info['plot'])
    if info.get('year'):
        tag.setYear(int(info['year']))
    if info.get('rating'):
        tag.setRating(float(info['rating']))
    if info.get('genre'):
        genre = info['genre']
        tag.setGenres(genre if isinstance(genre, list) else [g.strip() for g in genre.split(',') if g.strip()])
    if info.get('director'):
        tag.setDirectors([d.strip() for d in info['director'].split(',') if d.strip()])
    if info.get('duration'):
        tag.setDuration(int(info['duration']))
    if info.get('season') is not None and info.get('mediatype') in ('episode', 'season'):
        tag.setSeason(int(info['season']))
    if info.get('episode') is not None and info.get('mediatype') == 'episode':
        tag.setEpisode(int(info['episode']))
    if info.get('tvshowtitle'):
        tag.setTvShowTitle(info['tvshowtitle'])
    if info.get('playcount'):
        tag.setPlaycount(int(info['playcount']))
    if info.get('resume'):
        pos, total = info['resume']
        tag.setResumePoint(float(pos), float(total))
    if info.get('dateadded'):
        tag.setDateAdded(info['dateadded'])


# ---------------------------------------------------------------- parental control
def parental_enabled():
    return get_bool('parental_enabled', False)


def adult_keywords():
    raw = get_setting('parental_keywords', DEFAULT_ADULT_KEYWORDS)
    return [k.strip().lower() for k in raw.split(',') if k.strip()]


def is_adult(name):
    if not parental_enabled():
        return False
    lower = (name or '').lower()
    return any(k in lower for k in adult_keywords())


def is_unlocked():
    return home_prop('unlocked') == '1'


def hide_locked():
    return parental_enabled() and get_bool('parental_hide', False) and not is_unlocked()


def unlock(name):
    """Ask for the PIN if `name` is an adult category. True when allowed."""
    if not is_adult(name) or is_unlocked():
        return True
    pin = xbmcgui.Dialog().numeric(0, L(30048), '', True)
    if not pin:
        return False
    if pin == get_setting('parental_pin', '0000'):
        home_prop('unlocked', '1')
        return True
    notify(L(30049))
    return False
