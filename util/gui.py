#!/usr/bin/env python3

""" tigertamer - util/gui.py
    Handles the GUI for TigerTamer.
    -Christopher Welborn 12-22-2018
"""

import os

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox

from .config import (
    config_save,
    ICONFILE,
    NAME,
)
from .logger import (
    debug,
    debug_err,
    debug_obj,
    print_err,
)
from .parser import (
    load_moz_files,
    write_tiger_file,
)


class WinMain(tk.Tk):
    default_theme = 'clam'

    def __init__(self, *args, **kwargs):
        self.config_gui = {k: v for k, v in kwargs.items()}
        # Don't send WinMain kwargs to Tk.
        for key in self.config_gui:
            kwargs.pop(key)
        super().__init__(*args, **kwargs)
        # Set icon for main window and all children.
        try:
            self.main_icon = tk.PhotoImage(master=self, file=ICONFILE)
            self.iconphoto(True, self.main_icon)
        except Exception as ex:
            print_err('Failed to set icon: {}\n{}'.format(ICONFILE, ex))
            self.main_icon = None

        debug_obj(self.config_gui, msg='Using GUI config:')

        self.title('Tiger Tamer')
        self.geometry(self.config_gui.get('geometry', '331x301'))
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.pack(fill=tk.BOTH, expand='yes')
        self.style = ttk.Style()

        # knownstyles = ('clam', 'alt', 'default', 'classic')
        self.known_themes = sorted(self.style.theme_names())
        usetheme = self.config_gui.get('theme', 'clam').lower()
        if usetheme not in self.known_themes:
            debug_err('Invalid theme name: {}'.format(usetheme))
            debug_err('Using {!r}'.format(self.default_theme))
            debug('Known themes: {}'.format(', '.join(self.known_themes)))
            usetheme = self.default_theme
        self.style.theme_use(usetheme)
        self.theme = usetheme

        # Build directory choosers.
        self.build_dir_frame('dat', 'Mozaik', 'dat_dir')
        self.build_dir_frame('tiger', 'Tiger', 'tiger_dir')
        self.build_dir_frame('arch', 'Archive', 'archive_dir')

        # Build options frame
        self.frm_opts_main = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
            borderwidth=2,
        )
        self.frm_opts_main.pack(fill=tk.X, expand='yes')

        # Build theme options.
        self.frm_theme = ttk.LabelFrame(
            self.frm_opts_main,
            text='Theme:',
            padding='2 2 2 2',
        )
        self.frm_theme.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand='yes',
            padx=1,
        )
        self.cmb_theme = ttk.Combobox(
            self.frm_theme,
            state='readonly',
            values=self.known_themes,
        )
        self.cmb_theme.pack(side=tk.LEFT, fill=tk.X, expand='yes')
        self.cmb_theme.current(self.known_themes.index(usetheme))
        self.cmb_theme.bind(
            '<<ComboboxSelected>>',
            self.event_cmb_theme_select,
        )
        # Build checkboxes
        self.frm_opts = ttk.LabelFrame(
            self.frm_opts_main,
            text='Options:',
            padding='2 2 2 2',
        )
        self.frm_opts.pack(
            side=tk.RIGHT,
            fill=tk.X,
            expand='yes',
            padx=1,
        )
        self.var_auto_exit = tk.BooleanVar()
        self.var_auto_exit.set(self.config_gui.get('auto_exit', False))
        self.chk_auto_exit = ttk.Checkbutton(
            self.frm_opts,
            text='Exit after report',
            onvalue=True,
            offvalue=False,
            variable=self.var_auto_exit,
        )
        self.chk_auto_exit.pack(
            side=tk.RIGHT,
            expand='no',
        )
        # Build Run/Exit buttons frame
        self.frm_cmds = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
            borderwidth=2,
        )
        self.frm_cmds.pack(fill=tk.BOTH, expand='yes')
        # Run button
        self.btn_run = ttk.Button(
            self.frm_cmds,
            text='Run',
            width=4,
            command=self.cmd_btn_run,
        )
        self.btn_run.pack(
            side=tk.LEFT,
            fill=tk.NONE,
            expand='no',
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )
        # Set focus to the Run button
        self.btn_run.focus_set()

        # Exit button
        self.btn_exit = ttk.Button(
            self.frm_cmds,
            text='Exit',
            width=4,
            command=self.cmd_btn_exit,
        )
        self.btn_exit.pack(
            side=tk.RIGHT,
            fill=tk.NONE,
            expand='no',
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )

        # A singleton instance for the report window (WinReport)
        self.win_report = None

        # Fix message boxes.
        self.option_add('*Dialog.msg.font', 'Arial 10')

        # Auto run?
        if self.config_gui.get('auto_run', False):
            self.cmd_btn_run()

    def build_dir_frame(self, name, proper_name, config_key):
        """ Build a label frame, entry box, and button for a directory
            chooser with a given name.
            Sets the attributes on `self` that are needed to retrieve these
            widgets, and links the handler function.
        """
        lbl_text = '{} files directory:'.format(proper_name)
        # Build the label frame
        frmname = 'frm_{}'.format(name)
        setattr(
            self,
            frmname,
            ttk.LabelFrame(
                self.frm_main,
                text=lbl_text,
            )
        )
        frm = getattr(self, frmname)
        frm.pack(
            fill=tk.X,
            expand='yes',
            anchor='nw',
            ipadx=4,
            ipady=4,
            pady=4,
        )
        # StringVar and Entry
        varname = 'var_{}'.format(name)
        setattr(self, varname, tk.StringVar())
        var = getattr(self, varname)
        entryname = 'entry_{}'.format(name)
        setattr(
            self,
            entryname,
            ttk.Entry(
                frm,
                textvariable=var,
            )
        )
        entry = getattr(self, entryname)
        configdir = self.config_gui.get(config_key, '')
        if not isinstance(configdir, str):
            # Handle possible lists of directories in `dat_dir`.
            configdir = configdir[0]
        var.set(configdir)
        entry.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand='yes',
            anchor='nw',
            padx=2,
        )
        debug('Set {} dir entry: {}'.format(name, entry.get()))

        # Button
        btnname = 'btn_{}'.format(name)
        cmdname = 'cmd_btn_{}'.format(name)
        cmd = getattr(self, cmdname)
        # Create button font.
        setattr(
            self,
            btnname,
            ttk.Button(
                frm,
                text='^',
                width=1,
                command=cmd,
            )
        )
        btn = getattr(self, btnname)
        btn.pack(
            side=tk.RIGHT,
            fill=tk.NONE,
            expand='no',
            anchor='nw',
            padx=2,
        )

    def cmd_btn_arch(self):
        """ Handles btn_arch click. """
        arch_dir = filedialog.askdirectory()
        if not arch_dir:
            return
        self.var_arch.set(arch_dir)
        self.config_gui['archive_dir'] = arch_dir
        debug('Selected new archive directory: {}'.format(
            self.var_arch.get()
        ))

    def cmd_btn_dat(self):
        """ Handles btn_dat click. """
        dat_dir = filedialog.askdirectory()
        if not dat_dir:
            return
        self.var_dat.set(dat_dir)
        self.config_gui['dat_dir'] = [dat_dir]
        debug('Selected new Mozaik directory: {}'.format(
            self.var_dat.get()
        ))

    def cmd_btn_exit(self):
        """ Handles btn_exit click. """
        self.destroy()

    def cmd_btn_run(self):
        """ Handles btn_run click. """
        if not self.validate_dirs():
            return

        self.enable_interface(False)
        mozdir = self.var_dat.get()
        try:
            mozfiles = load_moz_files(
                filepaths=mozdir,
                ignore_dirs=self.config_gui['ignore_dirs'],
            )
        except OSError as ex:
            self.show_error('Cannot load .dat files in: {}\n{}'.format(
                mozdir,
                ex,
            ))
            self.enable_interface(True)
            return

        if not mozfiles:
            self.show_error('No Mozaik (.dat) files found in: {}'.format(
                mozdir,
            ))
            self.enable_interface(True)
            return

        error_files = []

        def add_error_file(mozfile, msg):
            error_files.append((mozfile, msg))
            return 1

        success_files = []

        def add_success_file(mozfile, tigerpath):
            success_files.append((mozfile, tigerpath))
            return 0

        errs = 0
        for mozfile in mozfiles:
            try:
                errs += write_tiger_file(
                    mozfile,
                    self.entry_tiger.get(),
                    archive_dir=self.entry_arch.get() or '',
                    error_cb=add_error_file,
                    success_cb=add_success_file,
                    )
            except Exception as ex:
                print_err('Error writing tiger file: {}\n{}'.format(
                    mozfile.filename,
                    ex
                ))
                add_error_file(mozfile, ex)
                errs += 1

        parentfiles = set(m.parent_file for m in mozfiles)

        # self.report_closed() will re-enable the interface.
        self.enable_interface(False)
        reportmsg = 'Success'
        if error_files:
            reportmsg = 'Errors: {}'.format(len(error_files))

        self.win_report = WinReport(  # noqa
            title_msg=reportmsg,
            config_gui=self.config_gui,
            theme=self.theme,
            parent_files=[
                self.trim_file_path(s) for s in sorted(parentfiles)
            ],
            error_files=[
                (self.trim_file_path(mozfile.filename), msg)
                for mozfile, msg in sorted(
                    error_files,
                    key=lambda tup: tup[0].filename
                )
            ],
            success_files=[
                (mozfile, tigerpath)
                for mozfile, tigerpath in sorted(
                    success_files,
                    key=lambda tup: tup[1]
                )
            ],
            destroy_cb=self.report_closed,
        )

    def cmd_btn_tiger(self):
        """ Handles btn_tiger click. """
        tiger_dir = filedialog.askdirectory()
        if not tiger_dir:
            return
        self.var_tiger.set(tiger_dir)
        self.config_gui['tiger_dir'] = tiger_dir
        debug('Selected new tiger directory: {}'.format(
            self.var_dat.get()
        ))

    def destroy(self):
        debug('Saving gui config...')
        self.config_gui['dat_dir'] = [self.entry_dat.get()]
        self.config_gui['tiger_dir'] = self.entry_tiger.get()
        self.config_gui['archive_dir'] = self.entry_arch.get()
        self.config_gui['geometry'] = self.geometry()
        self.config_gui['theme'] = self.theme
        self.config_gui['auto_exit'] = self.var_auto_exit.get()
        config_save(self.config_gui)
        debug('Closing main window (geometry={!r}).'.format(self.geometry()))
        super().destroy()

    def enable_interface(self, enabled=True):
        """ Enable/Disable the user interface (while running,
            or after running).
        """
        state = 'enabled' if enabled else 'disabled'
        widgets = (
            self.btn_run,
            self.btn_exit,
            self.entry_dat,
            self.btn_dat,
            self.entry_tiger,
            self.btn_tiger,
            self.entry_arch,
            self.btn_arch,
        )
        for widget in widgets:
            widget['state'] = state

    def event_cmb_theme_select(self, event):
        self.theme = self.known_themes[self.cmb_theme.current()]
        self.style.theme_use(self.theme)
        self.config_gui['theme'] = self.theme

    def report_closed(self):
        """ Called when the report window is closed. """
        self.enable_interface()
        if self.var_auto_exit.get():
            self.destroy()

    def show_error(self, msg):
        """ Show a tkinter error dialog. """
        title = '{} - Error'.format(NAME)
        messagebox.showerror(title=title, message=str(msg))

    def show_done_msg(self, msg, errors=0):
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

    @staticmethod
    def trim_file_path(filepath):
        """ Trim most of the directories off of a file path.
            Leaves only the file name, and one sub directory.
        """
        path, fname = os.path.split(filepath)
        _, subdir = os.path.split(path)
        return os.path.join(subdir, fname)

    def validate_dirs(self):
        """ Returns True if all directories are set, and valid.
            Shows an error message if any of them are not.
        """
        dirs = (
            ('Mozaik (.dat)', self.entry_dat.get()),
            ('Tiger (.tiger)', self.entry_tiger.get()),
            ('Archive', self.entry_arch.get()),
        )
        for name, dirpath in dirs:
            if (name == 'Archive') and (not dirpath):
                # Allow empty archive dir.
                continue
            if dirpath and (os.path.exists(dirpath)):
                continue
            # Invalid dir.
            msg = 'Invalid {} directory: {}'.format(
                name,
                dirpath if dirpath else '<not set>',
            )
            print_err(msg)
            self.show_error(msg)
            return False
        return True


