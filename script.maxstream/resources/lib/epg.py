# -*- coding: utf-8 -*-
"""XMLTV EPG: download, parse (streaming, gzip aware) and store in SQLite."""
import calendar
import gzip
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET

from . import net
from .common import ensure_dir, get_int, log, log_error, replace_file
from .storage import CACHE_ROOT

TIME_RE = re.compile(r'^(\d{14})\s*([+-]\d{4})?')


def parse_xmltv_time(value):
    match = TIME_RE.match((value or '').strip())
    if not match:
        return None
    ts = calendar.timegm(time.strptime(match.group(1), '%Y%m%d%H%M%S'))
    tz = match.group(2)
    if tz:
        sign = -1 if tz[0] == '-' else 1
        ts -= sign * (int(tz[1:3]) * 3600 + int(tz[3:5]) * 60)
    return ts


def norm(value):
    return (value or '').strip().lower()


class EPGStore(object):
    def __init__(self, pid):
        self.dir = ensure_dir(os.path.join(CACHE_ROOT, pid))
        self.path = os.path.join(self.dir, 'epg.db')
        self._conn = None
        self._names = None

    # ------------------------------------------------------------ state
    def exists(self):
        return os.path.exists(self.path)

    def age(self):
        try:
            return time.time() - os.path.getmtime(self.path)
        except OSError:
            return None

    def is_stale(self):
        age = self.age()
        return age is None or age > max(1, get_int('epg_refresh_hours', 12)) * 3600

    def conn(self):
        if self._conn is None and self.exists():
            self._conn = sqlite3.connect(self.path, timeout=10)
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------ update
    def update(self, urls, progress=None, keep_first=None):
        """Download and parse every url. progress(percent, message) -> False aborts."""
        tmp_db = self.path + '.new'
        if os.path.exists(tmp_db):
            os.remove(tmp_db)
        db = sqlite3.connect(tmp_db)
        db.execute('CREATE TABLE channels (id TEXT, name TEXT)')
        db.execute('CREATE TABLE prog (channel TEXT, start INTEGER, stop INTEGER, title TEXT, descr TEXT)')
        now = time.time()
        tmin = now - max(1, get_int('epg_days_past', 7)) * 86400
        tmax = now + max(1, get_int('epg_days_future', 2)) * 86400
        count = 0
        kept = False
        try:
            for idx, url in enumerate(urls):
                raw = os.path.join(self.dir, 'epg_download.tmp')

                def _dl(done, total, _idx=idx):
                    if progress:
                        pct = int(done * 100 / total) if total else min(95, done // (1024 * 1024))
                        return progress(pct, 'download %d/%d - %.1f MB' % (_idx + 1, len(urls), done / 1048576.0))
                    return True
                try:
                    net.download(url, raw, _dl)
                except net.NetError as err:
                    log_error('EPG download failed %s: %s' % (url, err))
                    continue
                if progress and progress(100, 'parsing...') is False:
                    raise net.NetError('cancelled')
                parsed = self._parse(raw, db, tmin, tmax)
                count += parsed
                if keep_first and parsed and not kept:
                    ensure_dir(os.path.dirname(keep_first))
                    replace_file(raw, keep_first)
                    kept = True
                    continue
                try:
                    os.remove(raw)
                except OSError:
                    pass
            db.execute('CREATE INDEX idx_prog ON prog(channel, start)')
            db.execute('CREATE INDEX idx_chan_name ON channels(name)')
            db.commit()
        finally:
            db.close()
        if count == 0:
            os.remove(tmp_db)
            return 0
        self.close()
        replace_file(tmp_db, self.path)
        return count

    @staticmethod
    def _parse(path, db, tmin, tmax):
        with open(path, 'rb') as probe:
            magic = probe.read(2)
        opener = gzip.open if magic == b'\x1f\x8b' else open
        channels = set()
        batch = []
        try:
            with opener(path, 'rb') as handle:
                context = ET.iterparse(handle, events=('start', 'end'))
                root = None
                for event, elem in context:
                    if root is None and event == 'start':
                        root = elem
                        continue
                    if event != 'end':
                        continue
                    if elem.tag == 'channel':
                        cid = norm(elem.get('id'))
                        if cid:
                            channels.add(cid)
                            db.execute('INSERT INTO channels VALUES (?, ?)', (cid, cid))
                            for name in elem.findall('display-name'):
                                if name.text:
                                    db.execute('INSERT INTO channels VALUES (?, ?)', (cid, norm(name.text)))
                        root.clear()
                    elif elem.tag == 'programme':
                        start = parse_xmltv_time(elem.get('start'))
                        stop = parse_xmltv_time(elem.get('stop')) or (start or 0) + 1800
                        if start and stop > tmin and start < tmax:
                            batch.append((norm(elem.get('channel')), start, stop,
                                          (elem.findtext('title') or '').strip(),
                                          (elem.findtext('desc') or '').strip()))
                            if len(batch) >= 5000:
                                db.executemany('INSERT INTO prog VALUES (?, ?, ?, ?, ?)', batch)
                                batch = []
                        root.clear()
        except (ET.ParseError, OSError, EOFError) as err:
            log_error('EPG parse error (keeping what was read): %s' % err)
        if batch:
            db.executemany('INSERT INTO prog VALUES (?, ?, ?, ?, ?)', batch)
        log('EPG: %d channels parsed' % len(channels))
        return len(channels)

    # ------------------------------------------------------------ queries
    def resolve(self, epg_id, name=''):
        """Map a playlist channel (tvg-id / name) to an XMLTV channel id."""
        if self._names is None:
            self._names = {}
            conn = self.conn()
            if conn is not None:
                for cid, cname in conn.execute('SELECT id, name FROM channels'):
                    self._names.setdefault(cname, cid)
        for candidate in (norm(epg_id), norm(name)):
            if candidate and candidate in self._names:
                return self._names[candidate]
        return None

    def now_next(self, channel_ids, limit=2):
        """{channel_id: [current, next, ...]} for many channels at once."""
        conn = self.conn()
        result = {}
        ids = [c for c in set(channel_ids) if c]
        if conn is None or not ids:
            return result
        now = int(time.time())
        for i in range(0, len(ids), 400):
            chunk = ids[i:i + 400]
            sql = ('SELECT channel, start, stop, title, descr FROM prog WHERE stop > ? AND start < ? '
                   'AND channel IN (%s) ORDER BY channel, start' % ','.join('?' * len(chunk)))
            for row in conn.execute(sql, [now, now + 86400] + chunk):
                lst = result.setdefault(row[0], [])
                if len(lst) < limit:
                    lst.append({'start': row[1], 'stop': row[2], 'title': row[3], 'desc': row[4]})
        return result

    def programmes(self, channel_id, start=None, end=None):
        conn = self.conn()
        if conn is None or not channel_id:
            return []
        start = start or 0
        end = end or 4102444800
        rows = conn.execute('SELECT start, stop, title, descr FROM prog WHERE channel = ? AND stop > ? '
                            'AND start < ? ORDER BY start', (channel_id, start, end))
        return [{'start': r[0], 'stop': r[1], 'title': r[2], 'desc': r[3]} for r in rows]

    def stats(self):
        conn = self.conn()
        if conn is None:
            return 0, 0
        chans = conn.execute('SELECT COUNT(DISTINCT id) FROM channels').fetchone()[0]
        progs = conn.execute('SELECT COUNT(*) FROM prog').fetchone()[0]
        return chans, progs
