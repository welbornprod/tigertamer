#!/usr/bin/env python3

""" common.py
    Common classes/utilities for Tiger Tamer GUI.
    -Christopher Welborn 01-05-2019
"""

import os
import tkinter as tk
from tkinter import ttk  # noqa (stored here for cleaner API)
from tkinter import filedialog  # noqa
from tkinter import messagebox

from ..util.logger import (
    debug,
    debug_exc,
    print_err,
)
from ..util.config import (
    NAME,
    lock_release,
)


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


def handle_cb(callback):
    """ Accepts a function, or a list of functions to call. """
    if not callback:
        return None
    if isinstance(callback, (list, tuple)):
        val = None
        for func in callback:
            val = func()
        return val
    # Single callback func.
    return callback()


def show_done_msg(msg, errors=0):
    """ Shows either a success or error dialog, based on whether `errors` is
        non-zero.
    """
    titletype = 'Success'
    if errors:
        titletype = '{} {}'.format(
            errors,
            'Error' if errors == 1 else 'Errors',
        )
    title = '{} - {}'.format(NAME, titletype)
    if errors:
        messagebox.showerror(title=title, message=msg)
    else:
        messagebox.showinfo(title=title, message=msg)


def show_error(msg):
    """ Show a tkinter error dialog. """
    title = '{} - Error'.format(NAME)
    messagebox.showerror(title=title, message=str(msg))


def show_question(msg, title=None):
    """ Show a tkinter askyesno dialog. """
    title = '{} - {}'.format(NAME, title or 'Confirm')
    return messagebox.askyesno(title=title, message=str(msg))


def trim_file_path(filepath):
    """ Trim most of the directories off of a file path.
        Leaves only the file name, and one sub directory.
    """
    path, fname = os.path.split(filepath)
    _, subdir = os.path.split(path)
    return os.path.join(subdir, fname)


def validate_dirs(dat_dir='', tiger_dir='', arch_dir='', ignore_dirs=None):
    """ Returns True if all directories are set, and valid.
        Shows an error message if any of them are not.
    """
    dirs = (
        ('Mozaik (.dat)', dat_dir),
        ('Tiger (.tiger)', tiger_dir),
        ('Archive', arch_dir),
    )
    for name, dirpath in dirs:
        s = name.split()[0].lower()
        if (not dirpath) and ignore_dirs:
            debug('Is empty allowed?: {} in? {!r}'.format(s, ignore_dirs))
            if s in ignore_dirs:
                # Allow empty archive dir or any other named dirs.
                debug('Empty directory is okay: {}'.format(s))
                continue
        if dirpath and (os.path.exists(dirpath)):
            continue
        # Invalid dir?
        debug('Is invalid allowed?: {}'.format(s))
        if s in ignore_dirs:
            debug('Invalid is okay: {}'.format(s))
            continue
        msg = 'Invalid {} directory: {}'.format(
            name,
            dirpath if dirpath else '<not set>',
        )
        print_err(msg)
        show_error(msg)
        return False
    return True


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
            debug_exc()
            messagebox.showerror(
                title='{} - Error'.format(NAME),
                message=str(ex),
            )
            raise


# Use TkErrorLogger
tk.CallWrapper = TkErrorLogger
