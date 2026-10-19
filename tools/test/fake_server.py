import gzip, json, threading, time, base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

NOW = int(time.time())
def xt(ts): return time.strftime('%Y%m%d%H%M%S +0000', time.gmtime(ts))

LIVE_CATS = [{'category_id': '1', 'category_name': 'News'}, {'category_id': '2', 'category_name': 'Sports'},
             {'category_id': '3', 'category_name': 'XXX Adult'}, {'category_id': '4', 'category_name': 'Empty'}]
LIVE = [
    {'num': 1, 'name': 'France 24', 'stream_id': 101, 'stream_icon': 'http://x/f24.png', 'epg_channel_id': 'france24.fr', 'category_id': '1', 'tv_archive': 1, 'tv_archive_duration': 3, 'added': '1700000000'},
    {'num': 2, 'name': 'Euro Sport 1', 'stream_id': 102, 'stream_icon': '', 'epg_channel_id': 'eurosport1', 'category_id': '2', 'tv_archive': 0, 'tv_archive_duration': 0, 'added': '1700000100'},
    {'num': 3, 'name': 'Night Channel', 'stream_id': 103, 'stream_icon': '', 'epg_channel_id': None, 'category_id': '3', 'tv_archive': 0, 'added': '1'},
]
VOD_CATS = [{'category_id': '10', 'category_name': 'Action'}, {'category_id': '11', 'category_name': 'Comédie'}]
VOD = [
    {'num': 1, 'name': 'Big Movie (2021)', 'stream_id': 201, 'stream_icon': 'http://x/p.jpg', 'rating': '7.5', 'added': '1710000000', 'category_id': '10', 'container_extension': 'mkv'},
    {'num': 2, 'name': 'Le Dîner de cons', 'stream_id': 202, 'stream_icon': '', 'rating': '', 'added': '1600000000', 'category_id': '11', 'container_extension': 'mp4'},
]
SER_CATS = [{'category_id': '20', 'category_name': 'Drama'}]
SERIES = [{'num': 1, 'name': 'The Show', 'series_id': 301, 'cover': 'http://x/s.jpg', 'plot': 'A show.', 'genre': 'Drama', 'releaseDate': '2019-01-01', 'last_modified': '1720000000', 'rating': '8', 'backdrop_path': ['http://x/b.jpg'], 'category_id': '20'},
          {'num': 2, 'name': 'Mini', 'series_id': 302, 'cover': '', 'category_id': '20', 'last_modified': '1'}]
SERIES_INFO = {
    '301': {'seasons': [{'season_number': 1, 'name': 'Season 1', 'cover': ''}],
            'info': {'name': 'The Show', 'plot': 'Plot', 'backdrop_path': ['http://x/b.jpg'], 'releaseDate': '2019-01-01'},
            'episodes': {'1': [{'id': '4001', 'episode_num': 2, 'title': 'The Show S01E02', 'container_extension': 'mkv', 'season': 1, 'info': {'plot': 'ep2', 'duration_secs': 2700}},
                               {'id': '4000', 'episode_num': 1, 'title': 'The Show S01E01', 'container_extension': 'mkv', 'season': 1, 'info': []}],
                         '2': [{'id': '4010', 'episode_num': 1, 'title': 'The Show S02E01', 'container_extension': 'mp4', 'season': 2, 'info': {}}]}},
    '302': {'seasons': [], 'info': {'name': 'Mini'}, 'episodes': [[{'id': '5000', 'episode_num': 1, 'title': 'Mini E1', 'container_extension': 'mp4', 'info': {}}]]},
}

def b64(s): return base64.b64encode(s.encode()).decode()

def xmltv():
    out = ['<?xml version="1.0" encoding="UTF-8"?><tv>',
           '<channel id="france24.fr"><display-name>France 24</display-name></channel>',
           '<channel id="EuroSport1"><display-name>Eurosport 1</display-name></channel>',
           '<channel id="arte.fr"><display-name>Arte</display-name></channel>']
    for cid in ('france24.fr', 'EuroSport1', 'arte.fr'):
        for i in range(-30, 30):
            s = NOW - NOW % 3600 + i * 3600
            out.append('<programme start="%s" stop="%s" channel="%s"><title>%s show %d &amp; co</title><desc>Desc %d</desc></programme>' % (xt(s), xt(s + 3600), cid, cid, i, i))
    out.append('</tv>')
    return '\n'.join(out).encode()

