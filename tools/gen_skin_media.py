# -*- coding: utf-8 -*-
"""Textures for the graphical interface: rounded shapes (tinted in XML with
colordiffuse), image masks, fades and white glyph icons."""
import math
import os
import sys

from PIL import Image, ImageDraw

OUT = os.path.join(sys.argv[1], 'resources', 'skins', 'Default', 'media')
os.makedirs(OUT, exist_ok=True)
S = 4
W = (255, 255, 255, 255)


def save(img, name):
    img.save(os.path.join(OUT, name))


def rounded(w, h, r, ring=0):
    big = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    if ring:
        d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=r * S, outline=W, width=ring * S)
    else:
        d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=r * S, fill=W)
    return big.resize((w, h), Image.LANCZOS)


save(Image.new('RGBA', (16, 16), W), 'ms_white.png')
save(rounded(16, 16, 4), 'ms_r4.png')
save(rounded(48, 48, 12), 'ms_r12.png')
save(rounded(64, 64, 20), 'ms_r20.png')
save(rounded(96, 96, 28), 'ms_r28.png')
save(rounded(96, 96, 26, ring=5), 'ms_ring20.png')
save(rounded(128, 128, 38, ring=6), 'ms_ring28.png')
# masks (diffuse) at their final aspect ratios
save(rounded(240, 360, 20), 'ms_mask_poster.png')
save(rounded(373, 560, 24), 'ms_mask_poster_big.png')
save(rounded(320, 180, 16), 'ms_mask_thumb.png')
save(rounded(128, 128, 22), 'ms_mask_square.png')

fade_h = Image.new('RGBA', (512, 8))
for x in range(512):
    a = int(255 * (1 - x / 511.0) ** 1.4)
    for y in range(8):
        fade_h.putpixel((x, y), (255, 255, 255, a))
save(fade_h, 'ms_fade_h.png')
fade_v = Image.new('RGBA', (8, 256))
for y in range(256):
    a = int(255 * (y / 255.0) ** 1.6)
    for x in range(8):
        fade_v.putpixel((x, y), (255, 255, 255, a))
save(fade_v, 'ms_fade_v.png')


def icon(name, draw, size=128):
    big = Image.new('RGBA', (size * S, size * S), (0, 0, 0, 0))
    draw(ImageDraw.Draw(big), size * S)
    save(big.resize((size, size), Image.LANCZOS), 'ic_%s.png' % name)


def lw(s, f=0.07):
    return int(s * f)


def tv(d, s):
    d.rounded_rectangle([s * .1, s * .27, s * .9, s * .8], radius=s * .07, outline=W, width=lw(s))
    d.line([s * .35, s * .1, s * .5, s * .25, s * .65, s * .1], fill=W, width=lw(s), joint='curve')


def movie(d, s):
    d.rounded_rectangle([s * .12, s * .38, s * .88, s * .86], radius=s * .05, outline=W, width=lw(s))
    d.polygon([(s * .1, s * .34), (s * .82, s * .14), (s * .86, s * .27), (s * .14, s * .47)], outline=W, fill=None)
    d.line([s * .1, s * .34, s * .82, s * .14, s * .86, s * .27, s * .14, s * .47, s * .1, s * .34], fill=W, width=lw(s), joint='curve')


def series(d, s):
    d.rounded_rectangle([s * .3, s * .3, s * .9, s * .78], radius=s * .05, outline=W, width=lw(s))
    d.line([s * .2, s * .68, s * .2, s * .22, s * .78, s * .22], fill=W, width=lw(s), joint='curve')
    d.polygon([(s * .52, s * .43), (s * .52, s * .65), (s * .7, s * .54)], fill=W)


def catchup(d, s):
    d.arc([s * .14, s * .14, s * .86, s * .86], start=-60, end=225, fill=W, width=lw(s))
    a = math.radians(225)
    x, y = s * .5 + s * .36 * math.cos(a), s * .5 + s * .36 * math.sin(a)
    d.polygon([(x - s * .12, y + s * .02), (x + s * .08, y - s * .08), (x + s * .07, y + s * .14)], fill=W)
    d.line([s * .5, s * .3, s * .5, s * .52, s * .66, s * .62], fill=W, width=lw(s), joint='curve')


def epg(d, s):
    d.rounded_rectangle([s * .12, s * .18, s * .88, s * .86], radius=s * .06, outline=W, width=lw(s))
    d.line([s * .12, s * .36, s * .88, s * .36], fill=W, width=lw(s))
    d.line([s * .32, s * .08, s * .32, s * .26], fill=W, width=lw(s))
    d.line([s * .68, s * .08, s * .68, s * .26], fill=W, width=lw(s))
    for r in range(2):
        for c in range(3):
            x, y = s * (.24 + c * .19), s * (.48 + r * .18)
            d.rectangle([x, y, x + s * .12, y + s * .1], fill=W)


def star_points(s, r_out=.4, r_in=.17, cy=.53):
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rr = s * (r_out if i % 2 == 0 else r_in)
        pts.append((s * .5 + rr * math.cos(ang), s * cy + rr * math.sin(ang)))
    return pts


def fav(d, s):
    d.polygon(star_points(s), fill=W)


def fav_o(d, s):
    pts = star_points(s)
    d.line(pts + [pts[0]], fill=W, width=lw(s, .06), joint='curve')


def search(d, s):
    d.ellipse([s * .14, s * .14, s * .64, s * .64], outline=W, width=lw(s, .08))
    d.line([s * .58, s * .58, s * .86, s * .86], fill=W, width=lw(s, .1))


def lists(d, s):
    for i in range(3):
        y = s * (.25 + i * .25)
        d.ellipse([s * .1, y - s * .05, s * .2, y + s * .05], fill=W)
        d.line([s * .32, y, s * .9, y], fill=W, width=lw(s))


def account(d, s):
    d.ellipse([s * .34, s * .12, s * .66, s * .44], outline=W, width=lw(s))
    d.arc([s * .16, s * .52, s * .84, s * 1.2], start=180, end=360, fill=W, width=lw(s))


def settings(d, s):
    cx = cy = s * .5
    for i in range(8):
        a = math.radians(i * 45)
        x, y = cx + s * .33 * math.cos(a), cy + s * .33 * math.sin(a)
        d.ellipse([x - s * .08, y - s * .08, x + s * .08, y + s * .08], fill=W)
    d.ellipse([cx - s * .3, cy - s * .3, cx + s * .3, cy + s * .3], fill=W)
    d.ellipse([cx - s * .12, cy - s * .12, cx + s * .12, cy + s * .12], fill=(0, 0, 0, 0))


def back(d, s):
    d.line([s * .62, s * .2, s * .32, s * .5, s * .62, s * .8], fill=W, width=lw(s, .1), joint='curve')


def play(d, s):
    d.polygon([(s * .28, s * .16), (s * .28, s * .84), (s * .84, s * .5)], fill=W)


for name, fn in [('live', tv), ('movie', movie), ('series', series), ('catchup', catchup), ('epg', epg),
                 ('fav', fav), ('fav_o', fav_o), ('search', search), ('lists', lists), ('account', account),
                 ('settings', settings), ('back', back), ('play', play)]:
    icon(name, fn)
try:
    import segno
    segno.make('https://paypal.me/MaxStreamKodi/5EUR', error='m').save(
        os.path.join(OUT, 'donate_qr.png'), scale=12, border=2, dark='#0B1220', light='#FFFFFF')
except ImportError:
    print('segno missing: donate_qr.png not regenerated (pip install segno)')
print('skin media ok:', len(os.listdir(OUT)))
