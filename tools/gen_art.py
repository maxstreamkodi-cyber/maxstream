# -*- coding: utf-8 -*-
"""Generate icon.png, fanart.jpg and menu icons (original artwork)."""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = sys.argv[1]
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
S = 4  # supersampling


def gradient(size, top, bottom):
    w, h = size
    img = Image.new('RGB', size)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        col = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = col
    return img


def tile(color, draw_glyph, size=256):
    big = size * S
    base = gradient((big, big), tuple(min(255, c + 40) for c in color), tuple(int(c * 0.55) for c in color))
    mask = Image.new('L', (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius=int(big * 0.22), fill=255)
    out = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    d = ImageDraw.Draw(out)
    draw_glyph(d, big)
    return out.resize((size, size), Image.LANCZOS)


W = (255, 255, 255, 255)


def g_tv(d, s):
    d.rounded_rectangle([s * .2, s * .28, s * .8, s * .7], radius=s * .05, outline=W, width=int(s * .055))
    d.line([s * .4, s * .16, s * .5, s * .27, s * .6, s * .16], fill=W, width=int(s * .045), joint='curve')
    d.line([s * .38, s * .79, s * .62, s * .79], fill=W, width=int(s * .055))


def g_movie(d, s):
    d.rounded_rectangle([s * .2, s * .32, s * .8, s * .78], radius=s * .04, fill=W)
    d.polygon([(s * .2, s * .3), (s * .78, s * .16), (s * .8, s * .25), (s * .22, s * .39)], fill=W)
    for i in range(3):
        x = s * (.3 + i * .17)
        d.polygon([(x, s * .27), (x + s * .07, s * .25), (x + s * .03, s * .35), (x - s * .04, s * .37)], fill=(0, 0, 0, 90))


def g_series(d, s):
    for i, off in enumerate((.0, .07, .14)):
        box = [s * (.18 + off), s * (.18 + off), s * (.68 + off), s * (.62 + off)]
        if i < 2:
            d.rounded_rectangle(box, radius=s * .04, outline=W, width=int(s * .04))
        else:
            d.rounded_rectangle(box, radius=s * .04, fill=W)
    cx, cy = s * .57, s * .54
    d.polygon([(cx - s * .06, cy - s * .08), (cx - s * .06, cy + s * .08), (cx + s * .08, cy)], fill=(0, 0, 0, 140))


def g_catchup(d, s):
    w = int(s * .06)
    d.arc([s * .2, s * .2, s * .8, s * .8], start=-60, end=230, fill=W, width=w)
    a = math.radians(230)
    x, y = s * .5 + s * .3 * math.cos(a), s * .5 + s * .3 * math.sin(a)
    d.polygon([(x - s * .1, y + s * .02), (x + s * .07, y - s * .06), (x + s * .06, y + s * .12)], fill=W)
    d.line([s * .5, s * .32, s * .5, s * .52, s * .63, s * .6], fill=W, width=w, joint='curve')


def star(d, s, cx, cy, r, fill):
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rr = r if i % 2 == 0 else r * .45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fill)


def g_fav(d, s):
    star(d, s, s * .5, s * .53, s * .33, W)


def g_continue(d, s):
    d.polygon([(s * .3, s * .22), (s * .3, s * .78), (s * .75, s * .5)], fill=W)
    d.rounded_rectangle([s * .18, s * .84, s * .82, s * .88], radius=s * .02, fill=(255, 255, 255, 120))
    d.rounded_rectangle([s * .18, s * .84, s * .55, s * .88], radius=s * .02, fill=W)


def g_recent(d, s):
    w = int(s * .06)
    d.ellipse([s * .2, s * .2, s * .8, s * .8], outline=W, width=w)
    d.line([s * .5, s * .3, s * .5, s * .5, s * .65, s * .6], fill=W, width=w, joint='curve')


def g_search(d, s):
    w = int(s * .07)
    d.ellipse([s * .2, s * .2, s * .6, s * .6], outline=W, width=w)
    d.line([s * .56, s * .56, s * .8, s * .8], fill=W, width=int(s * .09))


def g_account(d, s):
    d.ellipse([s * .37, s * .18, s * .63, s * .44], fill=W)
    d.pieslice([s * .2, s * .5, s * .8, s * 1.1], start=180, end=360, fill=W)


def g_playlists(d, s):
    w = int(s * .06)
    for i in range(3):
        y = s * (.28 + i * .2)
        d.ellipse([s * .18, y - s * .04, s * .26, y + s * .04], fill=W)
        d.line([s * .34, y, s * .82, y], fill=W, width=w)