M3U_PLAIN = '''#EXTM3U url-tvg="{base}/epg.xml.gz" catchup="shift"
#EXTINF:-1 tvg-id="arte.fr" tvg-name="Arte" tvg-logo="http://x/arte.png" group-title="TV, FR" catchup-days="5",Arte HD
#EXTVLCOPT:http-user-agent=MyUA/1.0
http://stream.example/arte/index.m3u8
#EXTINF:-1 tvg-id="" group-title="TV, FR",France 24
#KODIPROP:inputstream=inputstream.adaptive
http://stream.example/f24.m3u8
#EXTINF:-1 tvg-id="x" group-title="Adult XXX",Hot
http://stream.example/hot.ts
#EXTINF:-1 tvg-logo="http://x/m.jpg" group-title="Films",Some Film (2020)
http://vod.example/films/some_film.mkv
#EXTINF:-1 group-title="Séries",Cool Show S01 E01
http://vod.example/cool/s1e1.mp4
#EXTINF:-1 group-title="Séries",Cool Show S01 E02
http://vod.example/cool/s1e2.mp4
#EXTINF:-1 group-title="Séries",Cool Show S02E01
http://vod.example/cool/s2e1.mp4
#EXTINF:-1 group-title="Séries",Other.Show.S01E01.720p
http://vod.example/other/s1e1.mp4
'''

VOD_DATA = bytes((i * 7 + i // 251) % 256 for i in range(5 * 1024 * 1024))
STATE = {'vod_conn': 0, 'live_conn': 0}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, body, ctype='application/json', gz=False):
        if isinstance(body, str): body = body.encode()
        if gz: body = gzip.compress(body)
        self.send_response(200); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        base = 'http://%s:%d' % self.server.server_address
        if u.path == '/player_api.php':
            if q.get('username') != 'u' or q.get('password') != 'p':
                return self.send(json.dumps({'user_info': {'auth': 0}}))
            a = q.get('action')
            data = {None: {'user_info': {'auth': 1, 'username': 'u', 'status': 'Active', 'exp_date': '1893456000', 'is_trial': '0', 'active_cons': '0', 'max_connections': '2', 'created_at': '1600000000'}, 'server_info': {'timezone': 'Europe/Brussels'}},
                    'get_live_categories': LIVE_CATS, 'get_live_streams': LIVE, 'get_vod_categories': VOD_CATS, 'get_vod_streams': VOD,
                    'get_series_categories': SER_CATS, 'get_series': SERIES,
                    'get_series_info': SERIES_INFO.get(q.get('series_id'), {}),
                    'get_vod_info': {'info': {'name': 'Big Movie', 'plot': 'Explosions.', 'cast': 'A, B', 'director': 'C', 'genre': 'Action', 'releasedate': '2021-05-01', 'duration_secs': 6000, 'rating': '7.5', 'backdrop_path': ['http://x/bd.jpg']}, 'movie_data': {}},
                    'get_simple_data_table': {'epg_listings': [{'title': b64('Past news'), 'description': b64('old'), 'start': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(NOW - 7200)), 'end': '', 'start_timestamp': str(NOW - 7200), 'stop_timestamp': str(NOW - 3600), 'has_archive': 1},
                                                              {'title': b64('Current news'), 'description': b64('now'), 'start': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(NOW - 600)), 'end': '', 'start_timestamp': str(NOW - 600), 'stop_timestamp': str(NOW + 600), 'has_archive': 0},
                                                              {'title': b64('Future'), 'description': '', 'start': '', 'end': '', 'start_timestamp': str(NOW + 600), 'stop_timestamp': str(NOW + 4200), 'has_archive': 0}]},
                    }
            return self.send(json.dumps(data.get(a, [])))
        if u.path == '/xmltv.php':
            return self.send(xmltv(), 'application/xml')
        if u.path == '/epg.xml.gz':
            return self.send(gzip.compress(xmltv()), 'application/gzip')
        if u.path == '/plain.m3u':
            return self.send(M3U_PLAIN.replace('{base}', base), 'audio/x-mpegurl', gz=True)
        if u.path == '/vodfile.mkv':
            STATE['vod_conn'] += 1
            conn = STATE['vod_conn']
            rng = self.headers.get('Range')
            start = int(rng.split('=')[1].split('-')[0]) if rng else 0
            body = VOD_DATA[start:]
            self.send_response(206 if rng else 200)
            self.send_header('Content-Type', 'video/x-matroska')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(len(body)))
            if rng:
                self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, len(VOD_DATA) - 1, len(VOD_DATA)))
            self.end_headers()
            try:
                if conn == 1:      # stall in the middle
                    self.wfile.write(body[:1024 * 1024]); self.wfile.flush(); time.sleep(3)
                    self.wfile.write(body[1024 * 1024:])
                elif conn == 2:    # drop the connection
                    self.wfile.write(body[:2 * 1024 * 1024]); self.wfile.flush()
                    self.connection.shutdown(2)
                else:
                    self.wfile.write(body)
            except OSError:
                pass
            return
        if u.path == '/live.ts':
            STATE['live_conn'] += 1
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp2t')
            self.end_headers()
            try:
                self.wfile.write(b'\x47' * 200000)
            except OSError:
                pass
            return
        if u.path == '/get.php':
            return self.send('#EXTM3U\n', 'audio/x-mpegurl')
        self.send_response(404); self.end_headers()

def start():
    srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d' % srv.server_address[1]
