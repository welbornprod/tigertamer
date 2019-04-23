#!/usr/bin/env python3

""" tigertamer - gui/unarchive.py
    Unarchive window for Tiger Tamer GUI.
    -Christopher Welborn 01-05-2019
"""

from ..util.config import (
    NAME,
    config_increment,
    config_save,
)
from ..util.logger import (
    debug,
)
from ..util.archive import (
    Archive,
)
from .common import (
    create_event_handler,
    handle_cb,
    tk,
    trim_file_path,
    ttk,
    validate_dirs,
    WinToplevelBase,
)
from .report import WinReport


class WinUnarchive(WinToplevelBase):
    def __init__(
            self, *args,
            settings, destroy_cb, report_cb, arch_dir, dat_dir,
            **kwargs):

        self.settings = settings
        self.destroy_cb = destroy_cb
        self.report_cb = report_cb
        self.arch_dir = arch_dir
        self.dat_dir = dat_dir
        super().__init__(*args, **kwargs)
        self.debug_settings()

        # Make a topmost window, because the main window can't be used
        # right now anyway.
        self.attributes('-topmost', 1)

        self.title('{} - Unarchive'.format(NAME))
        self.geometry(
            self.settings.get('geometry_unarchive', None) or '731x163'
        )

        # Hotkey info.
        hotkeys = {
            'unarchive': {
                'label': 'Unarchive',
                'char': 'U',
                'func': self.cmd_btn_unarchive,
            },
            'exit': {
                'label': 'Exit',
                'char': 'x',
                'func': self.cmd_btn_exit,
            },
        }
        # Singleton for the report window.
        self.win_report = None

        # Archive info, set with `self.build_file_tree()` after init.
        # It will be a util.archive.Archive object.
        self.archive = None

        # Topmost frame, for window padding.
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.pack(fill=tk.BOTH, expand=True)

        # File wrapper.
        self.frm_top = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_top.pack(
            fill=tk.BOTH,
            side=tk.TOP,
            expand=True,
        )
        # # Build files frame
        self.frm_files = ttk.Frame(
            self.frm_top,
            padding='2 2 2 2',
        )
        self.frm_files.pack(
            fill=tk.BOTH,
            side=tk.LEFT,
            expand=True,
        )
        self.tree_files = ttk.Treeview(
            self.frm_files,
            selectmode='extended',
            height=3,
        )
        self.tree_files.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_files.configure(columns=('file', ), show='headings')
        self.tree_files.heading(
            'file',
            anchor='w',
            text=' Archive Files:',
        )
        self.scroll_files = ttk.Scrollbar(
            self.frm_files,
            orient='vertical',
            command=self.tree_files.yview,
        )
        self.tree_files.configure(
            yscrollcommand=self.scroll_files.set
        )
        self.scroll_files.pack(side=tk.RIGHT, fill=tk.Y, expand=False)

        # Main commands frame.
        self.frm_cmds = ttk.Frame(
            self.frm_main,
            padding='2 4 2 2',
        )
        self.frm_cmds.pack(
            fill=tk.X,
            side=tk.TOP,
            expand=False,
        )

        # # Main commands.
        btnwidth = 10
        unarchivelbl = hotkeys['unarchive']['label']
        self.btn_unarchive = ttk.Button(
            self.frm_cmds,
            text=unarchivelbl,
            underline=unarchivelbl.index(hotkeys['unarchive']['char']),
            width=btnwidth,
            command=hotkeys['unarchive']['func'],
        )
        self.btn_unarchive.pack(
            side=tk.LEFT,
            fill=tk.NONE,
            expand=False,
            anchor='nw',
            padx=2,
            ipadx=8,
            ipady=8,
        )

        exitlbl = hotkeys['exit']['label']
        self.btn_exit = ttk.Button(
            self.frm_cmds,
            text=exitlbl,
            underline=exitlbl.index(hotkeys['exit']['char']),
            width=btnwidth,
            command=hotkeys['exit']['func'],
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
        for btninfo in hotkeys.values():
            self.bind_all(
                '<Control-{}>'.format(btninfo['char'].lower()),
                create_event_handler(btninfo['func']),
            )

        # Build file tree.
        self.build_file_tree()

    def build_file_tree(self):
        """ Fills the file treeview with archive files. """
        # Hide this window, in case there are no files to display.
        self.withdraw()
        try:
            self.archive = Archive(self.arch_dir, self.dat_dir)
        except (OSError, ValueError) as ex:
            return self.show_error(ex, fatal=True)
        if not self.archive:
            self.show_error('No archive files found.', fatal=True)

        # Show this window since we have files to display.
        self.deiconify()
        for src in sorted(self.archive):
            self.tree_files.insert(
                '',
                tk.END,
                values=(src, ),
                text='Archive File',
                tag='archive',
            )

        self.tree_files.heading(
            'file',
            anchor='w',
            text=' Archive Files: {}'.format(len(self.archive)),
        )

    def cmd_btn_exit(self):
        """ Handles btn_exit click. """
        self.destroy()

    def cmd_btn_unarchive(self):
        """ Handles btn_unarchive click. """
        debug('Attempting to unarchive files...')
        # Validate the dirs, but the input, output directory doesn't matter.
        if not self.validate_dirs():
            return False

        selected = self.tree_files.selection()
        if not selected:
            self.show_error('No archive files are selected.')
            return False

        # Files that will be unarchived
        targetinfo = []
        for index in selected:
            iteminfo = self.tree_files.item(index)
            filepath = iteminfo['values'][0]
            targetinfo.append(self.archive[filepath])

        self.attributes('-topmost', 0)
        self.withdraw()
        if not self.confirm_unarchive(targetinfo):
            debug('User cancelled unarchiving.')
            self.attributes('-topmost', 1)
            self.deiconify()
            return False

        errs = []
        success = []

        archive_files = []
        for archfile in targetinfo:
            archive_files.append(archfile.filepath)
            try:
                archfile.unarchive()
            except OSError as ex:
                errs.append((archfile.dest_path, str(ex)))
            else:
                success.append(archfile.filepath)

        config_increment(unarchive_files=len(success), default=0)

        self.show_report(
            archive_files,
            errs,
            success,
        )
        return True

    def confirm_unarchive(self, archfiles):
        """ Returns True if the user confirms the question. """
        filelen = len(archfiles)
        plural = 'file' if filelen == 1 else 'files'
        msg = '\n'.join((
            'This will unarchive {length} {plural}:',
            '{files}',
            '\nContinue?',
        )).format(
            length=filelen,
            plural=plural,
            files='\n'.join(
                '  {}'.format(trim_file_path(archfile.filepath))
                for archfile in archfiles
            )
        )
        return self.show_question(
            msg,
            title='Unarchive {} {}?'.format(filelen, plural)
        )

    def destroy(self):
        """ Handle this unarchive window being destroyed. """
        debug('Saving unarchive-gui config...')
        self.settings['geometry_unarchive'] = self.geometry()
        config_save(self.settings)
        debug('Closing unarchive window (geometry={!r}).'.format(
            self.settings['geometry_unarchive']
        ))
        # Remove topmost, and hide this window, in case any callbacks want
        # to show a dialog.
        self.attributes('-topmost', 0)
        self.withdraw()
        super().destroy()
        debug('Calling destroy_cb({})...'.format(self.destroy_cb))
        handle_cb(self.destroy_cb)

    def enable_interface(self, enabled=True):
        """ Enable/Disable the user interface (while running,
            or after running).
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        widgets = (
            self.btn_unarchive,
            self.btn_exit,
        )
        for widget in widgets:
            widget['state'] = state

    def show_report(self, parent_files, error_files, success_files):
        """ Show a report for moz->tiger transformations or unarchiving files
        """
        # self.report_closed() will re-enable the interface.
        self.enable_interface(False)
        if self.report_cb is None:
            destroy_cb = self.destroy
        else:
            destroy_cb = [
                self.destroy,
                self.report_cb,
            ]
        reportmsg = 'Success'
        if error_files:
            reportmsg = 'Errors: {}'.format(len(error_files))

        self.win_report = WinReport(  # noqa
            self,
            title_msg=reportmsg,
            settings={
                'geometry_report': self.settings['geometry_report'],
            },
            destroy_cb=destroy_cb,
            parent_files=[trim_file_path(s) for s in parent_files],
            error_files=[
                (trim_file_path(s), m) for s, m in error_files
            ],
            success_files=[trim_file_path(s) for s in success_files],
            parent_name='Archive',
            success_name='Restored',
        )

    def validate_dirs(self):
        return validate_dirs(
            arch_dir=self.arch_dir,
            dat_dir=self.dat_dir,
            ignore_dirs=('mozaik', 'tiger'),
        )