class WinReport(tk.Tk):
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
            # List of (MozaikFile, tigerpath)
            self.success_files = kwargs.pop('success_files')
        except KeyError as ex:
            raise TypeError('Missing required kwarg: {}'.format(ex))
        super().__init__(*args, **kwargs)

        # Report window should stay above the main window.
        self.attributes('-topmost', 1)

        self.parent_len = len(self.parent_files)
        self.error_len = len(self.error_files)
        self.success_len = len(self.success_files)

        self.title('{} - {}'.format(NAME, self.title_msg))
        self.geometry(self.config_gui.get('geometry_report', '331x301'))
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.pack(fill=tk.BOTH, expand='yes')
        self.style = ttk.Style()
        self.style.theme_use(self.theme)

        # Build parent files frame
        self.frm_parent = ttk.Frame(
            self.frm_main,
            # text='Master files ({}):'.format(self.parent_len),
            padding='2 2 2 2',
        )
        self.frm_parent.pack(fill=tk.X, expand='yes')
        self.tree_parent = ttk.Treeview(
            self.frm_parent,
            selectmode='none',
            height=3,
        )
        self.tree_parent.pack(side=tk.LEFT, fill=tk.X, expand='yes')
        self.tree_parent['columns'] = ('file',)
        self.tree_parent['show'] = 'headings'
        self.tree_parent.heading(
            'file',
            anchor='w',
            text=' Master Files: {}'.format(self.parent_len),
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
        self.scroll_parent.pack(side=tk.RIGHT, fill=tk.Y, expand='no')

        # Build error files frame
        self.frm_error = ttk.Frame(
            self.frm_main,
            # text='Errors ({}):'.format(self.error_len),
            padding='2 2 2 2',
        )
        self.frm_error.pack(fill=tk.X, expand='yes')
        self.tree_error = ttk.Treeview(
            self.frm_error,
            selectmode='none',
            height=5,
        )
        self.tree_error.pack(side=tk.LEFT, fill=tk.X, expand='yes')
        self.tree_error['columns'] = ('file', 'message')
        self.tree_error['show'] = 'headings'
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
        self.scroll_error.pack(side=tk.RIGHT, fill=tk.Y, expand='no')

        # Build success files frame
        self.frm_success = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_success.pack(fill=tk.X, expand='yes')
        self.tree_success = ttk.Treeview(
            self.frm_success,
            selectmode='none',
            height=10,
        )

        self.tree_success.pack(side=tk.LEFT, fill=tk.X, expand='yes')
        self.tree_success['columns'] = ('file',)
        self.tree_success['show'] = 'headings'
        self.tree_success.heading(
            'file',
            anchor='w',
            text=' Tiger Files: {}'.format(self.success_len),
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
        self.scroll_success.pack(side=tk.RIGHT, fill=tk.Y, expand='no')

        # Build cmds frame.
        self.frm_cmds = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_cmds.pack(fill=tk.X, expand='yes')

        self.btn_ok = ttk.Button(
            self.frm_cmds,
            text='Okay',
            width=4,
            command=self.cmd_btn_ok,
        )
        self.btn_ok.pack(
            side=tk.RIGHT,
            fill=tk.NONE,
            expand='no',
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )
        self.btn_ok.focus_set()
        # Fill tree views.
        self.build_trees()

    def build_trees(self):
        """ Build/fill tree views from file names, errors, and messages. """
        for parentfile in self.parent_files:
            self.tree_parent.insert(
                '',
                tk.END,
                values=(parentfile, ),
                text='Master File',
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

        for mozfile, tigerpath in self.success_files:
            self.tree_success.insert(
                '',
                tk.END,
                values=(tigerpath, ),
                text='Tiger File',
                tag='success',
            )

    def cmd_btn_ok(self):
        """ Handles btn_okay click. """
        self.destroy()

    def destroy(self):
        debug('Saving gui-report config...')
        self.config_gui['geometry_report'] = self.geometry()
        self.config_gui.pop('auto_run')
        config_save(self.config_gui)
        debug('Calling destroy_cb()...')
        self.destroy_cb()
        debug('Closing report window (geometry={!r}).'.format(self.geometry()))
        super().destroy()


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


def load_gui(**kwargs):
    win = WinMain(**kwargs)  # noqa
    debug('Starting main window...')
    try:
        tk.mainloop()
    except Exception as ex:
        print_err('Main loop error: ({})\n{}'.format(
            type(ex).__name__,
            ex,
        ))
