#!/usr/bin/env python3

""" labels.py
    Label config window for Tiger Tamer GUI.
    -Christopher Welborn 04-13-2019
"""

from collections import UserList

from .common import (
    Font,
    WinToplevelBase,
    create_event_handler,
    handle_cb,
    tk,
    ttk,
)

from ..util.config import (
    NAME,
    config_save,
)
from ..util.format import (
    available_labels,
    label_config_get,
    label_config_save,
)
from ..util.logger import (
    debug,
    debug_obj,
)


# TODO: Still not sure if scaling is correct.
# TODO: Double-click tag to reset to file-based config values.


class TagInfo(object):
    """ A namedtuple-style class for canvas tag references.
        Holds a canvas id, tag name, and a Font.
    """
    __slots__ = ('id', 'name', 'font', 'fontconfig', 'width', 'height')

    def __init__(self, canvasid, name, font):
        self.id = canvasid
        self.name = name
        self.font = font
        self.fontconfig = font.configure()
        self.width = self.font.measure(self.name)
        self.height = self.font.metrics()['ascent']

    def __str__(self):
        return '{}: {} ({} {})'.format(
            self.id,
            self.name.title(),
            self.fontconfig['family'],
            self.fontconfig['size'],
        )


class TagInfos(UserList):
    """ A list of TagInfos, held by ArialWinLabels. """
    def tag_by_id(self, canvasid):
        for canvastag in self:
            if canvastag.id == canvasid:
                return canvastag
        raise ValueError('No TagInfo with that id: {!r}'.format(canvasid))

    def tag_by_name(self, name):
        for canvastag in self:
            if canvastag.name == name:
                return canvastag
        raise ValueError('No TagInfo with that name: {!r}'.format(name))


