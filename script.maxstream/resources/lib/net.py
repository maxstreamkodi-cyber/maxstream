# -*- coding: utf-8 -*-
"""Tiny HTTP layer on top of urllib (no external dependency)."""
import gzip
import json
import socket
import ssl
import urllib.error
import urllib.request

from .common import DEFAULT_UA, get_bool, get_int, get_setting, log


class NetError(Exception):
    pass


def user_agent():
    return get_setting('user_agent', DEFAULT_UA)


def _context():
    if get_bool('verify_ssl', True):
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _open(url, timeout=None, headers=None):
    hdrs = {'User-Agent': user_agent(), 'Accept-Encoding': 'gzip', 'Accept': '*/*'}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    timeout = timeout or get_int('timeout', 20)
    log('GET %s' % _mask(url))
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=_context())
    except urllib.error.HTTPError as err:
        raise NetError('HTTP %s' % err.code)
    except urllib.error.URLError as err:
        raise NetError(str(err.reason))
    except (socket.timeout, ssl.SSLError, OSError) as err:
        raise NetError(str(err))


def _mask(url):
    """Avoid writing passwords to the Kodi log."""
    import re
    return re.sub(r'(password=)[^&]+', r'\1***', url)


def fetch(url, timeout=None, headers=None):
    resp = _open(url, timeout, headers)
    try:
        data = resp.read()
    except (socket.timeout, OSError) as err:
        raise NetError(str(err))
    finally:
        resp.close()
    if data[:2] == b'\x1f\x8b':
        try:
            data = gzip.decompress(data)
        except OSError:
            pass
    return data


def fetch_text(url, timeout=None):
    data = fetch(url, timeout)
    for enc in ('utf-8-sig', 'latin-1'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', 'replace')


def fetch_json(url, timeout=None):
    text = fetch_text(url, timeout).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        raise NetError('Invalid response from server')


def download(url, dest, progress=None, timeout=None):
    """Stream a (possibly huge) file to disk. progress(bytes_done, total) -> False aborts."""
    resp = _open(url, timeout or max(get_int('timeout', 20), 60))
    total = int(resp.headers.get('Content-Length') or 0)
    done = 0
    try:
        with open(dest, 'wb') as out:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress and progress(done, total) is False:
                    raise NetError('cancelled')
    except (socket.timeout, OSError) as err:
        raise NetError(str(err))
    finally:
        resp.close()
    return dest