def g_epg(d, s):
    d.rounded_rectangle([s * .18, s * .22, s * .82, s * .8], radius=s * .05, outline=W, width=int(s * .05))
    d.line([s * .18, s * .36, s * .82, s * .36], fill=W, width=int(s * .05))
    for r in range(2):
        for c in range(3):
            x, y = s * (.27 + c * .17), s * (.47 + r * .16)
            d.rectangle([x, y, x + s * .11, y + s * .09], fill=W)


def g_refresh(d, s):
    w = int(s * .06)
    d.arc([s * .22, s * .22, s * .78, s * .78], start=20, end=320, fill=W, width=w)
    a = math.radians(320)
    x, y = s * .5 + s * .28 * math.cos(a), s * .5 + s * .28 * math.sin(a)
    d.polygon([(x - s * .02, y - s * .12), (x + s * .12, y + s * .01), (x - s * .1, y + s * .07)], fill=W)


def g_settings(d, s):
    cx = cy = s * .5
    for i in range(8):
        a = math.radians(i * 45)
        x, y = cx + s * .27 * math.cos(a), cy + s * .27 * math.sin(a)
        d.ellipse([x - s * .07, y - s * .07, x + s * .07, y + s * .07], fill=W)
    d.ellipse([cx - s * .25, cy - s * .25, cx + s * .25, cy + s * .25], fill=W)
    d.ellipse([cx - s * .1, cy - s * .1, cx + s * .1, cy + s * .1], fill=(0, 0, 0, 0))


def g_add(d, s):
    w = int(s * .09)
    d.line([s * .5, s * .22, s * .5, s * .78], fill=W, width=w)
    d.line([s * .22, s * .5, s * .78, s * .5], fill=W, width=w)


ICONS = {
    'live': ((229, 57, 53), g_tv), 'movie': ((142, 36, 170), g_movie), 'series': ((30, 136, 229), g_series),
    'catchup': ((0, 137, 123), g_catchup), 'favourites': ((251, 140, 0), g_fav),
    'continue': ((67, 160, 71), g_continue), 'recent': ((84, 110, 122), g_recent),
    'search': ((57, 73, 171), g_search), 'account': ((0, 151, 167), g_account),
    'playlists': ((109, 76, 65), g_playlists), 'epg': ((216, 27, 96), g_epg),
    'refresh': ((3, 155, 229), g_refresh), 'settings': ((97, 97, 97), g_settings), 'add': ((41, 182, 246), g_add),
}



# ---------------- add-on icon: play triangle inside a signal "stream" wave
def g_logo(d, s):
    d.polygon([(s * .36, s * .28), (s * .36, s * .72), (s * .72, s * .5)], fill=W)
    for i, r in enumerate((.36, .44)):
        d.arc([s * (.5 - r), s * (.5 - r), s * (.5 + r), s * (.5 + r)], start=-50, end=50,
              fill=(255, 255, 255, 230 - i * 70), width=int(s * .035))
        d.arc([s * (.5 - r), s * (.5 - r), s * (.5 + r), s * (.5 + r)], start=130, end=230,
              fill=(255, 255, 255, 230 - i * 70), width=int(s * .035))


icon = tile((21, 101, 192), g_logo, 512)
bg = Image.new('RGB', icon.size, (10, 18, 32))
bg.paste(icon, (0, 0), icon)
bg.save(os.path.join(ROOT, 'icon.png'))

# ---------------- fanart
W2, H2 = 1920, 1080
fan = gradient((W2, H2), (8, 14, 28), (14, 40, 78)).convert('RGBA')
glow = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for i in range(14):
    r = 180 + i * 70
    gd.ellipse([1450 - r, 540 - r, 1450 + r, 540 + r], outline=(41, 182, 246, max(8, 70 - i * 5)), width=3)
glow = glow.filter(ImageFilter.GaussianBlur(2))
fan = Image.alpha_composite(fan, glow)
logo = tile((21, 101, 192), g_logo, 300)
fan.paste(logo, (1300, 390), logo)
d = ImageDraw.Draw(fan)
font = ImageFont.truetype(BOLD, 120)
small = ImageFont.truetype(BOLD, 44)
d.text((160, 400), 'MaxStream', font=font, fill=(255, 255, 255))
d.text((166, 560), 'Live TV  ·  Movies  ·  Series  ·  Catch-up', font=small, fill=(144, 202, 249))
fan.convert('RGB').save(os.path.join(ROOT, 'fanart.jpg'), quality=88)
print('art done')