class WinLabels(WinToplevelBase):
    def __init__(
            self, *args,
            settings, destroy_cb,
            **kwargs):
        self.settings = settings
        self.destroy_cb = destroy_cb
        # Don't send kwargs to Toplevel().
        super().__init__(*args, **kwargs)

        # Initialize this window.
        self.title('{} - Labels'.format(NAME))
        self.geometry(
            self.settings.get('geometry_labels', None) or '420x186'
        )
        # About window should stay above the main window.
        self.attributes('-topmost', 1)
        # Make the main frame expand.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.lbl_config = label_config_get()

        # Max values, no matter what font size is selected.
        # This size is in 'dots'.
        self.max_dot_x = 446
        self.max_dot_y = 268
        # Convert dots to inches (Tk can set canvas widths in inches).
        self.max_lbl_size_x = self.max_dot_x * 0.005
        self.max_lbl_size_y = self.max_dot_y * 0.005
        # Actual height/width of canvas in pixels.
        self.max_lbl_x = self.max_dot_x // 2.23
        self.max_lbl_y = self.max_dot_y // 1.34
        # Acceptable font sizes (according to TigerLink 6).
        self.valid_font_sizes = (6, 9, 12, 16, 24)

        # Label that was selected before new label selection (None at first).
        self.last_label = None

        # Tag drag/drop info. Set in event_tag_*.
        self.tag_drag = {'x': 0, 'y': 0, 'id': None, 'dragged': False}

        # Main frame.
        self.frm_main = ttk.Frame(self, padding='2 2 2 2')
        self.frm_main.pack(fill=tk.BOTH, expand=True)

        # # Top frame.
        self.frm_top = ttk.Frame(self.frm_main, padding='2 2 2 2')
        self.frm_top.pack(
            side=tk.TOP,
            fill=tk.X,
            expand=True,
        )

        # # # Config frame.
        self.frm_config = ttk.LabelFrame(
            self.frm_top,
            text='Labels:',
            padding='2 2 2 2',
        )
        self.frm_config.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=False,
            padx=1,
        )
        self.cmb_labels = ttk.Combobox(
            self.frm_config,
            state='readonly',
            values=self.label_names(title=True),
        )
        self.cmb_labels.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.cmb_labels.bind(
            '<<ComboboxSelected>>',
            self.event_cmb_labels_select,
        )
        # # # Label values
        self.frm_values = ttk.Frame(self.frm_config, padding='2 2 2 2')
        self.frm_values.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self._build_entries()
        self.entry_fontsize.bind(
            '<Return>',
            self.event_entry_return
        )
        self.entry_x.bind(
            '<Return>',
            self.event_entry_return
        )
        self.entry_y.bind(
            '<Return>',
            self.event_entry_return
        )
        if self.lbl_config:
            # Select the first label, if any config was available.
            self.cmb_labels.current(0)
            # Ensure the selection event fires (with no event info though).
            self.event_cmb_labels_select(None)

        # # # Label preview.
        self.frm_canvas = ttk.Frame(self.frm_top, padding='2 2 2 2')
        self.frm_canvas.pack(
            side=tk.RIGHT,
            fill=tk.X,
            expand=False,
        )
        # Set canvas width/height to a 2.2in by 1.25in label.
        # Tkinter allows units of measurement in it's height/width values:
        # c: Centimeters
        # i: Inches
        # m: Millimeters
        # p: Printer's points (1/72")
        self.canvas_lbl = tk.Canvas(
            self.frm_canvas,
            height='{}i'.format(self.max_lbl_size_y),
            width='{}i'.format(self.max_lbl_size_x),
            background='white',
        )
        self.canvas_lbl.pack(fill=tk.NONE, expand=False)
        canvas_lbl_config = self.canvas_lbl.configure()
        self.canvas_height = int(canvas_lbl_config['height'][4])
        self.canvas_width = int(canvas_lbl_config['width'][4])
        debug('Set canvas Height: {}, Width: {}'.format(
            self.canvas_height,
            self.canvas_width,
        ))
        self.canvas_lbl.bind(
            '<Motion>',
            self.event_canvas_lbl_motion
        )
        # References to canvas items.
        self.canvas_tags = TagInfos()
        self.update_label_canvas()

        # # Status frame.
        self.frm_status = ttk.Frame(self.frm_main, padding='2 2 2 2')
        self.frm_status.pack(
            fill=tk.X,
            expand=True,
        )
        self.var_status = tk.StringVar()
        self.lbl_status = ttk.Label(
            self.frm_status,
            text="",
            textvariable=self.var_status,
            anchor=tk.E,
            font='Monospace 9',
        )
        self.lbl_status.pack(
            fill=tk.X,
            expand=True,
        )

        # # Button frame.
        self.frm_btns = ttk.Frame(self.frm_main, padding='5 2 5 2')
        self.frm_btns.pack(
            fill=tk.X,
            expand=False,
        )

        # # # Buttons.
        btninfo = {
            'Ok': {
                'char': 'O',
                'func': self.cmd_btn_ok,
            },
            'Cancel': {
                'char': 'C',
                'func': self.cmd_btn_cancel,
            }
        }
        btnwidth = len(max(btninfo, key=len)) + 1
        # Ok button.
        oklbl = 'Ok'
        self.btn_ok = ttk.Button(
            self.frm_btns,
            text=oklbl,
            underline=oklbl.index(btninfo[oklbl]['char']),
            width=btnwidth,
            command=btninfo[oklbl]['func'],
        )
        self.btn_ok.pack(
            side=tk.LEFT,
            fill=tk.NONE,
            expand=False,
            anchor=tk.SW,
        )

        # Cancel button.
        cancellbl = 'Cancel'
        self.btn_cancel = ttk.Button(
            self.frm_btns,
            text=cancellbl,
            underline=cancellbl.index(btninfo[cancellbl]['char']),
            width=btnwidth,
            command=btninfo[cancellbl]['func'],
        )
        self.btn_cancel.pack(
            side=tk.RIGHT,
            fill=tk.NONE,
            expand=False,
            anchor=tk.SE,
        )

        # Bind hotkeys for buttons.
        for info in btninfo.values():
            self.bind_all(
                '<Control-{}>'.format(info['char'].lower()),
                create_event_handler(info['func']),
            )

    def _build_entries(self):
        """ Build the label/emtry pairs for each editable value for the
            labels.
        """
        for val_name in ('font_size', 'x', 'y'):
            self._build_entry(val_name)

    def _build_entry(self, name):
        """ Build a single label/entry pair for an editable value. """
        # Wrapper frame for each editable value.
        widgetname = name.replace('_', '')
        frmname = 'frm_{}'.format(widgetname)
        setattr(
            self,
            frmname,
            ttk.Frame(self.frm_values, padding='0')
        )
        frm = getattr(self, frmname)
        frm.pack(side=tk.TOP, fill=tk.X, expand=True)
        # Label for each entry.
        lblname = 'lbl_{}'.format(widgetname)
        setattr(
            self,
            lblname,
            ttk.Label(
                frm,
                text='{}: '.format(name.replace('_', ' ').title()),
                anchor=tk.E,
                justify='right',
            )
        )
        lbl = getattr(self, lblname)
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Entry/StringVar for each value.
        entryname = 'entry_{}'.format(widgetname)
        varname = 'var_{}'.format(widgetname)
        setattr(
            self,
            varname,
            tk.StringVar(frm, value='0'),
        )
        # Valid percent substitutions for validatecommand.
        # They are passed as arguments to the validation function.
        #
        # %d : Type of action (1=insert, 0=delete, -1 for others)
        # %i : Index of char string to be inserted/deleted, or -1
        # %P : Value of the entry if the edit is allowed
        # %s : Value of entry prior to editing
        # %S : The text string being inserted or deleted, if any
        # %v : The type of validation that is currently set
        # %V : The type of validation that triggered the callback
        #      (key, focusin, focusout, forced)
        # %W : The tk name of the widget
        vcmd = (
            self.register(self.validate_int_entry),
            "%d",
            "%i",
            "%P",
            "%s",
            "%S",
            "%v",
            "%V",
            "%W",
        )
        setattr(
            self,
            entryname,
            ttk.Entry(
                frm,
                width=4,
                textvariable=getattr(self, varname),
                validate='key',
                validatecommand=vcmd,
            )
        )
        entry = getattr(self, entryname)
        entry.pack(side=tk.RIGHT)

    def cmd_btn_cancel(self):
        """ Handles btn_cancel.click. """
        return self.destroy()

    def cmd_btn_ok(self):
        """ Handles btn_ok.click. """
        # Save current label config in memory.
        self.update_label_config()
        # Validate label config before saving.
        err_lines = []
        for lblname in self.label_names():
            try:
                self.validate_lbl_config(lblname)
            except ValueError as ex:
                err_lines.append(str(ex))
                self.label_select(lblname)

        if err_lines:
            # Bad config, can't save.
            self.show_error('\n\n'.join(err_lines))
            return

        debug('Saving label config...')
        label_config_save(self.lbl_config)
        return self.destroy()

    def destroy(self):
        """ Close the window. """
        debug('Saving gui-labels config...')
        self.settings['geometry_labels'] = self.geometry()
        config_save(self.settings)
        debug('Closing labels window (geometry={!r}).'.format(
            self.settings['geometry_labels']
        ))
        self.attributes('-topmost', 0)
        self.withdraw()
        super().destroy()
        debug('Calling destroy_cb({})...'.format(self.destroy_cb))
        handle_cb(self.destroy_cb)

    def entry_clear(self, entry):
        """ Clear an Entry widget's text. """
        entry.delete(0, tk.END)

    def entry_set(self, entry, text):
        """ Clear and Set an Entry widget's text. """
        self.entry_clear(entry)
        entry.insert(tk.END, text)

    def event_canvas_lbl_motion(self, event):
        """ Handler for mouse motion in `self.canvas_lbl`. """
        x = event.x
        y = event.y
        if not self.tag_drag['dragged']:
            # Don't update while dragging tags. event_tag_motion does that.
            self.var_status.set(
                'x:{:>3}, y:{:>3}'.format(int(x), int(y))
            )

    def event_cmb_labels_select(self, event):
        """ Handler for self.cmd_labels selection. """
        # This does not fire when self.cmb_labels.current(index) is called.
        name = self.cmb_labels.get()
        if self.last_label:
            # Save current label config in memory.
            self.update_label_config(name=self.last_label)
        # Update the label info entries.
        self.update_label_entries()
        self.last_label = name

    def event_entry_return(self, event):
        """ Handler for <Return> in all Entry widgets. """
        self.update_label_config()
        self.update_label_canvas()

    def event_tag_motion(self, event):
        """ Handler for tag left-down-motion in `self.canvas_lbl`. """
        self.tag_drag['dragged'] = True
        canvasid = self.tag_from_event(event)
        coords = self.canvas_lbl.coords(canvasid)
        tagx, tagy = int(coords[0]), int(coords[1])
        # Find move-difference and "move" the tag by that much,
        # only if it's within the bounds of the canvas.
        delta_x = event.x - self.tag_drag['x']
        delta_y = event.y - self.tag_drag['y']
        # Don't move if it would move the tag outside the bounds.
        newtagx = tagx + delta_x
        newtagy = tagy + delta_y
        taginfo = self.canvas_tags.tag_by_id(canvasid)
        max_width = self.canvas_width - taginfo.width
        max_height = self.canvas_height - taginfo.height
        if (newtagx < 0) or (newtagx > max_width):
            delta_x = 0
        if (newtagy < 0) or (newtagy > max_height):
            delta_y = 0

        if delta_x or delta_y:
            self.canvas_lbl.move(self.tag_drag['id'], delta_x, delta_y)

        # Reset drag data, for next drag move.
        self.tag_drag['x'] = event.x
        self.tag_drag['y'] = event.y

        # Dragging a tag, "fix" the status values to mean label x and y.
        self.var_x.set(tagx)
        self.var_y.set(tagy)
        self.var_status.set(
            'x:{:>3}, y:{:>3}'.format(tagx, tagy)
        )

    def event_tag_press(self, event):
        """ Handler for tag left-button-down in `self.canvas_lbl`. """
        self.tag_drag = {
            'x': event.x,
            'y': event.y,
            'id': self.tag_from_event(event),
            'dragged': False,
        }
        self.label_select_index(self.label_index_from_event(event))

    def event_tag_release(self, event):
        """ Handler for tag left-button-up in `self.canvas_lbl`. """
        if self.tag_drag['dragged']:
            name = self.label_name_from_event(event)
            self.update_label_config(name=name)
            # Save this label name so `event_cmb_labels_select` doesn't
            # overwrite the wrong label info.
            self.last_label = name
        # Reset drag data.
        self.tag_drag = {'x': 0, 'y': 0, 'id': None, 'dragged': False}

    def label_index(self, name):
        """ Get an index into `cmb_labels` or `lbl_config` by name. """
        return self.label_names().index(name.lower())

    def label_index_from_event(self, event):
        """ Get an index into `cmb_labels` or `lbl_config` by tag position.
        """
        canvasid = self.tag_from_event(event)
        # Canvas ids are 1-based, and increment on every
        # call to update_label_canvas().
        return ((canvasid % 4) or 4) - 1

    def label_info_get(self, name):
        """ Get config values for a specific label by name. """
        name = name.lower()
        for lblname, lblinfo in self.lbl_config:
            if name == lblname:
                return lblinfo
        # No config for this label. Is it new?
        return {}

    def label_info_set(self, name, fontsize=None, x=None, y=None):
        """ Set label config in memory for WinLabels, by label name. """
        name = name.lower()
        d = None
        lblconfig = list(self.lbl_config)
        for lblname, lblinfo in lblconfig:
            if name == lblname:
                d = lblinfo
                break
        else:
            # New item.
            if name not in available_labels:
                self.show_error('\n\n'.join((
                    'Not a valid label name: {}'.format(name),
                    'Should be one of:',
                    ', '.join(available_labels)
                )))
                return
        # Set config values if they are not empty.
        if fontsize and (int(fontsize) > 0):
            d['fontsize'] = fontsize
        else:
            debug('Not setting empty {}.fontsize!'.format(name))
        if x or (x == 0):
            d['x'] = x
        else:
            debug('Not setting empty {}.x!'.format(name))
        if y or (y == 0):
            d['y'] = y
        else:
            debug('Not setting empty {}.y!'.format(name))

        self.update_label_canvas()

    def label_name(self, index):
        """ Get a label name from an index. """
        return self.label_names()[index]

    def label_name_from_event(self, event):
        """ Get a label name from a position in `event`. """
        return self.label_name(self.label_index_from_event(event))

    def label_names(self, title=False):
        """ Get the names for all label's in `self.lbl_config`. """
        return tuple((s.title() if title else s) for s, _ in self.lbl_config)

    def label_select(self, name):
        """ Select a label in `cmb_labels` by name. """
        self.labels_select_index(self.label_index(name))

    def label_select_index(self, index, no_canvas=False):
        """ Select a label in `cmb_labels` by index. """
        self.cmb_labels.current(index)
        self.update_label_entries()

    def tag_from_event(self, event):
        """ Return a tag id from an event's x,y coordinates. """
        return self.canvas_lbl.find_closest(event.x, event.y)[0]

    def update_label_canvas(self):
        """ Re-draw the label preview canvas based on self.lbl_config. """
        # Clear current tags and bindings for them.
        for canvastag in self.canvas_tags:
            self.canvas_lbl.tag_unbind(canvastag.id, '<ButtonPress-1>')
        self.canvas_lbl.delete(tk.ALL)
        self.canvas_tags = TagInfos()

        for name, lblinfo in self.lbl_config:
            fontsize = int(lblinfo['fontsize'])
            font = Font(family='Doris PP', size=fontsize, weight='normal')
            x = int(lblinfo['x'])
            y = int(lblinfo['y'])
            canvasid = self.canvas_lbl.create_text(
                (x, y),
                text=name.title(),
                anchor=tk.NW,
                activefill='blue',
                fill='black',
                font=font,
            )
            # Save canvas id and bind event handlers to it.
            canvastag = TagInfo(canvasid, name, font)
            self.canvas_tags.append(canvastag)
            self.canvas_lbl.tag_bind(
                canvasid,
                '<ButtonPress-1>',
                self.event_tag_press,
            )
            self.canvas_lbl.tag_bind(
                canvasid,
                '<ButtonRelease-1>',
                self.event_tag_release,
            )
            self.canvas_lbl.tag_bind(
                canvasid,
                '<B1-Motion>',
                self.event_tag_motion,
            )

    def update_label_config(self, name=None):
        """ Update `self.lbl_config` with values from the entries. """
        if not name:
            name = self.cmb_labels.get()
        if not name:
            return None
        self.label_info_set(
            name,
            fontsize=self.var_fontsize.get(),
            x=self.var_x.get(),
            y=self.var_y.get(),
        )
        return None

    def update_label_entries(self):
        """ Update entry values with `self.lbl_config`. """
        name = self.cmb_labels.get()
        # Update the label info entries.
        lblinfo = self.label_info_get(name)
        fontsize = lblinfo.get(
            'fontsize',
            str(self.valid_font_sizes[0])
        )
        self.var_fontsize.set(fontsize)
        self.entry_set(self.entry_fontsize, fontsize)
        x = lblinfo.get('x', '0')
        self.var_x.set(x)
        self.entry_set(self.entry_x, x)
        y = lblinfo.get('y', '0')
        self.var_y.set(y)
        self.entry_set(self.entry_y, y)

    def validation_debug(self, *args):
        arg_names = (
            'action_type',
            'index',
            'val_if_allowed',
            'val_prior',
            'val_changed',
            'validation_type_set',
            'validate_type_triggered',
            'tk_widget_name',
        )
        arginfo = {arg_names[i]: arg for i, arg in enumerate(args)}
        debug_obj(arginfo, msg='Received arguments:')
        return arginfo

    def validate_int_entry(
            self,
            action_type,
            index,
            val_if_allowed,
            val_prior,
            val_changed,
            validation_type_set,
            validate_type_triggered,
            tk_widget_name):
        """ Validate integer input for entries using `validatecommand`.
            Returns True for integer input, otherwise False.
        """
        if not val_if_allowed:
            return True
        try:
            int(val_if_allowed)
        except (TypeError, ValueError):
            debug('Invalid content for {}:'.format(
                tk_widget_name,
            ))
            self.bell()
            return False

        return True

    def validate_lbl_config(self, name):
        """ Validate a label's config settings by name.

        """
        name = name.lower()
        lblinfo = self.label_info_get(name)
        if not lblinfo:
            raise ValueError(
                'Label config not found: {}'.format(name)
            )
        # Font size validation.
        fontsize_cfg = lblinfo.get('fontsize', self.valid_font_sizes[0])
        try:
            fontsize = int(fontsize_cfg or self.valid_font_sizes[0])
        except (TypeError, ValueError):
            raise ValueError(
                'Font size for {} is not a number: {}'.format(
                    name,
                    fontsize_cfg,
                )
            )
        if fontsize not in self.valid_font_sizes:
            raise ValueError(
                'Invalid font size for {}: {}\n\nExpecting one of: {}'.format(
                    name.title(),
                    fontsize_cfg,
                    ', '.join(str(x) for x in self.valid_font_sizes)
                )
            )

        # X validation.
        x_cfg = lblinfo.get('x', '0')
        try:
            x = int(x_cfg or 0)
        except (TypeError, ValueError):
            raise ValueError(
                'X position for {!r} is not a number: {}'.format(
                    name.title(),
                    x_cfg
                )
            )
        if x < 0:
            raise ValueError(
                'X position for {!r} must be positive: {}'.format(
                    name.title(),
                    x_cfg
                )
            )
        if x > self.max_dot_x:
            raise ValueError(
                'X position for {!r} must be less than {}: {}'.format(
                    name.title(),
                    self.max_dot_x,
                    x_cfg,
                )
            )

        # Y validation.
        y_cfg = lblinfo.get('y', '0')
        try:
            y = int(y_cfg or 0)
        except (TypeError, ValueError):
            raise ValueError(
                'Y position for {!r} is not a number: {}'.format(
                    name.title(),
                    y_cfg
                )
            )
        if y < 0:
            raise ValueError(
                'Y position for {!r} must be positive: {}'.format(
                    name.title(),
                    y_cfg
                )
            )
        if y > self.max_dot_y:
            raise ValueError(
                'Y position for {!r} must be less than {}: {}'.format(
                    name.title(),
                    self.max_dot_y,
                    y_cfg,
                )
            )
