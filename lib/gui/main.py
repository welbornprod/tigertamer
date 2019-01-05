#!/usr/bin/env python3

""" tigertamer - gui/main.py
    Handles the GUI for TigerTamer.
    -Christopher Welborn 12-22-2018 - 1-5-19
"""

import os


from ..util.config import (
    config_save,
    ICONFILE,
    NAME,
)

from ..util.logger import (
    debug,
    debug_err,
    debug_obj,
    get_debug_mode,
    print_err,
    set_debug_mode,
)
from ..util.parser import (
    get_archive_info,
    get_tiger_files,
    load_moz_files,
    unarchive_file,
    write_tiger_file,
)

from common import (
    tk,
    ttk,
    filedialog,
    messagebox,
)

from report import WinReport


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
        # Auto exit?
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
        # Debug mode?
        self.var_debug = tk.BooleanVar()
        self.var_debug.set(get_debug_mode())
        self.chk_debug = ttk.Checkbutton(
            self.frm_opts,
            text='Debug mode',
            onvalue=True,
            offvalue=False,
            variable=self.var_debug,
            command=self.cmd_chk_debug,
        )
        self.chk_debug.pack(
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

        # Undo menu
        self.menu_btn_undo = ttk.Menubutton(
            self.frm_cmds,
            text='Undo',
            width=5,
        )
        self.menu_undo = tk.Menu(
            self.menu_btn_undo,
            cursor='left_ptr',
            tearoff=0,
        )
        self.menu_btn_undo['menu'] = self.menu_undo
        # Add commands to menu.
        self.menu_undo.add_command(
            label='Unarchive',
            command=self.cmd_menu_unarchive,
        )
        self.menu_undo.add_command(
            label='Remove Tiger Files',
            command=self.cmd_menu_remove_tiger_files,
        )
        self.menu_btn_undo.pack(
            side=tk.LEFT,
            fill=tk.NONE,
            expand='no',
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )

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
        # Validate dirs, but allow an empty archive dir.
        if not self.validate_dirs(ignore_dirs=('archive', )):
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

        self.show_report(
            parent_files=parentfiles,
            error_files=[
                (mozfile.filename, msg)
                for mozfile, msg in sorted(
                    error_files,
                    key=lambda tup: tup[0].filename
                )
            ],
            success_files=[
                tigerpath
                for mozfile, tigerpath in sorted(
                    success_files,
                    key=lambda tup: tup[1]
                )
            ],
            allow_auto_exit=True,
            parent_name='Master',
            success_name='Tiger',
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

    def cmd_chk_debug(self):
        """ Handles chk_debug click. Sets debug mode. """
        set_debug_mode(self.var_debug.get())

    def cmd_menu_remove_tiger_files(self):
        """ Handles menu_remove_tiger_files click. """
        if not self.validate_dirs(ignore_dirs=('mozaik', 'archive')):
            return

        outdir = self.var_tiger.get()

        try:
            filepaths = get_tiger_files(outdir)
        except OSError as ex:
            self.show_error(ex)
            return

        if not filepaths:
            self.show_error('No files to remove: {}'.format(outdir))
            return

        if not self.confirm_remove(filepaths):
            debug('User cancelled tiger file removal.')
            return
        errs = []
        success = []
        for filepath in filepaths:
            try:
                os.remove(filepath)
            except OSError as ex:
                errs.append((filepath, str(ex)))
                debug_err(
                    'Failed to remove file: {}\n{}'.format(filepath, ex)
                )
            else:
                debug('Removed tiger file: {}'.format(filepath))
                success.append(filepath)

        self.show_report(
            filepaths,
            errs,
            success,
            allow_auto_exit=False,
            parent_name='Tiger',
            success_name='Removed Tiger',
        )
        return

    def cmd_menu_unarchive(self):
        """ Handles btn_unarchive click. """
        debug('Attempting to unarchive files...')
        # Validate the dirs, but the input, output directory doesn't matter.
        if not self.validate_dirs(ignore_dirs=('mozaik', 'tiger')):
            return
        datdir = self.var_dat.get()
        archdir = self.var_arch.get()
        try:
            files = get_archive_info(datdir, archdir)
        except (OSError, ValueError) as ex:
            self.show_error(ex)
            return
        if not self.confirm_unarchive(files):
            debug('User cancelled unarchiving.')
            return

        errs = []
        success = []

        archive_files = []
        for src, dest in files:
            archive_files.append(src)
            try:
                finalpath = unarchive_file(src, dest)
            except OSError as ex:
                errs.append((dest, str(ex)))
            else:
                success.append(finalpath)

        self.show_report(
            archive_files,
            errs,
            success,
            allow_auto_exit=False,
            parent_name='Archive',
            success_name='Restored',
        )
        return

    def confirm_remove(self, files):
        """ Returns True if the user confirms the question. """
        filelen = len(files)
        plural = 'file' if filelen == 1 else 'files'
        msg = '\n'.join((
            'This will remove {length} tiger {plural}:',
            '{files}',
            '\nContinue?',
        )).format(
            length=filelen,
            plural=plural,
            files='\n'.join(
                '  {}'.format(self.trim_file_path(s))
                for s in files
            )
        )
        return self.show_question(
            msg,
            title='Remove {} {}?'.format(filelen, plural)
        )

    def confirm_unarchive(self, files):
        """ Returns True if the user confirms the question. """
        filelen = len(files)
        plural = 'file' if filelen == 1 else 'files'
        msg = '\n'.join((
            'This will unarchive {length} {plural}:',
            '{files}',
            '\nContinue?',
        )).format(
            length=filelen,
            plural=plural,
            files='\n'.join(
                '  {}'.format(self.trim_file_path(s))
                for s, _ in files
            )
        )
        return self.show_question(
            msg,
            title='Unarchive {} {}?'.format(filelen, plural)
        )

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
            self.menu_btn_undo,
            self.btn_exit,
            self.chk_auto_exit,
            self.chk_debug,
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

    def report_closed(self, allow_auto_exit=True):
        """ Called when the report window is closed. """
        self.enable_interface()
        if allow_auto_exit and self.var_auto_exit.get():
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

    def show_question(self, msg, title=None):
        """ Show a tkinter askyesno dialog. """
        title = '{} - {}'.format(NAME, title or 'Confirm')
        return messagebox.askyesno(title=title, message=str(msg))

    def show_report(
            self, parent_files, error_files, success_files,
            allow_auto_exit=True, parent_name='Master', success_name='Tiger'):
        """ Show a report for moz->tiger transformations or unarchiving files
        """
        # self.report_closed() will re-enable the interface.
        self.enable_interface(False)
        reportmsg = 'Success'
        if error_files:
            reportmsg = 'Errors: {}'.format(len(error_files))

        self.win_report = WinReport(  # noqa
            title_msg=reportmsg,
            config_gui=self.config_gui,
            theme=self.theme,
            parent_files=[self.trim_file_path(s) for s in parent_files],
            error_files=[
                (self.trim_file_path(s), m) for s, m in error_files
            ],
            success_files=[self.trim_file_path(s) for s in success_files],
            parent_name=parent_name,
            success_name=success_name,
            destroy_cb=lambda: self.report_closed(
                allow_auto_exit=allow_auto_exit,
            ),
        )

    @staticmethod
    def trim_file_path(filepath):
        """ Trim most of the directories off of a file path.
            Leaves only the file name, and one sub directory.
        """
        path, fname = os.path.split(filepath)
        _, subdir = os.path.split(path)
        return os.path.join(subdir, fname)

    def validate_dirs(self, ignore_dirs=None):
        """ Returns True if all directories are set, and valid.
            Shows an error message if any of them are not.
        """
        dirs = (
            ('Mozaik (.dat)', self.entry_dat.get()),
            ('Tiger (.tiger)', self.entry_tiger.get()),
            ('Archive', self.entry_arch.get()),
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
            self.show_error(msg)
            return False
        return True


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