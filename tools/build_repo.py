# -*- coding: utf-8 -*-
"""Build the Kodi repository published on GitHub Pages (docs/).

python tools/build_repo.py

docs/
  index.html                          download page (also browsable by Kodi's file manager)
  repository.maxstream-<v>.zip        the zip people install first
  repo/addons.xml, addons.xml.md5     index read by Kodi
  repo/<addon id>/<addon id>-<v>.zip  + icon.png, fanart.jpg
"""
import hashlib
import os
import re
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
ADDONS = ['script.maxstream', 'repository.maxstream']
PAGE_URL = 'https://maxstreamkodi-cyber.github.io/maxstream/'
DONATE_URL = 'https://paypal.me/MaxStreamKodi/5EUR'


def addon_info(folder):
    xml = open(os.path.join(ROOT, folder, 'addon.xml'), encoding='utf-8').read()
    version = re.search(r'<addon[^>]+version="([^"]+)"', xml).group(1)
    body = re.sub(r'^<\?xml[^>]*\?>\s*', '', xml).strip()
    return version, body


def zip_addon(folder, target):
    src = os.path.join(ROOT, folder)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in ('__pycache__', '.git'))
            for name in sorted(files):
                if name.endswith(('.pyc', '.pyo')) or name.startswith('.'):
                    continue
                path = os.path.join(base, name)
                zf.write(path, os.path.join(folder, os.path.relpath(path, src)).replace(os.sep, '/'))


def main():
    shutil.rmtree(DOCS, ignore_errors=True)
    repo = os.path.join(DOCS, 'repo')
    os.makedirs(repo)
    entries, versions = [], {}
    for folder in ADDONS:
        version, body = addon_info(folder)
        versions[folder] = version
        out = os.path.join(repo, folder)
        os.makedirs(out)
        zip_addon(folder, os.path.join(out, '%s-%s.zip' % (folder, version)))
        for asset in ('icon.png', 'fanart.jpg'):
            shutil.copy(os.path.join(ROOT, folder, asset), out)
        entries.append(body)
    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n%s\n</addons>\n' % '\n'.join(entries)
    with open(os.path.join(repo, 'addons.xml'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(addons_xml)
    with open(os.path.join(repo, 'addons.xml.md5'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(hashlib.md5(addons_xml.encode('utf-8')).hexdigest())
    repo_zip = 'repository.maxstream-%s.zip' % versions['repository.maxstream']
    shutil.copy(os.path.join(repo, 'repository.maxstream', repo_zip), os.path.join(DOCS, repo_zip))
    app_zip = 'repo/script.maxstream/script.maxstream-%s.zip' % versions['script.maxstream']
    shutil.copy(os.path.join(ROOT, 'script.maxstream', 'icon.png'), os.path.join(DOCS, 'icon.png'))
    template = open(os.path.join(ROOT, 'tools', 'page_template.html'), encoding='utf-8').read()
    page = (template.replace('{{REPO_ZIP}}', repo_zip).replace('{{APP_ZIP}}', app_zip)
            .replace('{{APP_VERSION}}', versions['script.maxstream']).replace('{{PAGE_URL}}', PAGE_URL)
            .replace('{{DONATE_URL}}', DONATE_URL))
    with open(os.path.join(DOCS, 'index.html'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(page)
    open(os.path.join(DOCS, '.nojekyll'), 'w').close()
    print('repository built:', versions)


if __name__ == '__main__':
    main()
