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
    show_question,
    tk,
    trim_file_path,
    ttk,
    WinToplevelBase,
)

from ..util.config import (
    NAME,
    config_save,
)
from ..util.format import (
    TigerFile,
)
from ..util.logger import (
    debug,
)
from ..util.preview import (
    LargeFileError,
    TigerFiles,
    check_file,
)


class WinViewer(WinToplevelBase):
    def __init__(
            self, *args,
            settings, destroy_cb, dat_dir, tiger_dir,
            filepaths=None, preview_files=None,
            **kwargs):
        self.settings = settings
        self.destroy_cb = destroy_cb
        self.dat_dir = dat_dir
        self.tiger_dir = tiger_dir
        # The `filepaths` arg is handled at the end of __init__.
        self.filepaths = []
        super().__init__(*args, **kwargs)
        self.debug_settings()

        # Initialize this window.
        self.default_title = '{} - Viewer'.format(NAME)
        self.title(self.default_title)
        self.geometry(
            self.settings.get('geometry_viewer', None) or '554x141'
        )
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
                'Close': {
                    'char': 'C',
                    'func': self.cmd_btn_close,
                    'order': 1,
                },
                '-': {'order': 2},
                'Preview Mozaik File': {
                    'char': 'P',
                    'func': self.cmd_btn_preview,
                    'order': 3,
                },
                '--': {'order': 4},
                'Exit': {
                    'char': 'x',
                    'func': self.cmd_btn_exit,
                    'order': 5,
                },
            },
            'btns': {
                'Open': {
                    'char': 'O',
                    'func': self.cmd_btn_open,
                },
                'Close': {
                    'char': 'C',
                    'func': self.cmd_btn_close,
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
            if lbl.startswith('-'):
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

        # Build Notebook.
        self.notebook = ttk.Notebook(self.frm_main)
        self.notebook.pack(
            fill=tk.BOTH,
            expand=True,
        )
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
            'index': {'minwidth': 60, 'width': 60, 'anchor': tk.E},
            'quantity': {'minwidth': 80, 'width': 80, 'anchor': tk.E},
            'completed': {'minwidth': 100, 'width': 100, 'anchor': tk.E},
            'length': {'minwidth': 70, 'width': 70, 'anchor': tk.E},
            'part': {'minwidth': 60, 'width': 60, 'anchor': tk.CENTER},
            'no': {'minwidth': 60, 'width': 60, 'anchor': tk.W},
            'note': {'minwidth': 60, 'width': 60, 'anchor': tk.W},
        }
        # References to LabelFrames/Treeviews for each file, for removing.
        # These are set in `self.build_tab()`.
        self.lbl_views = []
        self.tree_views = []

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

        # Close button
        closelbl = 'Close'
        closeinfo = hotkeys['btns'][closelbl]
        self.btn_close = ttk.Button(
            self.frm_cmds,
            text=closelbl,
            underline=closelbl.index(closeinfo['char']),
            width=5,
            command=closeinfo['func'],
        )
        self.btn_close.pack(
            side=tk.LEFT,
            fill=tk.NONE,
            expand=False,
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )
        self.enable_close(False)

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
        # Build default tab.
        self.build_tab()
        # Open file passed in with kwargs?
        if filepaths:
            self.after_idle(self.cmd_btn_open, filepaths)
        elif preview_files:
            self.after_idle(self.preview_files, preview_files)

    def build_tab(self, filepath=None):
        frm_view = ttk.Frame(
            master=self.notebook,
            padding='2 2 2 2',
        )
        frm_view.pack(fill=tk.BOTH, expand=True)
        frm_tree = ttk.Frame(
            master=frm_view,
            padding='2 2 2 2',
        )
        frm_tree.pack(
            side=tk.TOP,
            fill=tk.BOTH,
            expand=True,
        )
        tree_view = ttk.Treeview(
            frm_tree,
            selectmode='browse',
            height=15,
        )
        tree_view.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_view.configure(
            columns=self.columns,
            show='headings',
        )
        for colname in self.columns:
            tree_view.column(colname, **self.column_info[colname])
            tree_view.heading(
                colname,
                anchor=tk.CENTER,
                text='{}:'.format(colname.title()),
            )

        scroll_view = ttk.Scrollbar(
            frm_tree,
            orient='vertical',
            command=tree_view.yview,
        )
        tree_view.configure(
            yscrollcommand=scroll_view.set
        )
        scroll_view.pack(
            side=tk.RIGHT,
            fill=tk.Y,
            expand=False,
        )
        tree_view.tag_configure(
            'odd',
            background='#FFFFFF',
            font='Arial 10',
        )
        tree_view.tag_configure(
            'even',
            background='#DADADA',
            font='Arial 10',
        )
        tree_view.tag_configure(
            'odd_completed',
            background='#CCFFCC',
            font='Arial 10',
        )
        tree_view.tag_configure(
            'even_completed',
            background='#AAFFAA',
            font='Arial 10',
        )
        lbl_view = ttk.Label(
            master=frm_view,
            foreground='#6C6C6C',
            text=filepath,
        )
        lbl_view.pack(
            side=tk.BOTTOM,
            fill=tk.X,
            expand=True,
            padx=2,
            pady=2,
        )

        # Save references to these, for modifying/removing.
        self.lbl_views.append(lbl_view)
        self.tree_views.append(tree_view)

        if filepath:
            # Use short file name for tab text.
            fname = os.path.split(filepath)[-1]
            text = os.path.splitext(fname)[0]
        else:
            text = None
        self.notebook.add(frm_view, text=text or 'No File')
        debug('Added a new tab for: {}'.format(text or 'Unknown'))
        return tree_view

    def clear_tabs(self, tabids=None):
        """ Clear a list of tabs, or ALL tabs if none are specified. """
        if not tabids:
            tabids = self.notebook.tabs()
        for tabid in tabids:
            self.remove_tab(tabid)

    def clear_treeview(self, index):
        self.tree_views[index].delete(*self.tree_views[index].get_children())

    def cmd_btn_close(self):
        """ Close the currently selected tab. """
        if not self.filepaths:
            self.show_error('No files to close.')
            return
        currentid = self.notebook.select()
        self.remove_tab(currentid)
        debug('Removed tab: {}'.format(currentid))

    def cmd_btn_exit(self):
        return self.destroy()

    def cmd_btn_open(self, filepaths=None):
        """ Pick a file with a Tk file dialog, and open it. """
        filepaths = filepaths or self.dialog_files(
            initialdir=self.tiger_dir,
            filetypes=(('Tiger Files', '*.tiger'), ),
        )
        if not filepaths:
            return
        for filepath in filepaths:
            if not os.path.exists(filepath):
                self.show_error('File does not exist:\n{}'.format(filepath))
                return
            try:
                existingindex = self.filepaths.index(filepath)
            except ValueError:
                pass
            else:
                # Remove the existing tab to reload this file.
                self.remove_tab(existingindex)

        return self.view_files(filepaths)

    def cmd_btn_preview(self):
        filepaths = self.dialog_files(
            initialdir=self.dat_dir,
            filetypes=(('Mozaik Files', '*.dat'), ),
        )
        if not filepaths:
            return
        return self.preview_files(filepaths)

    def destroy(self):
        debug('Saving gui-viewer config...')
        self.settings['geometry_viewer'] = self.geometry()
        config_save(self.settings)
        debug('Closing viewer window (geometry={!r}).'.format(
            self.settings['geometry_viewer']
        ))
        self.attributes('-topmost', 0)
        self.withdraw()
        super().destroy()
        debug('Calling destroy_cb({})...'.format(self.destroy_cb))
        handle_cb(self.destroy_cb)

    def dialog_files(self, initialdir=None, filetypes=None):
        """ Use tk.filedialog.askopenfiles(), and return the result. """
        self.attributes('-topmost', 0)
        self.withdraw()
        filepaths = filedialog.askopenfilenames(
            initialdir=initialdir,
            filetypes=filetypes,
        )
        self.attributes('-topmost', 1)
        self.deiconify()
        return filepaths

    def enable_close(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.btn_close.configure(state=state)
        self.menu_file.entryconfigure('Close', state=state)

    def enable_interface(self, enabled=True):
        """ Enable/Disable the user interface (while running,
            or after running).
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        widgets = (
            self.btn_open,
        )
        for widget in widgets:
            widget.configure(state=state)

        # Main menus.
        menus = (
            'File',
        )
        for name in menus:
            self.menu_main.entryconfigure(name, state=state)

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

    def preview_files(self, filepaths):
        """ Preview Mozaik files (.dat), selected with `cmd_btn_preview`, or
            passed in through `self.__init__(preview_files=..)`.
        """
        if not filepaths:
            return
        # Clear all tabs.
        self.clear_tabs()

        for filepath in filepaths:
            try:
                check_file(filepath)
            except FileNotFoundError:
                self.show_error('File does not exist:\n{}'.format(filepath))
                return
            except LargeFileError as ex:
                msg = '\n'.join((
                    'File is large: ({} bytes)'.format(ex.size),
                    trim_file_path(ex.filepath),
                    '',
                    'This may take a minute, continue?'
                ))
                if not self.show_question(msg):
                    return
            # TODO: Show a 'busy' window while working on the parts,
            #       and use the callback from view_masterfiles to remove it.
            for tigerfile in TigerFiles.from_file(filepath, split_parts=True):
                self.view_tigerfile(tigerfile)

    def remove_tab(self, tabid):
        """ Remove a tab and it's associated file name. """
        try:
            tabid = int(tabid)
        except ValueError:
            # Tab id str.
            tabid = self.notebook.index(tabid)
        if tabid == 0 and not self.filepaths:
            # Can't remove the default tab.
            debug('Not removing the default tab.')
            return
        # Normal index
        self.notebook.forget(tabid)
        self.filepaths.pop(tabid)
        self.lbl_views.pop(tabid)
        self.tree_views.pop(tabid)
        if not self.filepaths:
            # Rebuild the default tab.
            self.build_tab()
            self.enable_close(False)

    def show_question(self, msg, title=None):
        """ Use show_question, but make sure this window is out of the way.
        """
        self.attributes('-topmost', 0)
        self.withdraw()
        ret = show_question(msg, title=title)
        self.attributes('-topmost', 1)
        self.deiconify()
        return ret

    def view_files(self, filepaths):
        for filepath in filepaths:
            self.view_tigerfile(TigerFile.from_file(filepath))

    def view_tigerfile(self, tigerfile):
        """ Load TigerFile instance parts into a new tab. """
        if self.filepaths:
            # Adding another file.
            tree_view = self.build_tab(filepath=tigerfile.filepath)
        else:
            # Using the default (empty) tree_view.
            tree_view = self.tree_views[0]
            lbl_view = self.lbl_views[0]
            lbl_view.configure(text=tigerfile.filepath)
            fname = os.path.split(tigerfile.filepath)[-1]
            fname = os.path.splitext(fname)[0]
            self.notebook.tab(0, text=fname)

        self.filepaths.append(tigerfile.filepath)

        for i, part in enumerate(tigerfile.parts):
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
            tree_view.insert(
                '',
                tk.END,
                values=tuple(
                    self.format_value(self.columns[i], v)
                    for i, v in enumerate(values)
                ),
                text='',
                tag=tag,
            )
        self.notebook.select(self.notebook.tabs()[-1])
        self.enable_close(True)
