# -*- coding: utf-8 -*-
"""Script entry: no argument opens the interface; action=<name> runs a settings action."""
from .common import log_error


def run(argv):
    params = dict(arg.split('=', 1) for arg in argv[1:] if '=' in arg)
    action = params.get('action')
    if action:
        from .actions import ACTIONS
        handler = ACTIONS.get(action)
        if handler is None:
            log_error('unknown action %s' % action)
            return
        handler(params)
        return
    from .gui import open_home
    open_home()
