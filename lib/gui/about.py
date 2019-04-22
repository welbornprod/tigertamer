#!/usr/bin/env python3

""" about.py
    About window for Tiger Tamer GUI.
    -Christopher Welborn 01-05-2019
"""

import random
import string

from platform import platform

from .common import (
    handle_cb,
    tk,
    ttk,
    WinToplevelBase,
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
)

PLATFORM = platform()


def humantime_fromsecs(secs, float_fmt='0.2f'):
    """ Return brief but human-readable string representing time-elapsed
        since `date`.
        Arguments:
            secs       : Seconds to determine time from.
    """

    if secs < 60:
        # Seconds (decimal format)
        fmtstr = '{{:{}}} seconds'.format(float_fmt)
        return fmtstr.format(secs)

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


class WinAbout(WinToplevelBase):
    def __init__(
            self, *args,
            settings, destroy_cb,
            **kwargs):
        self.settings = settings
        self.destroy_cb = destroy_cb

        # Don't send kwargs to Toplevel().
        super().__init__(*args, **kwargs)

        # Initialize this window.
        self.title('{} - About'.format(NAME))
        self.geometry(
            self.settings.get('geometry_about', None) or '442x246'
        )
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
        # .Info wrapper.
        self.frm_top = ttk.Frame(
            self.frm_main,
            padding='2 2 2 2',
        )
        self.frm_top.grid(row=0, column=0, sticky=(tk.N, tk.E, tk.W))
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
        # See cmd_lbl_img_click()..
        self.lbl_clicks = 0
        self.appending_garbage = False

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
            text=AUTHOR or 'Christopher Welborn',
            font='Arial 10 italic',
            justify=tk.CENTER,
        )
        self.lbl_author.grid(row=2, column=0, pady=4)

        # .Sys Info Frame
        self.frm_info = ttk.Frame(self.frm_main, padding='2 2 2 2')
        self.frm_info.grid(row=1, column=0, sticky=tk.NSEW)
        self.frm_main.rowconfigure(1, weight=1)
        self.frm_info.rowconfigure(0, weight=1)
        self.frm_info.columnconfigure(0, weight=100)
        self.frm_info.columnconfigure(1, weight=1)
        # ..Sys Info Scrollbar
        self.scroll_info = ttk.Scrollbar(self.frm_info)
        self.scroll_info.grid(row=0, column=1, sticky=tk.NSEW)
        # ..Sys Info Text
        sysinfo = self.get_info()
        sysinfolines = sysinfo.split('\n')
        self.max_info_lines = len(sysinfolines)
        self.max_info_cols = len(PLATFORM) + 5
        self.text_info = tk.Text(
            self.frm_info,
            width=self.max_info_cols,
            height=self.max_info_lines,
            yscrollcommand=self.scroll_info.set,
            bg='#ffffff',
            fg='#000000',
        )
        self.text_info.tag_configure('error', foreground='#FF0000')
        self.scroll_info.configure(command=self.text_info.yview)
        self.text_info.grid(row=0, column=0, sticky=tk.NSEW)
        # Insert all information into the Text widget.
        self.append_info(sysinfo)
        # Make text read-only.
        self.text_info.configure(state=tk.DISABLED)

    def append_garbage(self, delay=0.025, callback=None):
        """ Append a bunch of garbage characters to `text_info`. """
        self.appending_garbage = True
        chars = ''.join((string.ascii_letters, string.punctuation))
        self.clear_info()
        delay = int(delay * 1000)
        msgs = [
            'Error',
            '[Deleting configuration...]',
            'ERROR',
            '[Deleting projects...]',
            'Deleting license...',
            'ID10T ERROR',
            '[Calling the boss...]',
            'PEBCAK FATAL ERROR',
            'You shouldn\'t mess with things you don\'t understand.',
        ]
        maxchars = (self.max_info_lines * self.max_info_cols)
        maxjunkchars = maxchars - len(''.join(msgs))
        chunk = maxjunkchars // len(msgs)
        while msgs:
            for i in range(chunk):
                self.append_info(random.choice(chars))
                self.after(delay)
                self.update_idletasks()
            for c in msgs.pop(0):
                self.append_info(c)
                self.after(delay)
                self.update_idletasks()
        if callback is None:
            return
        return callback()

    def append_info(self, text, tag=None):
        """ Append lines of information into the `text_info` Text() widget.
            If a `str` is passed, the text is simply appended with no newline.
        """
        self.text_info.configure(state=tk.NORMAL)
        if not isinstance(text, str):
            for line in text:
                if not line.endswith('\n'):
                    line = '{}\n'.format(line)
                self.append_info(line)
            return None
        if tag:
            self.text_info.insert(tk.END, text, tag)
        else:
            self.text_info.insert(tk.END, text)
        self.text_info.configure(state=tk.DISABLED)
        return None

    def change_info(self, text, tag=None):
        """ Change the text_info Text() widget's text. """
        self.clear_info()
        self.append_info(text, tag=None)

    def clear_info(self):
        """ Clear the `text_info` Text() widget. """
        self.text_info.configure(state=tk.NORMAL)
        self.text_info.delete('0.0', tk.END)
        self.text_info.configure(state=tk.DISABLED)

    def cmd_lbl_img_click(self, event):
        """ Handles lbl_img click. """
        self.lbl_clicks += 1
        if self.lbl_clicks < 2:
            return
        msgs = [
            'Stop doing that.',
            'Stop.',
            'Seriously, you don\'t know what is going to happen.',
        ]
        msglen = len(msgs)
        max_clicks = msglen + 1
        if self.lbl_clicks == max_clicks:
            self.change_info('Final warning.', tag='error')
        elif self.lbl_clicks > max_clicks:
            if not self.appending_garbage:
                self.append_garbage(callback=self.destroy)
        else:
            self.change_info(msgs[(self.lbl_clicks - 1) % msglen])

    def destroy(self):
        debug('Saving gui-about config...')
        self.settings['geometry_about'] = self.geometry()
        config_save(self.settings)
        debug('Closing about window (geometry={!r}).'.format(
            self.settings['geometry_about']
        ))
        self.attributes('-topmost', 0)
        self.withdraw()
        super().destroy()
        debug('Calling destroy_cb({})...'.format(self.destroy_cb))
        handle_cb(self.destroy_cb)

    def get_info(self):
        """ Get machine/app/runtime info. """
        # TODO: Use insert(index, chars, tags) to tag labels/values and
        #       colorize them?
        d = get_system_info()
        avgtime = (d['runtime_secs'] or 1) / (d['runs'] or 1)
        debug('Total Time: {}, Runs: {}, Average: {}'.format(
            d['runtime_secs'],
            d['runs'],
            avgtime,
        ))

        return '\n'.join((
            '      Total Runs: {d[runs]}',
            '      Total Time: {totaltime}',
            '    Average Time: {avgtime}',
            '    Master Files: {d[master_files]}',
            '     Tiger Files: {d[tiger_files]}',
            '  Archived Files: {d[archive_files]}',
            'Unarchived Files: {d[unarchive_files]}',
            '   Removed Files: {d[remove_files]}',
            '    Fatal Errors: {d[fatal_errors]}',
            '  Python Version: {d[python_ver]}',
            '        Platform:',
            '  {d[platform]}',

        )).format(
            d=d,
            avgtime=humantime_fromsecs(avgtime) or 'n/a',
            totaltime=humantime_fromsecs(d['runtime_secs']) or 'n/a',
        )
