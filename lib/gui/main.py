#!/usr/bin/env python3

""" tigertamer - gui/main.py
    Handles the GUI for TigerTamer.
    -Christopher Welborn 12-22-2018 - 1-5-19
"""

import os
from time import time

from ..util.config import (
    config_increment,
    config_save,
    lock_acquire,
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
    get_tiger_files,
    load_moz_files,
    write_tiger_file,
)

from .about import WinAbout
from .common import (
    create_event_handler,
    filedialog,
    show_error,
    show_question,
    tk,
    trim_file_path,
    ttk,
    validate_dirs,
)

from .labels import WinLabels
from .report import WinReport
from .unarchive import WinUnarchive
from .viewer import WinViewer


class WinMain(tk.Tk):
    default_theme = 'clam'

    def __init__(self, *, run_function=None, **kwargs):
        self.run_function = run_function or None
        self.settings = {k: v for k, v in kwargs.items()}
        # Don't send WinMain kwargs to Tk.
        super().__init__()

        # Set icon for main window and all children.
        try:
            self.main_icon = tk.PhotoImage(master=self, file=ICONFILE)
            self.iconphoto(True, self.main_icon)
        except Exception as ex:
            print_err('Failed to set icon: {}\n{}'.format(ICONFILE, ex))
            self.main_icon = None

        debug_obj(self.settings, msg='Using GUI config:')

        self.title('Tiger Tamer')
        self.geometry(self.settings.get('geometry', '331x301'))
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.pack(fill=tk.BOTH, expand=True)
        self.style = ttk.Style()

        # knownstyles = ('clam', 'alt', 'default', 'classic')
        self.known_themes = sorted(self.style.theme_names())
        usetheme = self.settings.get('theme', 'clam').lower()
        if usetheme not in self.known_themes:
            debug_err('Invalid theme name: {}'.format(usetheme))
            debug_err('Using {!r}'.format(self.default_theme))
            debug('Known themes: {}'.format(', '.join(self.known_themes)))
            usetheme = self.default_theme
        self.style.theme_use(usetheme)
        self.theme = usetheme

        # Fix message boxes.
        self.option_add('*Dialog.msg.font', 'Arial 10')

        # Singleton instance for the About window (WinAbout).
        self.win_about = None
        # Singleton instance for the Label Config window (WinLabels).
        self.win_labels = None
        # A singleton instance for the Report window (WinReport).
        self.win_report = None
        # A singleton instance for the Unarchive window (WinUnarchive).
        self.win_unarchive = None
        # A singleton instance for the Tiger Viewer window (WinViewer).
        self.win_viewer = None

        # Hotkey and Menu information for this window, programmatically setup.
        # They are first sorted by label, and then by 'order' (if available).
        hotkeys = {
            'help': {
                'About': {
                    'char': 'A',
                    'func': self.cmd_menu_about,
                },
            },
            'admin': {
                'Remove Tiger Files': {
                    'char': 'T',
                    'func': self.cmd_menu_remove_tiger_files,
                },
                # Label Config is the first item (order: 0)
                'Label Config': {
                    'char': 'L',
                    'func': self.cmd_menu_labels,
                    'order': 0,
                },
                'Tiger Viewer': {
                    'char': 'V',
                    'func': self.cmd_menu_viewer,
                    'order': 1,
                },
                # Separator under tiger viewer (order: 2).
                '-': {'order': 2},
                'Unarchive and Remove Tiger Files': {
                    'char': 'n',
                    'func': self.cmd_menu_unarchive_and_remove,
                },
                'Unarchive': {
                    'char': 'U',
                    'func': self.cmd_menu_unarchive,
                },
            },
            'btns': {
                'Run': {
                    'char': 'R',
                    'func': self.cmd_btn_run,
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
        self.menu_admin = tk.Menu(self.menu_main, tearoff=0)
        adminsortkey = lambda k: hotkeys['admin'][k].get('order', 99)  # noqa
        for lbl in sorted(sorted(hotkeys['admin']), key=adminsortkey):
            if lbl.startswith('-'):
                self.menu_admin.add_separator()
                continue
            admininfo = hotkeys['admin'][lbl]
            self.menu_admin.add_command(
                label=lbl,
                underline=lbl.index(admininfo['char']),
                command=admininfo['func'],
                accelerator='Ctrl+{}'.format(admininfo['char'].upper()),
            )
            self.bind_all(
                '<Control-{}>'.format(admininfo['char'].lower()),
                create_event_handler(admininfo['func'])
            )
        self.menu_main.add_cascade(
            label='Admin',
            menu=self.menu_admin,
            underline=0,
        )

        # Build Help menu.
        self.menu_help = tk.Menu(self.menu_main, tearoff=0)
        for lbl, helpinfo in hotkeys['help'].items():
            self.menu_help.add_command(
                label=lbl,
                underline=lbl.index(helpinfo['char']),
                command=helpinfo['func'],
                accelerator='Ctrl+{}'.format(helpinfo['char'].upper()),
            )
            self.bind_all(
                '<Control-{}>'.format(helpinfo['char'].lower()),
                lambda event: helpinfo['func']()
            )

        self.menu_main.add_cascade(
            label='Help',
            menu=self.menu_help,
            underline=0,
        )

        # Set main menu to root window.
        self.config(menu=self.menu_main)

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
        self.frm_opts_main.pack(fill=tk.X, expand=True)

        # Build theme options.
        self.frm_theme = ttk.LabelFrame(
            self.frm_opts_main,
            text='Theme:',
            padding='2 2 2 2',
        )
        self.frm_theme.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=1,
        )
        self.cmb_theme = ttk.Combobox(
            self.frm_theme,
            state='readonly',
            values=self.known_themes,
        )
        self.cmb_theme.pack(side=tk.LEFT, fill=tk.X, expand=True)
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
            expand=True,
            padx=1,
        )
        # Build left row of options.
        self.frm_opts_left = ttk.Frame(
            self.frm_opts,
        )
        self.frm_opts_left.pack(
            fill=tk.BOTH,
            side=tk.LEFT,
            expand=True,
            padx=0,
        )
        # Auto exit?
        self.var_auto_exit = tk.BooleanVar()
        self.var_auto_exit.set(self.settings.get('auto_exit', False))
        self.chk_auto_exit = ttk.Checkbutton(
            self.frm_opts_left,
            text='Exit after report',
            onvalue=True,
            offvalue=False,
            variable=self.var_auto_exit,
        )
        self.chk_auto_exit.pack(
            side=tk.TOP,
            anchor=tk.W,
            expand=False,
        )
        # Extra data?
        self.var_extra_data = tk.BooleanVar()
        self.var_extra_data.set(self.settings.get('extra_data', False))
        self.chk_extra_data = ttk.Checkbutton(
            self.frm_opts_left,
            text='Use extra data',
            onvalue=True,
            offvalue=False,
            variable=self.var_extra_data,
        )
        self.chk_extra_data.pack(
            side=tk.BOTTOM,
            anchor=tk.W,
            expand=False,
        )
        # Build right row of options.
        self.frm_opts_right = ttk.Frame(
            self.frm_opts,
        )
        self.frm_opts_right.pack(
            fill=tk.BOTH,
            expand=True,
            side=tk.RIGHT,
            padx=0,
        )
        # Debug mode?
        self.var_debug = tk.BooleanVar()
        self.var_debug.set(get_debug_mode())
        self.chk_debug = ttk.Checkbutton(
            self.frm_opts_right,
            text='Debug mode',
            onvalue=True,
            offvalue=False,
            variable=self.var_debug,
            command=self.cmd_chk_debug,
        )
        self.chk_debug.pack(
            side=tk.TOP,
            anchor=tk.W,
            expand=False,
        )
        # Split parts?
        self.var_no_part_split = tk.BooleanVar()
        self.var_no_part_split.set(self.settings.get('no_part_split', True))
        self.chk_no_part_split = ttk.Checkbutton(
            self.frm_opts_right,
            text='Don\'t split parts',
            onvalue=True,
            offvalue=False,
            variable=self.var_no_part_split,
        )
        self.chk_no_part_split.pack(
            side=tk.BOTTOM,
            anchor=tk.W,
            expand=False,
        )
        # Build Run/Exit buttons frame
        self.frm_cmds = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
            borderwidth=2,
        )
        self.frm_cmds.pack(fill=tk.BOTH, expand=True)
        # Run button
        runlbl = 'Run'
        runinfo = hotkeys['btns'][runlbl]
        self.btn_run = ttk.Button(
            self.frm_cmds,
            text=runlbl,
            underline=runlbl.index(runinfo['char']),
            width=4,
            command=runinfo['func'],
        )
        self.btn_run.pack(
            side=tk.LEFT,
            fill=tk.NONE,
            expand=False,
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )
        # Set focus to the Run button
        self.btn_run.focus_set()

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

        if self.run_function:
            # Auto run function?
            self.call_by_name(self.run_function)
        elif self.settings.get('auto_run', False):
            # Auto run?
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
            expand=True,
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
        configdir = self.settings.get(config_key, '')
        if not isinstance(configdir, str):
            # Handle possible lists of directories in `dat_dir`.
            configdir = configdir[0]
        var.set(configdir)
        entry.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
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
            expand=False,
            anchor='nw',
            padx=2,
        )

    def call_by_name(self, name, *args, **kwargs):
        """ Call a WinMain method by name only. """
        func = getattr(self, name, None)
        if func is None:
            # Look for a function starting with `self.run_function`.
            origname = name
            name = self.find_func_by_name(name)
            if name is None:
                name = origname
                func = None
            else:
                func = getattr(self, name, None)
            if func is None:
                raise ValueError('Invalid function name: {}}'.format(
                    name,
                ))
        if not callable(func):
            raise ValueError('Not callable: {!r}'.format(func))
        debug('Calling function for user: {}()'.format(name))
        return func()

    def cmd_btn_arch(self):
        """ Handles btn_arch click. """
        arch_dir = filedialog.askdirectory()
        if not arch_dir:
            return
        self.var_arch.set(arch_dir)
        self.settings['archive_dir'] = arch_dir
        debug('Selected new archive directory: {}'.format(
            self.var_arch.get()
        ))

    def cmd_btn_dat(self):
        """ Handles btn_dat click. """
        dat_dir = filedialog.askdirectory()
        if not dat_dir:
            return
        self.var_dat.set(dat_dir)
        self.settings['dat_dir'] = [dat_dir]
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
                ignore_dirs=self.settings['ignore_dirs'],
                ignore_strs=self.settings['ignore_strs'],
                split_parts=not self.var_no_part_split.get(),
            )
        except OSError as ex:
            show_error('Cannot load .dat files in: {}\n{}'.format(
                mozdir,
                ex,
            ))
            self.enable_interface(True)
            return

        if not mozfiles:
            show_error('No Mozaik (.dat) files found in: {}'.format(
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

        time_start = time()
        errs = 0
        for mozfile in mozfiles:
            try:
                errs += write_tiger_file(
                    mozfile,
                    self.entry_tiger.get(),
                    archive_dir=self.entry_arch.get() or '',
                    extra_data=self.var_extra_data.get(),
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

        config_increment(
            master_files=len(parentfiles),
            tiger_files=len(success_files),
            runs=1,
            runtime_secs=time() - time_start,
            default=0,
        )

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
        self.settings['tiger_dir'] = tiger_dir
        debug('Selected new tiger directory: {}'.format(
            self.var_dat.get()
        ))

    def cmd_chk_debug(self):
        """ Handles chk_debug click. Sets debug mode. """
        set_debug_mode(self.var_debug.get())

    def cmd_menu_about(self):
        """ Handles menu_about click. """
        # destroy_cb will re-enable the interface.
        self.enable_interface(False)
        self.win_about = WinAbout(
            self,
            settings={'geometry_about': self.settings['geometry_about']},
            destroy_cb=lambda: self.report_closed(
                allow_auto_exit=False,
            ),
        )

    def cmd_menu_labels(self):
        """ Handles menu->Label Config click. """
        self.enable_interface(False)
        self.win_labels = WinLabels(
            self,
            settings={
                'geometry_labels': self.settings['geometry_labels'],
            },
            destroy_cb=lambda: self.enable_interface(True),
        )
        return True

    def cmd_menu_remove_tiger_files(self):
        """ Handles menu_remove_tiger_files click. """
        if not self.validate_dirs(ignore_dirs=('mozaik', 'archive')):
            return

        outdir = self.var_tiger.get()

        try:
            filepaths = get_tiger_files(outdir)
        except OSError as ex:
            show_error(ex)
            return False

        if not filepaths:
            show_error('No files to remove: {}'.format(outdir))
            return False

        if not self.confirm_remove(filepaths):
            debug('User cancelled tiger file removal.')
            return False
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

        config_increment(remove_files=len(success), default=0)

        self.show_report(
            filepaths,
            errs,
            success,
            allow_auto_exit=False,
            parent_name='Tiger',
            success_name='Removed Tiger',
        )
        return True

    def cmd_menu_test(self):
        """ Test menu item, foobjectr dev-related testing. """
        debug('Test menu clicked.')

    def cmd_menu_unarchive(self, remove_tiger_files=False):
        """ Handles btn_unarchive click. """
        if not self.validate_dirs(ignore_dirs=('tiger', 'mozaik')):
            return False

        if remove_tiger_files:
            report_cb = self.cmd_menu_remove_tiger_files
        else:
            report_cb = None

        self.enable_interface(False)
        self.win_unarchive = WinUnarchive(
            self,
            settings={
                'geometry_report': self.settings['geometry_report'],
                'geometry_unarchive': self.settings['geometry_unarchive'],
            },
            destroy_cb=lambda: self.enable_interface(True),
            report_cb=report_cb,
            arch_dir=self.entry_arch.get(),
            dat_dir=self.entry_dat.get(),
        )
        return True

    def cmd_menu_unarchive_and_remove(self):
        """ Handles menu->Unarchive and Remove Tiger Files """
        return self.cmd_menu_unarchive(remove_tiger_files=True)

    def cmd_menu_viewer(self, filenames=None, preview_files=None):
        """ Handles menu->Tiger Viewer click. """
        self.enable_interface(False)
        self.win_viewer = WinViewer(
            self,
            settings={
                'geometry_viewer': self.settings['geometry_viewer'],
            },
            destroy_cb=lambda: self.enable_interface(True),
            dat_dir=self.entry_dat.get(),
            tiger_dir=self.entry_tiger.get(),
            filenames=filenames,
            preview_files=preview_files,
        )
        return True

    @classmethod
    def cmds(cls):
        """ Return a list of all cmd_* function names. """
        return [a for a in dir(cls) if a.startswith('cmd_')]

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
                '  {}'.format(trim_file_path(s))
                for s in files
            )
        )
        return show_question(
            msg,
            title='Remove {} {}?'.format(filelen, plural)
        )

    def destroy(self):
        debug('Saving gui config...')
        self.settings['dat_dir'] = [self.entry_dat.get()]
        self.settings['tiger_dir'] = self.entry_tiger.get()
        self.settings['archive_dir'] = self.entry_arch.get()
        self.settings['geometry'] = self.geometry()
        self.settings['theme'] = self.theme
        self.settings['auto_exit'] = self.var_auto_exit.get()
        self.settings['extra_data'] = self.var_extra_data.get()
        self.settings['no_part_split'] = self.var_no_part_split.get()
        # Child windows have saved their geometry already.
        self.settings.pop('geometry_report')
        self.settings.pop('geometry_about')
        self.settings.pop('geometry_unarchive')
        self.settings.pop('geometry_viewer')
        config_save(self.settings)
        debug('Closing main window (geometry={!r}).'.format(self.geometry()))
        super().destroy()

    def enable_interface(self, enabled=True):
        """ Enable/Disable the user interface (while running,
            or after running).
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        widgets = (
            self.btn_run,
            self.btn_exit,
            self.chk_auto_exit,
            self.chk_debug,
            self.chk_extra_data,
            self.chk_no_part_split,
            self.entry_dat,
            self.btn_dat,
            self.entry_tiger,
            self.btn_tiger,
            self.entry_arch,
            self.btn_arch,
        )
        for widget in widgets:
            widget.configure(state=state)

        # Main menus.
        menus = (
            'Admin',
            'Help',
        )
        for name in menus:
            self.menu_main.entryconfigure(name, state=state)

    def event_cmb_theme_select(self, event):
        self.theme = self.known_themes[self.cmb_theme.current()]
        self.style.theme_use(self.theme)
        self.settings['theme'] = self.theme

    def find_func_by_name(self, name):
        """ Find a WinMain method by name, or the start/end of a name.
            Returns the method name on success, or None if it can't be found.
        """
        names = [
            a
            for a in dir(self)
            if a.startswith(name) or a.endswith(name)
        ]
        if not names:
            return None
        return sorted(names)[0]

    def report_closed(self, allow_auto_exit=False):
        """ Called when the report window is closed. """
        self.enable_interface()
        if allow_auto_exit and self.var_auto_exit.get():
            self.destroy()

    def show_fatal_error(self, msg):
        """ Show an error message and close. """
        show_error(msg)
        self.destroy()

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
            self,
            title_msg=reportmsg,
            settings={
                'geometry_report': self.settings['geometry_report'],
            },
            destroy_cb=lambda: self.report_closed(
                allow_auto_exit=allow_auto_exit,
            ),
            parent_files=[trim_file_path(s) for s in parent_files],
            error_files=[
                (trim_file_path(s), m) for s, m in error_files
            ],
            success_files=[trim_file_path(s) for s in success_files],
            parent_name=parent_name,
            success_name=success_name,
        )

    def validate_dirs(self, ignore_dirs=None):
        """ Returns True if all directories are set, and valid.
            Shows an error message if any of them are not.
        """
        return validate_dirs(
            dat_dir=self.entry_dat.get(),
            tiger_dir=self.entry_tiger.get(),
            arch_dir=self.entry_arch.get(),
            ignore_dirs=ignore_dirs,
        )


def list_funcs():
    """ List all functions available with -f (from WinMain).
        Returns an exit status code.
    """
    funcs = WinMain.cmds()
    if not funcs:
        print_err('No functions found! What happened?')
        return 1
    funclen = len(funcs)
    plural = 'function' if funclen == 1 else 'functions'
    print('Found {} WinMain {}:'.format(funclen, plural))
    print('    {}'.format('\n    '.join(sorted(funcs))))
    return 0


def load_gui(**kwargs):
    tiger_files = kwargs.pop('tiger_files')
    preview_files = kwargs.pop('preview_files')
    debug('Starting main window...')
    debug('tiger_files: {}'.format(tiger_files))
    debug('preview_files: {}'.format(preview_files))
    win = WinMain(**kwargs)  # noqa
    if (tiger_files is not None) and (not tiger_files):
        # --view was used without file paths.
        win.withdraw()
        show_error('No Tiger (.tiger) files provided for viewing.')
        return 1
    elif (preview_files is not None) and (not preview_files):
        # --preview was used without file paths.
        win.withdraw()
        show_error('No Mozaik (.dat) files provided for preview.')
        return 1
    elif tiger_files or preview_files:
        # Schedule a viewing/previewing when ready.
        win.after_idle(win.cmd_menu_viewer, tiger_files, preview_files)
    try:
        lock_acquire()
    except ValueError:
        win.attributes('-topmost', 0)
        win.withdraw()
        print_err('{} is already running.'.format(NAME))
        return 3
    try:
        tk.mainloop()
    except Exception as ex:
        print_err('Main loop error: ({})\n{}'.format(
            type(ex).__name__,
            ex,
        ))
        return 1
    return 0
