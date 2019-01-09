#!/usr/bin/env python3

""" about.py
    About window for Tiger Tamer GUI.
    -Christopher Welborn 01-05-2019
"""

import sys
from platform import platform

from .common import (
    tk,
    ttk,
)

from ..util.config import (
    ICONFILE,
    NAME,
    VERSION,
    config_save,
    get_system_info,
)
from ..util.logger import (
    debug,
)

PLATFORM = platform()


def humantime_fromsecs(secs):
    """ Return brief but human-readable string representing time-elapsed
        since `date`.
        Arguments:
            secs       : Seconds to determine time from.
    """

    if secs < 60:
        # Seconds (decimal format)
        return '{:0.1f} seconds'.format(secs)

    minutes, seconds = divmod(secs, 60)
    minstr = 'minute' if int(minutes) == 1 else 'minutes'
    secstr = 'second' if seconds == 1 else 'seconds'
    if minutes < 60:
        # Minutes and seconds only.
        if seconds == 0:
            # minutes
            return '{:.0f} {}'.format(minutes, minstr)
        # minutes, seconds
        return '{:.0f} {}, {:.0f} {}'.format(minutes, minstr, seconds, secstr)

    hours, minutes = divmod(minutes, 60)
    hourstr = 'hour' if int(hours) == 1 else 'hours'
    minstr = 'minute' if minutes == 1 else 'minutes'
    if hours < 24:
        # Hours, minutes, and seconds only.
        if minutes == 0:
            # hours
            return '{:.0f} {}'.format(hours, hourstr)
        # hours, minutes
        return '{:.0f} {}, {:.0f} {}'.format(hours, hourstr, minutes, minstr)

    days, hours = divmod(hours, 24)

    # Days, hours
    daystr = 'day' if days == 1 else 'days'
    hourstr = 'hour' if hours == 1 else 'hours'
    if hours == 0:
        # days
        return '{:.0f} {}'.format(days, daystr)

    # days, hours
    return '{:.0f} {}, {:.0f} {}'.format(days, daystr, hours, hourstr)


