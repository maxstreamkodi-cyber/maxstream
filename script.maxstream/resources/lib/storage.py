# -*- coding: utf-8 -*-
"""Persistent data: playlists (accounts), favourites, history, resume points,
hidden categories, recent searches and a small TTL cache."""
import os
import re
import shutil
import time
import uuid

from .common import PROFILE, ensure_dir, get_int, read_json, write_json

PLAYLISTS_FILE = os.path.join(PROFILE, 'playlists.json')
CACHE_ROOT = os.path.join(PROFILE, 'cache')
DATA_ROOT = os.path.join(PROFILE, 'data')
PENDING_FILE = os.path.join(PROFILE, 'pending_playback.json')


# ---------------------------------------------------------------- playlists
def _load():
    data = read_json(PLAYLISTS_FILE, None) or {}
    data.setdefault('active', None)
    data.setdefault('items', [])
    return data


def playlists():
    return _load()['items']


def active_playlist():
    data = _load()
    for item in data['items']:
        if item['id'] == data['active']:
            return item
    return data['items'][0] if data['items'] else None


def get_playlist(pid):
    for item in playlists():
        if item['id'] == pid:
            return item
    return None


def new_id():
    return uuid.uuid4().hex[:10]


def add_playlist(playlist):
    data = _load()
    playlist.setdefault('id', new_id())
    playlist['created'] = int(time.time())
    data['items'].append(playlist)
    data['active'] = playlist['id']
    write_json(PLAYLISTS_FILE, data)
    return playlist


def update_playlist(playlist):
    data = _load()
    data['items'] = [playlist if p['id'] == playlist['id'] else p for p in data['items']]
    write_json(PLAYLISTS_FILE, data)


def delete_playlist(pid):
    data = _load()
    data['items'] = [p for p in data['items'] if p['id'] != pid]
    if data['active'] == pid:
        data['active'] = data['items'][0]['id'] if data['items'] else None
    write_json(PLAYLISTS_FILE, data)
    for root in (CACHE_ROOT, DATA_ROOT):
        shutil.rmtree(os.path.join(root, pid), ignore_errors=True)


def set_active(pid):
    data = _load()
    data['active'] = pid
    write_json(PLAYLISTS_FILE, data)


# ---------------------------------------------------------------- cache
class Cache(object):
    def __init__(self, pid):
        self.dir = ensure_dir(os.path.join(CACHE_ROOT, pid))

    def path(self, key):
        return os.path.join(self.dir, re.sub(r'[^\w\-.]', '_', key) + '.json')

    def get(self, key, ttl):
        path = self.path(key)
        try:
            if ttl is not None and time.time() - os.path.getmtime(path) > ttl:
                return None
        except OSError:
            return None
        return read_json(path, None)

    def set(self, key, data):
        write_json(self.path(key), data)

    def clear(self, keep=('epg.db',)):
        for name in os.listdir(self.dir):
            if name in keep:
                continue
            try:
                os.remove(os.path.join(self.dir, name))
            except OSError:
                pass


def clear_all_cache():
    shutil.rmtree(CACHE_ROOT, ignore_errors=True)


# ---------------------------------------------------------------- per-playlist data
def _data_path(pid, name):
    return os.path.join(DATA_ROOT, pid, name + '.json')


def item_key(kind, item_id):
    return '%s:%s' % (kind, item_id)


class ItemList(object):
    """Ordered list of {'kind', 'item', 'ts'} (favourites, history)."""

    def __init__(self, pid, name, limit=None):
        self.path = _data_path(pid, name)
        self.limit = limit
        self.entries = read_json(self.path, []) or []

    def save(self):
        write_json(self.path, self.entries)

    def all(self, kind=None):
        return [e for e in self.entries if kind is None or e['kind'] == kind]

    def keys(self):
        return set(item_key(e['kind'], e['item']['id']) for e in self.entries)

    def contains(self, kind, item_id):
        return item_key(kind, item_id) in self.keys()

    def add(self, kind, item, front=True):
        self.remove(kind, item['id'], save=False)
        entry = {'kind': kind, 'item': item, 'ts': int(time.time())}
        if front:
            self.entries.insert(0, entry)
        else:
            self.entries.append(entry)
        if self.limit:
            self.entries = self.entries[:self.limit]
        self.save()

    def remove(self, kind, item_id, save=True):
        key = item_key(kind, item_id)
        self.entries = [e for e in self.entries if item_key(e['kind'], e['item']['id']) != key]
        if save:
            self.save()

    def clear(self):
        self.entries = []
        self.save()


def favourites(pid):
    return ItemList(pid, 'favourites')


def history(pid):
    return ItemList(pid, 'history', limit=max(10, get_int('history_size', 50)))


class Resume(object):
    """key -> {'pos', 'total', 'ts', 'watched'}"""

    def __init__(self, pid):
        self.path = _data_path(pid, 'resume')
        self.data = read_json(self.path, {}) or {}

    def get(self, key):
        return self.data.get(key)

    def update(self, key, pos, total):
        if total <= 0:
            return
        if pos >= total * 0.92:
            self.data[key] = {'pos': 0, 'total': total, 'ts': int(time.time()), 'watched': True}
        elif pos > 30:
            self.data[key] = {'pos': int(pos), 'total': int(total), 'ts': int(time.time()),
                              'watched': self.data.get(key, {}).get('watched', False)}
        write_json(self.path, self.data)


class KeyValue(object):
    def __init__(self, pid, name, default):
        self.path = _data_path(pid, name)
        self.data = read_json(self.path, None)
        if self.data is None:
            self.data = default

    def save(self):
        write_json(self.path, self.data)


def hidden_categories(pid):
    store = KeyValue(pid, 'hidden', {'live': [], 'movie': [], 'series': []})
    for kind in ('live', 'movie', 'series'):
        store.data.setdefault(kind, [])
    return store


def recent_searches(pid):
    return KeyValue(pid, 'searches', [])
