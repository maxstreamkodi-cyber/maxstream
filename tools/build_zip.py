# -*- coding: utf-8 -*-
"""Build dist/script.maxstream-<version>.zip, installable via Kodi > Add-ons > Install from zip file."""
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ADDON = 'script.maxstream'
SRC = os.path.join(ROOT, ADDON)

version = re.search(r'<addon[^>]+version="([^"]+)"', open(os.path.join(SRC, 'addon.xml'), encoding='utf-8').read()).group(1)
os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
target = os.path.join(ROOT, 'dist', '%s-%s.zip' % (ADDON, version))
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
    for folder, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
        for name in files:
            if name.endswith(('.pyc', '.pyo')) or name.startswith('.'):
                continue
            path = os.path.join(folder, name)
            zf.write(path, os.path.join(ADDON, os.path.relpath(path, SRC)).replace(os.sep, '/'))
print(target)
