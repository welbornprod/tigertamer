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
    config_gui_get,
    config_gui_merge,
    config_gui_save,
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


class MainWin(tk.Tk):
    default_theme = 'clam'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_gui = config_gui_get()
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
        self.frm_opts = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
            borderwidth=2,
        )
        self.frm_opts.pack(fill=tk.X, expand='yes')

        # Build theme options.
        self.frm_theme = ttk.LabelFrame(
            self.frm_opts,
            text='Theme:',
            padding='2 2 2 2',
        )
        self.frm_theme.pack(fill=tk.X, expand='yes')
        self.cmb_theme = ttk.Combobox(
            self.frm_theme,
            state='readonly',
            values=self.known_themes,
        )
        self.cmb_theme.pack(fill=tk.BOTH, expand='yes')
        self.cmb_theme.current(self.known_themes.index(usetheme))
        self.cmb_theme.bind(
            '<<ComboboxSelected>>',
            self.event_cmb_theme_select,
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
        )

        # Fix message boxes.
        self.option_add('*Dialog.msg.font', 'Arial 10')

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
        debug('Set {} dir: {}'.format(name, entry.get()))

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

    def build_done_msg(self, parent_files, error_files, success_files):
        """ Build a report/message regarding the parent files parsed,
            any errors/error-files, and the success files.
        """
        parentlen = len(parent_files)
        parentlines = [
            'Parsed {} {}{}'.format(
                parentlen,
                'file' if parentlen == 1 else 'files',
                ':' if parent_files else '.'
            )
        ]
        parentlines.extend(
            '  {}'.format(self.trim_file_path(s))
            for s in sorted(parent_files)
        )
        parentmsg = '\n'.join(parentlines)

        errlen = len(error_files)
        errlines = [
            '{} {} had an error{}'.format(
                errlen,
                'file' if errlen == 1 else 'files',
                ':' if error_files else '.',
            )
        ]
        errlines.extend(
            '\n'.join((
                '  {}'.format(self.trim_file_path(errfile.filename)),
                '    {}'.format(msg),
            ))
            for errfile, msg in error_files
        )
        errmsg = '\n'.join(errlines)

        successlen = len(success_files)
        successlines = [
            'Created {} tiger {}{}'.format(
                successlen,
                'file' if successlen == 1 else 'files',
                ':' if success_files else '.',
            )
        ]
        successlines.extend(
            '  {}'.format(self.trim_file_path(tigerpath))
            for _, tigerpath in success_files
        )
        successmsg = '\n'.join(successlines)

        return '\n\n'.join((parentmsg, errmsg, successmsg))

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
        msg = self.build_done_msg(parentfiles, error_files, success_files)
        self.show_done_msg(msg, errors=len(error_files))

        self.enable_interface(True)

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
        config_gui_merge(self.config_gui)
        config_gui_save()
        debug('Closing main window (geometry={!r}).'.format(self.geometry()))
        super().destroy()

    def enable_interface(self, enabled):
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
            self.show_error(msg)
            return False
        return True


def load_gui():
    win = MainWin()  # noqa
    debug('Starting main window...')
    tk.mainloop()