class WinAbout(tk.Tk):
    def __init__(self, *args, **kwargs):
        self.config_gui = {k: v for k, v in kwargs.items()}
        try:
            self.destroy_cb = kwargs.pop('destroy_cb')
            self.config_gui.pop('destroy_cb')
        except KeyError as ex:
            raise TypeError('Missing required kwarg: {}'.format(ex))
        # Don't send kwargs to Tk().
        for k in self.config_gui:
            kwargs.pop(k)
        super().__init__(*args, **kwargs)

        # Initialize this window.
        self.title('{} - About'.format(NAME))
        self.geometry(self.config_gui.get('geometry_about', '442x228'))
        # About window should stay above the main window.
        self.attributes('-topmost', 1)
        # Make the main frame expand.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        # Main frame.
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.grid(row=0, column=0, sticky=tk.NSEW)
        for x in range(1):
            self.frm_main.columnconfigure(x, weight=1)
            self.frm_main.rowconfigure(x, weight=1)
        # .Info wrapper.
        self.frm_top = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_top.grid(row=0, column=0, sticky=tk.EW)
        # Make the children in column 1 expand.
        self.frm_top.columnconfigure(1, weight=1)
        # ..Image
        self.frm_img = ttk.Frame(
            self.frm_top,
            borderwidth=2,
            relief=tk.GROOVE,
        )
        self.frm_img.grid(row=0, column=0, sticky=tk.NSEW)
        self.img_icon = tk.PhotoImage(master=self.frm_img, file=ICONFILE)
        self.lbl_img = ttk.Label(self.frm_img, image=self.img_icon)
        self.lbl_img.image = self.img_icon
        self.lbl_img.grid(row=0, column=0, sticky=tk.NSEW)
        self.lbl_img.bind('<ButtonRelease>', self.cmd_lbl_img_click)

        # ..Main information panel.
        self.frm_tt = ttk.Frame(
            self.frm_top,
            padding='2 2 2 2',
        )
        self.frm_tt.grid(row=0, column=1, sticky=tk.NSEW)
        # Make children expand.
        self.frm_tt.columnconfigure(0, weight=1)
        # ...Name label
        self.lbl_name = ttk.Label(
            self.frm_tt,
            text=NAME,
            font='Arial 11 bold',
            justify=tk.CENTER,
        )
        self.lbl_name.grid(row=0, column=0, pady=4)
        # ...Version label
        self.lbl_version = ttk.Label(
            self.frm_tt,
            text='v. {}'.format(VERSION),
            font='Arial 8',
            justify=tk.CENTER,
        )
        self.lbl_version.grid(row=1, column=0)
        # ...Author label
        self.var_author = tk.StringVar()
        self.lbl_author = ttk.Label(
            self.frm_tt,
            text='Christopher Welborn',
            font='Arial 10 italic',
            justify=tk.CENTER,
        )
        self.lbl_author.grid(row=2, column=0, pady=4)

        # .Sys Info Frame
        self.frm_info = ttk.Frame(self.frm_main, padding='2 2 2 2')
        self.frm_info.grid(row=1, column=0)
        # Make the entry grow.
        for x in range(1):
            self.frm_info.columnconfigure(x, weight=1)
            self.frm_info.rowconfigure(x, weight=1)
        # ..Sys Info Scrollbar
        self.scroll_info = ttk.Scrollbar(self.frm_info)
        self.scroll_info.grid(row=0, column=1, sticky=tk.NSEW)
        # ..Sys Info Text
        self.text_info = tk.Text(
            self.frm_info,
            width=len(PLATFORM) + 5,
            height=10,
            yscrollcommand=self.scroll_info.set,
            bg='#ffffff',
            fg='#000000',
        )
        self.scroll_info.configure(command=self.text_info.yview)
        self.text_info.grid(row=0, column=0, sticky=tk.NSEW)
        # Insert all information into the Text widget.
        self.build_info()
        self.text_info.configure(state=tk.DISABLED)

    def append_info(self, text):
        """ Append lines of information into the text_info Text() widget.
            If a `str` is passed, the text is simply appended with no newline.
        """
        if not isinstance(text, str):
            for line in text:
                if not line.endswith('\n'):
                    line = '{}\n'.format(line)
                self.append_info(line)
            return None

        self.text_info.insert(tk.END, text)
        return None

    def build_info(self):
        """ Insert machine/app/runtime info into the text_info Text(). """
        d = get_system_info()
        self.append_info(
            '\n'.join((
                '      Total Runs: {d[runs]}',
                '      Total Time: {totaltime}',
                '    Average Time: {avgtime}',
                '    Master Files: {d[master_files]}',
                '     Tiger Files: {d[tiger_files]}',
                '  Archived Files: {d[archive_files]}',
                'Unarchived Files: {d[unarchive_files]}',
                '   Removed Files: {d[remove_files]}',
                '  Python Version: {d[python_ver]}',
                '        Platform:',
                '  {d[platform]}',

            )).format(
                d=d,
                avgtime=humantime_fromsecs(
                    (d['runtime_secs'] or 1) / (d['runs'] or 1)
                ) or 'n/a',
                totaltime=humantime_fromsecs(d['runtime_secs']) or 'n/a',
            )
        )

    def cmd_lbl_img_click(self, event):
        """ Handles lbl_img click. """
        # TODO: Easter Egg.
        debug('Icon clicked.')

    def destroy(self):
        debug('Saving gui-about config...')
        self.config_gui['geometry_about'] = self.geometry()
        config_save(self.config_gui)
        debug('Calling destroy_cb()...')
        self.destroy_cb()
        debug('Closing about window (geometry={!r}).'.format(self.geometry()))
        super().destroy()
