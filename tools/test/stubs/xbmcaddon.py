import os, re
ROOT = os.environ['KODI_TEST_ROOT']; ADDON_DIR = os.environ['KODI_ADDON_DIR']
SETTINGS = {}
_DEF = None
def _defaults():
    xml = open(os.path.join(ADDON_DIR, 'resources/settings.xml'), encoding='utf-8').read()
    return dict(re.findall(r'<setting id="(\w+)"[^>]*>\s*<level>0</level>\s*<default>([^<]*)</default>', xml))
def _strings():
    po = open(os.path.join(ADDON_DIR, 'resources/language/resource.language.en_gb/strings.po'), encoding='utf-8').read()
    return {int(a): b.replace('\\"', '"') for a, b in re.findall(r'msgctxt "#(\d+)"\nmsgid "((?:[^"\\]|\\.)*)"', po)}
STR = _strings()
class Addon(object):
    def __init__(self, id=None):
        assert id in (None, 'script.maxstream'), id
    def getAddonInfo(self, key):
        return {'id': 'script.maxstream', 'name': 'MaxStream IPTV', 'version': '2.0.0',
                'path': ADDON_DIR, 'profile': 'special://profile/addon_data/script.maxstream/'}[key]
    def getSetting(self, sid):
        global _DEF
        if _DEF is None:
            _DEF = _defaults()
        return SETTINGS.get(sid, _DEF.get(sid, ''))
    def setSetting(self, sid, value): SETTINGS[sid] = value
    def getLocalizedString(self, sid): return STR.get(sid, '')
    def openSettings(self): pass
