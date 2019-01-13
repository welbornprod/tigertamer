#!/usr/bin/env python3

""" common.py
    Common classes/utilities for Tiger Tamer GUI.
    -Christopher Welborn 01-05-2019
"""

import tkinter as tk
from tkinter import ttk  # noqa (stored here for cleaner API)
from tkinter import filedialog  # noqa
from tkinter import messagebox

from ..util.logger import (
    debug,
    print_err,
)
from ..util.config import NAME


def create_event_handler(func):
    def anon_event_handler(event):
        eventkey = first_available(
            event.keysym,
            event.char,
            event.keycode,
            event.type,
            default='<unknown event code>',
        )
        ignored = {
            ttk.Entry: ('c', 'v', 'x'),
        }
        for widgettype, keys in ignored.items():
            if isinstance(event.widget, widgettype) and (eventkey in keys):
                debug('Ignoring event for Entry: {!r}'.format(eventkey))
                return None
        debug('Handling event: {!r} in {!r}, with: {!r}'.format(
            eventkey,
            type(event.widget).__name__,
            func.__name__,
        ))
        return func()
    return anon_event_handler


def first_available(*args, default=None):
    """ Return the first truthy argument given, or `default` if none is found.
    """
    for arg in args:
        if arg:
            return arg
    return default


class TkErrorLogger(object):
    """ Wrapper for tk calls, to log error messages. """
    def __init__(self, func, subst, widget):
        self.func = func
        self.subst = subst
        self.widget = widget

    def __call__(self, *args):
        try:
            if self.subst:
                args = self.subst(*args)
            return self.func(*args)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            # Log the message, and show an error dialog.
            print_err('GUI Error: ({})'.format(type(ex).__name__))
            messagebox.showerror(
                title='{} - Error'.format(NAME),
                message=str(ex),
            )
            raise


# Use TkErrorLogger
tk.CallWrapper = TkErrorLogger
