#!/usr/bin/env python3

""" viewer.py
    Tiger Viewer window for Tiger Tamer GUI.
    -Christopher Welborn 02-25-2019
"""

from .common import (
    create_event_handler,
    handle_cb,
    tk,
    ttk,
)

from ..util.config import (
    AUTHOR,
    ICONFILE,
    NAME,
    VERSION,
    config_save,
    get_system_info,
)
from ..util.logger import (
    debug,
    debug_err,
    debug_obj,
)


class WinViewer(tk.Toplevel):
    def __init__(self, *args, **kwargs):
        # Don't send kwargs to Toplevel().
        try:
            self.config_gui = kwargs.pop('config_gui')
            self.destroy_cb = kwargs.pop('destroy_cb')
        except KeyError as ex:
            raise TypeError('Missing required kwarg: {}'.format(ex))
        super().__init__(*args, **kwargs)

        # Initialize this window.
        self.title('{} - Viewer'.format(NAME))
        self.geometry(self.config_gui.get('geometry_viewer', '554x141'))
        # About window should stay above the main window.
        self.attributes('-topmost', 1)
        # Hotkey and Menu information for this window, programmatically setup.
        # They are first sorted by label, and then by 'order' (if available).
        hotkeys = {
            'file': {
                'Open': {
                    'char': 'O',
                    'func': self.cmd_btn_open,
                    'order': 0,
                },
                '-': {'order': 1},
                'Exit': {
                    'char': 'x',
                    'func': self.cmd_btn_exit,
                    'order': 2,
                },
            },
            'btns': {
                'Open': {
                    'char': 'O',
                    'func': self.cmd_btn_open,
                },
                'Exit': {
                    'char': 'x',
                    'func': self.cmd_btn_exit,
                },
            },
        }

        # Build Main menu.
        self.menu_main = tk.Menu(self)
        # Build Admin menu.
        self.menu_file = tk.Menu(self.menu_main, tearoff=0)
        filesortkey = lambda k: hotkeys['file'][k].get('order', 99)  # noqa
        for lbl in sorted(sorted(hotkeys['file']), key=filesortkey):
            if lbl == '-':
                self.menu_file.add_separator()
                continue
            fileinfo = hotkeys['file'][lbl]

            self.menu_file.add_command(
                label=lbl,
                underline=lbl.index(fileinfo['char']),
                command=fileinfo['func'],
                accelerator='Ctrl+{}'.format(fileinfo['char'].upper()),
            )

            self.bind_all(
                '<Control-{}>'.format(fileinfo['char'].lower()),
                create_event_handler(fileinfo['func'])
            )
        self.menu_main.add_cascade(
            label='File',
            menu=self.menu_file,
            underline=0,
        )
        # Set main menu to root window.
        self.config(menu=self.menu_main)

        # Make the main frame expand.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        # Main frame.
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.grid(row=0, column=0, sticky=tk.NSEW)
        for x in range(1):
            self.frm_main.columnconfigure(x, weight=1)

        # Columns for file view frame.
        self.columns = ('index', 'width', 'length', 'part', 'no', 'note')
        # Column settings for file view frame.
        self.column_info = {
            'index': {'minwidth': 60, 'width': 60},
            'width': {'minwidth': 60, 'width': 60},
            'length': {'minwidth': 70, 'width': 70},
            'part': {'minwidth': 60, 'width': 60},
            'no': {'minwidth': 60, 'width': 100},
            'note': {'minwidth': 60, 'width': 80},
        }
        # Build file view frame
        self.frm_view = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_view.pack(fill=tk.X, expand=True)
        self.tree_view = ttk.Treeview(
            self.frm_view,
            selectmode='none',
            height=15,
        )
        self.tree_view.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tree_view.configure(
            columns=self.columns,
            show='headings',
        )
        for colname in self.columns:
            self.tree_view.column(colname, **self.column_info[colname])
            self.tree_view.heading(
                colname,
                anchor='w',
                text=' {}:'.format(colname.title()),
            )

        self.scroll_view = ttk.Scrollbar(
            self.frm_view,
            orient='vertical',
            command=self.tree_view.yview,
        )
        self.tree_view.configure(
            yscrollcommand=self.scroll_view.set
        )
        self.scroll_view.pack(side=tk.RIGHT, fill=tk.Y, expand=False)

        # Build Open/Exit buttons frame
        self.frm_cmds = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
            borderwidth=2,
        )
        self.frm_cmds.pack(fill=tk.BOTH, expand=True)
        # Open button
        openlbl = 'Open'
        openinfo = hotkeys['btns'][openlbl]
        self.btn_open = ttk.Button(
            self.frm_cmds,
            text=openlbl,
            underline=openlbl.index(openinfo['char']),
            width=4,
            command=openinfo['func'],
        )
        self.btn_open.pack(
            side=tk.LEFT,
            fill=tk.NONE,
            expand=False,
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )
        # Set focus to the Open button
        self.btn_open.focus_set()

        # Exit button
        exitlbl = 'Exit'
        exitinfo = hotkeys['btns'][exitlbl]
        self.btn_exit = ttk.Button(
            self.frm_cmds,
            text=exitlbl,
            underline=exitlbl.index(exitinfo['char']),
            width=4,
            command=exitinfo['func'],
        )
        self.btn_exit.pack(
            side=tk.RIGHT,
            fill=tk.NONE,
            expand=False,
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )

        # Bind hotkeys for buttons.
        for btninfo in hotkeys['btns'].values():
            self.bind_all(
                '<Control-{}>'.format(btninfo['char'].lower()),
                create_event_handler(btninfo['func']),
            )

    def cmd_btn_exit(self):
        return self.destroy()

    def cmd_btn_open(self):
        return

    def destroy(self):
        debug('Saving gui-viewer config...')
        self.config_gui['geometry_viewer'] = self.geometry()
        config_save(self.config_gui)
        debug('Closing viewer window (geometry={!r}).'.format(
            self.config_gui['geometry_viewer']
        ))
        self.attributes('-topmost', 0)
        self.withdraw()
        super().destroy()
        debug('Calling destroy_cb({})...'.format(self.destroy_cb))
        handle_cb(self.destroy_cb)
