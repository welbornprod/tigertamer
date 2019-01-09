#!/usr/bin/env python3

""" common.py
    Common classes/utilities for Tiger Tamer GUI.
    -Christopher Welborn 01-05-2019
"""

import tkinter as tk
from tkinter import ttk  # noqa (stored here for cleaner API)
from tkinter import filedialog  # noqa
from tkinter import messagebox

from ..util.logger import print_err
from ..util.config import NAME


class TkErrorLogger(object):
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
