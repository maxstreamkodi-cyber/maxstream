import os, re
ALPHANUM_HIDE_INPUT = 2
RESPONSES = []   # queue of scripted dialog answers
DIALOGS = []
INFO_SHOWN = []
WINDOWS = []     # every window/dialog created, in order
def _answer(kind, *args):
    DIALOGS.append((kind,) + args)
    if RESPONSES:
        return RESPONSES.pop(0)
    raise AssertionError('no scripted answer for %s %r' % (kind, args))
class InfoTag(object):
    def __init__(self): self.data = {}
    def __getattr__(self, name):
        if name.startswith('set'):
            def setter(*a): self.data[name[3:].lower()] = a if len(a) > 1 else a[0]
            return setter
        raise AttributeError(name)
class ListItem(object):
    def __init__(self, label='', label2='', path='', offscreen=False):
        self.label, self.label2, self.path = label, label2, path
        self.art, self.props, self.ctx, self.tag, self.mime = {}, {}, [], InfoTag(), None
    def setArt(self, a): self.art.update(a)
    def getArt(self, k): return self.art.get(k, '')
    def setProperty(self, k, v): self.props[k] = v
    def getProperty(self, k): return self.props.get(k, '')
    def addContextMenuItems(self, items): self.ctx += items
    def getVideoInfoTag(self): return self.tag
    def setLabel(self, l): self.label = l
    def setLabel2(self, l): self.label2 = l
    def getLabel(self): return self.label
    def getLabel2(self): return self.label2
    def setMimeType(self, m): self.mime = m
    def setContentLookup(self, v): pass
    def setPath(self, p): self.path = p
    def getPath(self): return self.path
class Dialog(object):
    def notification(self, h, m, icon=None, t=0): DIALOGS.append(('notification', m))
    def ok(self, h, m): DIALOGS.append(('ok', m)); return True
    def yesno(self, h, m, *a, **k): return _answer('yesno', m)
    def select(self, h, items, *a, **k): return _answer('select', h, items)
    def multiselect(self, h, items, *a, **k): return _answer('multiselect', h, items)
    def contextmenu(self, items): return _answer('contextmenu', items)
    def input(self, h, defaultt='', type=0, option=0, autoclose=0): return _answer('input', h, defaultt)
    def numeric(self, t, h, defaultt='', bHiddenInput=False): return _answer('numeric', h)
    def browse(self, t, h, s, mask='', *a, **k): return _answer('browse', h)
    def textviewer(self, h, text, usemono=False): DIALOGS.append(('textviewer', h, text))
    def info(self, li): INFO_SHOWN.append(li); return True
class DialogProgress(object):
    def create(self, h, m=''): pass
    def update(self, p, m=''): pass
    def iscanceled(self): return False
    def close(self): pass
_PROPS = {}
class Window(object):
    def __init__(self, wid=None): pass
    def getProperty(self, k): return _PROPS.get(k, '')
    def setProperty(self, k, v): _PROPS[k] = v

class Control(object):
    def __init__(self, cid, ctype):
        self.id, self.type, self.items, self.selected, self.percent, self.nav = cid, ctype, [], 0, 0, {}
    def getId(self): return self.id
    def reset(self): self.items, self.selected = [], 0
    def addItems(self, items): self.items += list(items)
    def addItem(self, item): self.items.append(item)
    def size(self): return len(self.items)
    def getSelectedPosition(self): return self.selected if self.items else -1
    def selectItem(self, i): self.selected = i
    def getSelectedItem(self): return self.items[self.selected] if self.items else None
    def getListItem(self, i): return self.items[i]
    def setPercent(self, p): self.percent = p
    def setVisible(self, v): pass
    def controlLeft(self, c): self.nav['left'] = c.id
    def controlRight(self, c): self.nav['right'] = c.id
    def controlUp(self, c): self.nav['up'] = c.id
    def controlDown(self, c): self.nav['down'] = c.id
    def labels(self): return [i.label for i in self.items]

def _xml_controls(path):
    xml = open(path, encoding='utf-8').read()
    return {int(i): t for t, i in re.findall(r'<control type="(\w+)" id="(\d+)"', xml)}

class WindowXML(object):
    def __init__(self, xml, path, skin='Default', res='720p', isMedia=False):
        full = os.path.join(path, 'resources', 'skins', skin, res, xml)
        assert os.path.exists(full), full
        self.xmlfile, self.ids = xml, _xml_controls(full)
        self.controls, self.props, self.focus, self.closed, self.inits = {}, {}, None, False, 0
        WINDOWS.append(self)
    def getControl(self, cid):
        if cid not in self.ids:
            raise RuntimeError('Non-Existent Control %d in %s' % (cid, self.xmlfile))
        return self.controls.setdefault(cid, Control(cid, self.ids[cid]))
    def setProperty(self, k, v): self.props[k] = v
    def getProperty(self, k): return self.props.get(k, '')
    def clearProperty(self, k): self.props.pop(k, None)
    def setFocusId(self, cid):
        if cid not in self.ids: raise RuntimeError('focus on missing %d' % cid)
        self.focus = cid
    def setFocus(self, c): self.focus = c.id
    def getFocusId(self): return self.focus
    def doModal(self):
        self.inits += 1
        self.onInit()
    def show(self): self.doModal()
    def close(self): self.closed = True
    def onInit(self): pass
class WindowXMLDialog(WindowXML):
    pass
class Action(object):
    def __init__(self, aid): self.aid = aid
    def getId(self): return self.aid
