# -*- coding: utf-8 -*-
"""M3U / M3U Plus parser and content classifier."""
import re
from urllib.parse import quote

ATTR_RE = re.compile(r'([\w\-]+)\s*=\s*"([^"]*)"')
SERIES_RE = re.compile(r'^(.*?)[\s._\-|:]*\b[Ss](\d{1,2})[\s._\-]*[Ee](\d{1,4})\b(.*)$')
VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg', '.webm', '.divx')


def _split_extinf(line):
    """Return (attribute_part, title) splitting on first comma outside quotes."""
    body = line[len('#EXTINF:'):]
    in_quote = False
    for idx, char in enumerate(body):
        if char == '"':
            in_quote = not in_quote
        elif char == ',' and not in_quote:
            return body[:idx], body[idx + 1:].strip()
    return body, ''


def parse(text):
    """Parse M3U text -> (header_attrs, entries)."""
    header = {}
    entries = []
    current = None
    group_hint = ''
    opts = {}
    props = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#EXTM3U'):
            header.update({k.lower(): v for k, v in ATTR_RE.findall(line)})
        elif line.startswith('#EXTINF:'):
            attr_part, title = _split_extinf(line)
            attrs = {k.lower(): v for k, v in ATTR_RE.findall(attr_part)}
            current = {'name': title or attrs.get('tvg-name') or '', 'attrs': attrs}
        elif line.startswith('#EXTGRP:'):
            group_hint = line[8:].strip()
        elif line.startswith('#EXTVLCOPT:'):
            key, _, value = line[11:].partition('=')
            opts[key.strip().lower()] = value.strip()
        elif line.startswith('#KODIPROP:'):
            key, _, value = line[10:].partition('=')
            props.append([key.strip(), value.strip()])
        elif line.startswith('#'):
            continue
        else:
            if current is None:
                current = {'name': line.rsplit('/', 1)[-1], 'attrs': {}}
            attrs = current['attrs']
            current['group'] = attrs.get('group-title') or group_hint or ''
            current['url'] = _with_headers(line, opts, attrs)
            current['props'] = props
            entries.append(current)
            current, group_hint, opts, props = None, '', {}, []
    return header, entries


def _with_headers(url, opts, attrs):
    headers = []
    ua = opts.get('http-user-agent') or attrs.get('user-agent') or attrs.get('http-user-agent')
    ref = opts.get('http-referrer') or opts.get('http-referer') or attrs.get('referer')
    if ua:
        headers.append('User-Agent=' + quote(ua))
    if ref:
        headers.append('Referer=' + quote(ref))
    if not headers:
        return url
    return url + ('&' if '|' in url else '|') + '&'.join(headers)


def classify(entry):
    """'live', 'movie' or 'series'."""
    path = entry['url'].split('|')[0].split('?')[0].lower()
    if '/series/' in path:
        return 'series'
    if '/movie/' in path or '/movies/' in path:
        return 'movie'
    if path.endswith(VIDEO_EXTS):
        return 'series' if SERIES_RE.match(entry['name']) else 'movie'
    return 'live'


def split_episode(name):
    """'Show S01 E02 Title' -> ('Show', 1, 2) or None."""
    match = SERIES_RE.match(name or '')
    if not match:
        return None
    show = match.group(1).strip(' -_.|:') or name
    return show, int(match.group(2)), int(match.group(3))
