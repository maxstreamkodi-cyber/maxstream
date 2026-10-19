# -*- coding: utf-8 -*-
"""Approximate renderer of the WindowXML files (for visual checks without Kodi).
python render_skin.py <addon_dir> <xml name> <out.png> <focus id> [json with props/list samples]"""
import json
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ADDON, NAME, OUT, FOCUS = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
DATA = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
PROPS = DATA.get('props', {})
LISTS = DATA.get('lists', {})
PO = open(ADDON + '/resources/language/resource.language.fr_fr/strings.po', encoding='utf-8').read()
STR = {int(a): (c or b) for a, b, c in re.findall(r'msgctxt "#(\d+)"\nmsgid "((?:[^"\\]|\\.)*)"\nmsgstr "((?:[^"\\]|\\.)*)"', PO)}
FONTS = {'font10': 23, 'font12': 27, 'font13': 31, 'font37': 40, 'font45': 50}
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MEDIA = ADDON + '/resources/skins/Default/media/'


def color(argb):
    v = int(argb, 16)
    return ((v >> 16) & 255, (v >> 8) & 255, v & 255, (v >> 24) & 255)


def resolve(text, item=None):
    text = re.sub(r'\$ADDON\[[\w.]+ (\d+)\]', lambda m: STR.get(int(m.group(1)), '?'), text)
    text = re.sub(r'\$INFO\[Window\.Property\((\w+)\)\]', lambda m: PROPS.get(m.group(1), ''), text)
    text = text.replace('$INFO[System.Time]', '21:04').replace('$INFO[System.Date]', 'dimanche 18 octobre 2026')
    item = item or {}
    text = re.sub(r'\$INFO\[(?:Container\(\d+\)\.)?ListItem\.Label\]', item.get('label', ''), text)
    text = re.sub(r'\$INFO\[(?:Container\(\d+\)\.)?ListItem\.Label2\]', item.get('label2', ''), text)
    text = re.sub(r'\$INFO\[(?:Container\(\d+\)\.)?ListItem\.Property\((\w+)\)\]', lambda m: str(item.get(m.group(1), '')), text)
    text = re.sub(r'\$INFO\[ListItem\.Art\(\w+\)\]', item.get('art', ''), text)
    return text.replace('[CR]', '\n')


def cond_ok(cond, item=None, focus=FOCUS):
    if not cond:
        return True
    item = item or {}
    def atom(a):
        a = a.strip()
        neg = a.startswith('!')
        a = a.lstrip('!')
        m = re.match(r'Control\.HasFocus\((\d+)\)', a)
        if m:
            r = int(m.group(1)) == focus
        elif a == 'Player.HasVideo':
            r = PROPS.get('_video') == '1'
        else:
            m = re.match(r'String\.IsEmpty\((.*)\)', a)
            if m:
                r = not value(m.group(1), item)
            else:
                m = re.match(r'String\.IsEqual\((.*),(.*)\)', a)
                if m:
                    r = str(value(m.group(1), item)) == m.group(2)
                else:
                    m = re.match(r'Integer\.IsGreater\((.*),(\d+)\)', a)
                    r = float(value(m.group(1), item) or 0) > int(m.group(2)) if m else True
        return not r if neg else r
    return all(atom(p) for p in cond.split('+'))


def value(expr, item):
    m = re.match(r'Window\.Property\((\w+)\)', expr)
    if m:
        return PROPS.get(m.group(1), '')
    m = re.match(r'ListItem\.Property\((\w+)\)', expr)
    if m:
        return item.get(m.group(1), '')
    if expr.startswith('ListItem.Art'):
        return item.get('art', '')
    if expr == 'ListItem.PercentPlayed':
        return item.get('pct', 0)
    m = re.match(r'Container\((\d+)\)\.NumItems', expr)
    if m:
        return len(LISTS.get(m.group(1), []))
    return ''


def g(el, tag, default=None):
    child = el.find(tag)
    return child.text if child is not None and child.text is not None else default


def box(el, ox, oy):
    return ox + int(g(el, 'left', 0)), oy + int(g(el, 'top', 0)), int(g(el, 'width', 0)), int(g(el, 'height', 0))


