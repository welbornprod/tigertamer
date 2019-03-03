#!/usr/bin/env python3

""" viewer.py
    Tiger Viewer window for Tiger Tamer GUI.
    -Christopher Welborn 02-25-2019
"""
import os

from .common import (
    create_event_handler,
    filedialog,
    handle_cb,
    show_error,
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
from ..util.format import (
    TigerFile,
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
        try:
            # Required, but may be None values.
            self.filename = kwargs.pop('filename')
        except KeyError as ex:
            raise TypeError('Missing required kwarg, may be None: {}'.format(
                ex
            ))
        super().__init__(*args, **kwargs)

        # Initialize this window.
        self.default_title = '{} - Viewer'.format(NAME)
        self.title(self.default_title)
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
        self.columns = (
            'index',
            'quantity',
            'completed',
            'length',
            'part',
            'no',
            'note',
        )
        # Column settings for file view frame.
        self.column_info = {
            'index': {'minwidth': 60, 'width': 60},
            'quantity': {'minwidth': 80, 'width': 80},
            'completed': {'minwidth': 100, 'width': 100},
            'length': {'minwidth': 70, 'width': 70},
            'part': {'minwidth': 60, 'width': 60},
            'no': {'minwidth': 60, 'width': 60},
            'note': {'minwidth': 60, 'width': 60},
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
        self.tree_view.tag_configure(
            'odd',
            background='#FFFFFF',
            font='Arial 10',
        )
        self.tree_view.tag_configure(
            'even',
            background='#DADADA',
            font='Arial 10',
        )
        self.tree_view.tag_configure(
            'odd_completed',
            background='#CCFFCC',
            font='Arial 10',
        )
        self.tree_view.tag_configure(
            'even_completed',
            background='#AAFFAA',
            font='Arial 10',
        )
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
        # Open file passed in with kwargs?
        if self.filename:
            self.view_file(self.filename)

    def cmd_btn_exit(self):
        return self.destroy()

    def cmd_btn_open(self):
        """ Pick a file with a Tk file dialog, and open it. """
        self.attributes('-topmost', 0)
        self.withdraw()
        filename = filedialog.askopenfilename()
        self.attributes('-topmost', 1)
        self.deiconify()
        if not filename:
            return
        if not os.path.exists(filename):
            show_error('File does not exist:\n{}'.format(filename))
            return

        return self.view_file(filename)

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

    def format_value(self, column, value):
        """ Format a value for the tree_view, with decent default values. """
        defaults = {
            'index': 0,
            'quantity': 0,
            'completed': 0,
            'length': 0,
            'part': '?',
            'no': '?',
            'note': '',
        }
        value = value or defaults[column]
        if column.lower() == 'length':
            value = '{:0.2f}'.format(float(value))
        return str(value)

    def view_file(self, filename):
        """ Load file contents into tree_view. """
        self.tree_view.delete(*self.tree_view.get_children())
        self.filename = filename
        tf = TigerFile.from_file(filename)
        for i, part in enumerate(tf.parts):
            # Get raw part values.
            values = [
                getattr(part, colname, None)
                for colname in self.columns
            ]
            quantity = values[1]
            completed = values[2]
            remaining = quantity - completed
            tag = 'odd' if i % 2 else 'even'
            tag = '{}{}'.format(tag, '' if remaining else '_completed')
            # Insert formatted values:
            self.tree_view.insert(
                '',
                tk.END,
                values=tuple(
                    self.format_value(self.columns[i], v)
                    for i, v in enumerate(values)
                ),
                text='',
                tag=tag,
            )
        self.title('{}: {}'.format(self.default_title, self.filename))
