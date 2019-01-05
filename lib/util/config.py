#!/usr/bin/env python3

""" tigertamer - util/config.py
    Holds configuration/settings for Tiger Tamer.
    -Christopher Welborn 12-22-2018
"""

import os
import sys

from easysettings import JSONSettings

from .logger import (
    debug_err,
    debug_obj,
)

NAME = 'Tiger Tamer'
VERSION = '0.1.0'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

CONFIGFILE = os.path.join(SCRIPTDIR, 'tigertamer.json')
ICONFILE = os.path.join(
    SCRIPTDIR,
    'resources',
    'tigertamer-icon.png'
)
try:
    config = JSONSettings.from_file(CONFIGFILE)
except FileNotFoundError:
    config = JSONSettings()
    config.filename = CONFIGFILE


def config_save(d=None):
    if d:
        config.update(d)
    debug_obj(dict(config.items()), msg='Saving config:')
    try:
        config.save(sort_keys=True)
    except EnvironmentError as ex:
        debug_err('Unable to save gui config!: {}'.format(ex))