def shape(img, x, y, w, h, tex, col, item=None):
    d = ImageDraw.Draw(img, 'RGBA')
    c = color(col) if col else (255, 255, 255, 255)
    if tex.startswith('ms_r') and not tex.startswith('ms_ring'):
        rad = {'ms_r4.png': 3, 'ms_r12.png': 12, 'ms_r20.png': 20, 'ms_r28.png': 28}.get(tex, 10)
        d.rounded_rectangle([x, y, x + w, y + h], radius=min(rad, h // 2, w // 2), fill=c)
    elif tex.startswith('ms_ring'):
        d.rounded_rectangle([x, y, x + w, y + h], radius=26, outline=c, width=5)
    elif tex == 'ms_white.png':
        d.rectangle([x, y, x + w, y + h], fill=c)
    elif tex.startswith('ms_fade'):
        pass
    elif tex.endswith('.png') and '/' not in tex:
        try:
            ic = Image.open(MEDIA + tex).convert('RGBA').resize((max(1, w), max(1, h)))
            tint = Image.new('RGBA', ic.size, c[:3] + (255,))
            tint.putalpha(ic.getchannel('A'))
            img.alpha_composite(tint, (x, y))
        except OSError:
            pass
    elif tex:
        d.rectangle([x, y, x + w, y + h], fill=(70, 90, 120, 255))
        d.text((x + 6, y + 6), 'img', fill=(200, 200, 200, 255))


def text(img, x, y, w, h, label, font, col, align, aligny, wrap=False):
    if not label:
        return
    bold = '[B]' in label
    label = re.sub(r'\[/?B\]|\[COLOR \w+\]|\[/COLOR\]', '', label)
    f = ImageFont.truetype(BOLD if bold else REG, FONTS.get(font, 27))
    d = ImageDraw.Draw(img, 'RGBA')
    lines = label.split('\n')
    if wrap or len(lines) > 1:
        out = []
        for line in lines:
            words, cur = line.split(' '), ''
            for word in words:
                trial = (cur + ' ' + word).strip()
                if d.textlength(trial, font=f) > w and cur:
                    out.append(cur)
                    cur = word
                else:
                    cur = trial
            out.append(cur)
        lines = out
    lh = f.size * 1.25
    total = lh * len(lines)
    ty = y + (h - total) / 2 if aligny == 'center' else (y + h - total if aligny == 'bottom' else y)
    for line in lines:
        while d.textlength(line, font=f) > w and len(line) > 1:
            line = line[:-2] + '…'
        tw = d.textlength(line, font=f)
        tx = x + (w - tw) / 2 if align == 'center' else (x + w - tw if align == 'right' else x)
        if ty + lh > y + h + 4 and (wrap or len(lines) > 1):
            break
        d.text((tx, ty), line, font=f, fill=color(col))
        ty += lh


def render(img, controls, ox, oy, item=None, focus=FOCUS):
    for el in controls:
        if el.tag != 'control':
            continue
        if not cond_ok(g(el, 'visible'), item, focus):
            continue
        t = el.get('type')
        x, y, w, h = box(el, ox, oy)
        if t == 'group':
            render(img, list(el), ox, oy, item, focus)
        elif t == 'image':
            tex = el.find('texture')
            shape(img, x, y, w, h, resolve(tex.text or '', item), tex.get('colordiffuse'), item)
        elif t in ('label', 'textbox'):
            text(img, x, y, w, h, resolve(g(el, 'label', ''), item), g(el, 'font'), g(el, 'textcolor', 'FFFFFFFF'),
                 g(el, 'align', 'left'), g(el, 'aligny', 'top' if t == 'textbox' else 'center'),
                 wrap=t == 'textbox' or g(el, 'wrapmultiline') == 'true')
        elif t == 'button':
            cid = int(el.get('id'))
            tex = el.find('texturefocus' if cid == focus else 'texturenofocus')
            shape(img, x, y, w, h, tex.text, tex.get('colordiffuse'))
            col = g(el, 'focusedcolor') if cid == focus else g(el, 'textcolor')
            off = int(g(el, 'textoffsetx', 0))
            text(img, x + off, y, w - off, h, resolve(g(el, 'label', '')), g(el, 'font'), col, g(el, 'align', 'center'), 'center')
        elif t == 'progress':
            shape(img, x, y, w, h, 'ms_r4.png', el.find('texturebg').get('colordiffuse'))
            pct = PROPS.get('_pct_%s' % el.get('id'), 0) if el.get('id') else (item or {}).get('pct', 0)
            if pct:
                shape(img, x, y, int(w * float(pct) / 100), h, 'ms_r4.png', el.find('midtexture').get('colordiffuse'))
        elif t == 'videowindow':
            shape(img, x, y, w, h, 'ms_white.png', 'FF203040')
        elif t in ('list', 'panel'):
            cid = el.get('id')
            items = LISTS.get(cid, [])
            il, fl = el.find('itemlayout'), el.find('focusedlayout')
            iw, ih = int(il.get('width')), int(il.get('height'))
            horizontal = g(el, 'orientation') == 'horizontal'
            cols = max(1, w // iw) if t == 'panel' else 1
            for idx, it in enumerate(items):
                if t == 'panel':
                    cx, cy = x + (idx % cols) * iw, y + (idx // cols) * ih
                elif horizontal:
                    cx, cy = x + idx * iw, y
                else:
                    cx, cy = x, y + idx * ih
                if cx + iw > x + w + iw or cy + ih > y + h + 4:
                    continue
                layout = fl if idx == it.get('_sel', 0) and idx == 0 else il
                layout = fl if it.get('_focused') else il
                render(img, list(layout), cx, cy, it, focus)


root = ET.parse(ADDON + '/resources/skins/Default/1080i/' + NAME).getroot()
canvas = Image.new('RGBA', (1920, 1080), (0, 0, 0, 255))
render(canvas, list(root.find('controls')), 0, 0)
canvas.convert('RGB').resize((1440, 810), Image.LANCZOS).save(OUT)
print('rendered', OUT)
