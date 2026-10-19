import os
ROOT = os.environ['KODI_TEST_ROOT']
def translatePath(p):
    return p.replace('special://profile/', ROOT + '/profile/')
class File(object):
    def __init__(self, path): self.f = open(path, 'rb')
    def readBytes(self): return bytearray(self.f.read())
    def close(self): self.f.close()
