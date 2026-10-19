# -*- coding: utf-8 -*-
"""Donation dialog: QR code + link to open in a browser when the device has one."""
import os
import webbrowser

import xbmc
import xbmcgui

from ..common import DONATE_URL, L, log_error, notify
from .base import BACK_ACTIONS, create

OPEN, CLOSE = 301, 302


def open_browser(url):
    try:
        if xbmc.getCondVisibility('System.Platform.Android'):
            xbmc.executebuiltin('StartAndroidActivity(,android.intent.action.VIEW,,%s)' % url)
            return True
        if xbmc.getCondVisibility('System.Platform.Windows'):
            os.startfile(url)  # pylint: disable=no-member
            return True
        return webbrowser.open(url)
    except Exception as err:  # pylint: disable=broad-except
        log_error('browser: %r' % err)
        return False


class DonateDialog(xbmcgui.WindowXMLDialog):
    XML = 'script-maxstream-donate.xml'

    def onAction(self, action):  # pylint: disable=invalid-name
        if action.getId() in BACK_ACTIONS:
            self.close()

    def onClick(self, control_id):  # pylint: disable=invalid-name
        if control_id == OPEN:
            if not open_browser(DONATE_URL):
                notify(L(30634))
        elif control_id == CLOSE:
            self.close()


def show_donate(_params=None):
    dialog = create(DonateDialog)
    dialog.doModal()
    del dialog
