#!/usr/bin/env python3

""" report.py
    Report window for Tiger Tamer GUI.
    -Christopher Welborn 01-05-2019
"""

from contextlib import suppress

from ..util.config import (
    NAME,
    config_save,
)
from ..util.logger import debug

from .common import (
    handle_cb,
    tk,
    ttk,
)


class WinReport(tk.Toplevel):
    def __init__(self, *args, **kwargs):
        try:
            self.config_gui = kwargs.pop('config_gui')
            self.destroy_cb = kwargs.pop('destroy_cb')
            self.theme = kwargs.pop('theme')
            self.title_msg = kwargs.pop('title_msg')
            # List of 'master files'
            self.parent_files = kwargs.pop('parent_files')
            # List of (tigerpath, 'message')
            self.error_files = kwargs.pop('error_files')
            # List of (tigerpath, )
            self.success_files = kwargs.pop('success_files')
        except KeyError as ex:
            raise TypeError('Missing required kwarg: {}'.format(ex))

        self.parent_name = kwargs.get('parent_name', 'Master')
        with suppress(KeyError):
            kwargs.pop('parent_name')
        self.success_name = kwargs.get('success_name', 'Tiger')
        with suppress(KeyError):
            kwargs.pop('success_name')

        super().__init__(*args, **kwargs)

        # Report window should stay above the main window.
        self.attributes('-topmost', 1)

        self.parent_len = len(self.parent_files)
        self.error_len = len(self.error_files)
        self.success_len = len(self.success_files)

        self.title('{} - {}'.format(NAME, self.title_msg))
        self.geometry(self.config_gui.get('geometry_report', '331x301'))
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.pack(fill=tk.BOTH, expand=True)

        # Build parent files frame
        self.frm_parent = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_parent.pack(fill=tk.X, expand=True)
        self.tree_parent = ttk.Treeview(
            self.frm_parent,
            selectmode='none',
            height=3,
        )
        self.tree_parent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tree_parent.configure(columns=('file', ), show='headings')
        self.tree_parent.heading(
            'file',
            anchor='w',
            text=' {} Files: {}'.format(
                self.parent_name,
                self.parent_len,
            ),
        )
        self.tree_parent.tag_configure('parent', foreground='#000068')
        self.scroll_parent = ttk.Scrollbar(
            self.frm_parent,
            orient='vertical',
            command=self.tree_parent.yview,
        )
        self.tree_parent.configure(
            yscrollcommand=self.scroll_parent.set
        )
        self.scroll_parent.pack(side=tk.RIGHT, fill=tk.Y, expand=False)

        # Build error files frame
        self.frm_error = ttk.Frame(
            self.frm_main,
            # text='Errors ({}):'.format(self.error_len),
            padding='2 2 2 2',
        )
        self.frm_error.pack(fill=tk.X, expand=True)
        self.tree_error = ttk.Treeview(
            self.frm_error,
            selectmode='none',
            height=5,
        )
        self.tree_error.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tree_error.configure(
            columns=('file', 'message'),
            show='headings',
        )
        self.tree_error.heading(
            'file',
            anchor='w',
            text=' Error Files: {}'.format(self.error_len),
        )
        self.tree_error.heading(
            'message',
            anchor='w',
            text=' Message',
        )
        self.tree_error.tag_configure('error', foreground='#b10000')
        self.scroll_error = ttk.Scrollbar(
            self.frm_error,
            orient='vertical',
            command=self.tree_error.yview,
        )
        self.tree_error.configure(
            yscrollcommand=self.scroll_error.set
        )
        self.scroll_error.pack(side=tk.RIGHT, fill=tk.Y, expand=False)

        # Build success files frame
        self.frm_success = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_success.pack(fill=tk.X, expand=True)
        self.tree_success = ttk.Treeview(
            self.frm_success,
            selectmode='none',
            height=10,
        )

        self.tree_success.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tree_success.configure(columns=('file', ), show='headings')
        self.tree_success.heading(
            'file',
            anchor='w',
            text=' {} Files: {}'.format(
                self.success_name,
                self.success_len,
            ),
        )
        self.tree_success.tag_configure('success', foreground='#007000')
        self.scroll_success = ttk.Scrollbar(
            self.frm_success,
            orient='vertical',
            command=self.tree_success.yview,
        )
        self.tree_success.configure(
            yscrollcommand=self.scroll_success.set
        )
        self.scroll_success.pack(side=tk.RIGHT, fill=tk.Y, expand=False)

        # Build cmds frame.
        self.frm_cmds = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_cmds.pack(fill=tk.X, expand=True)

        self.btn_ok = ttk.Button(
            self.frm_cmds,
            text='Okay',
            underline=0,
            width=4,
            command=self.cmd_btn_ok,
        )
        self.btn_ok.pack(
            side=tk.RIGHT,
            fill=tk.NONE,
            expand=False,
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )
        self.btn_ok.focus_set()
        self.bind_all(
            'o',
            lambda event: self.cmd_btn_ok()
        )
        # Fill tree views.
        self.build_trees()

    def build_trees(self):
        """ Build/fill tree views from file names, errors, and messages. """
        for parentfile in self.parent_files:
            self.tree_parent.insert(
                '',
                tk.END,
                values=(parentfile, ),
                text='{} File'.format(self.parent_name or 'Master'),
                tag='parent',
            )

        for errfile, msg in self.error_files:
            self.tree_error.insert(
                '',
                tk.END,
                values=(errfile, msg),
                text='Errors',
                tag='error',
            )

        for tigerpath in self.success_files:
            self.tree_success.insert(
                '',
                tk.END,
                values=(tigerpath, ),
                text='{} File'.format(self.success_name or 'Tiger'),
                tag='success',
            )

    def cmd_btn_ok(self):
        """ Handles btn_okay click. """
        self.destroy()

    def destroy(self):
        debug('Saving gui-report config...')
        self.config_gui['geometry_report'] = self.geometry()
        config_save(self.config_gui)
        # Remove topmost, and hide this report, in case any callbacks want
        # to show a dialog.
        debug('Closing report window (geometry={!r}).'.format(
            self.config_gui['geometry_report'],
        ))
        self.attributes('-topmost', 0)
        self.withdraw()
        self.update()
        super().destroy()
        debug('Calling destroy_cb({})...'.format(self.destroy_cb))
        handle_cb(self.destroy_cb)
