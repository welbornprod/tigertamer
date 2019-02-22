#!/usr/bin/env python3

""" tigertamer - util/config.py
    Holds configuration/settings for Tiger Tamer.
    -Christopher Welborn 12-22-2018
"""

import os
import sys
from platform import platform

from easysettings import JSONSettings

from .logger import (
    debug,
    debug_err,
)

NAME = 'Tiger Tamer'
VERSION = '0.1.1'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

CONFIGFILE = os.path.join(SCRIPTDIR, 'tigertamer.json')
ICONFILE = os.path.join(
    SCRIPTDIR,
    'resources',
    'tigertamer-icon.png'
)

# Something besides None, to mean No Value.
Nothing = object()

try:
    config = JSONSettings.from_file(CONFIGFILE)
    debug('Loaded config from: {}'.format(CONFIGFILE))
except FileNotFoundError:
    config = JSONSettings()
    config.filename = CONFIGFILE
    debug('No config file, starting fresh: {}'.format(CONFIGFILE))


def config_increment(**kwargs):
    """ Retrieve a config key's value, and increment it by `value`,
        then save the config.
        Config keys/values are passed in by `kwargs`.
        A `default` key can be given, for default values.
    """
    default = kwargs.get('default', Nothing)
    if default is not Nothing:
        kwargs.pop('default')

    for key, value in kwargs.items():
        debug('Incrementing config value: {!r}={!r} ({!r})'.format(
            key,
            value,
            'Nothing' if default is Nothing else default,
        ))
        v = config.get(key, default)
        if v is Nothing:
            debug_err('Tried to increment invalid config key: {}'.format(key))
            return False
        if value == 0:
            debug_err('Tried to increment by 0. Cancelling.')
            return False
        try:
            config[key] = v + value
        except Exception as ex:
            debug_err(
                'Can\'t increment key \'{}\': ({}) {}'.format(
                    key,
                    type(ex).__name__,
                    ex)
            )
            return False
    return config_save()


def config_load():
    """ Reload config from disk. """
    try:
        c = JSONSettings.from_file(CONFIGFILE)
        debug('Config reloaded from: {}'.format(CONFIGFILE))
    except FileNotFoundError:
        c = JSONSettings()
        c.filename = CONFIGFILE
        debug('No config to reload: {}'.format(CONFIGFILE))
    return c


def config_save(d=None):
    global config
    # Reload config from disk, because other threads may have changed it.
    config = config_load()

    if d:
        config.update(d)
    # debug_obj(dict(config.items()), msg='Saving config:')
    debug('Saving config (items: {})'.format(len(d or config)))
    try:
        config.save(sort_keys=True)
    except EnvironmentError as ex:
        debug_err('Unable to save gui config!: {}'.format(ex))
        return False
    return True


def get_system_info():
    """ Returns information about this machine/app. """
    debug('Building system info...')
    return {
        'platform': platform(),
        'python_ver': '.'.join(str(i) for i in sys.version_info[0:3]),
        'runs': config.get('runs', 1),
        'runtime_secs': config.get('runtime_secs', 1),
        'master_files': config.get('master_files', 0),
        'tiger_files': config.get('tiger_files', 0),
        'archive_files': config.get('archive_files', 0),
        'unarchive_files': config.get('unarchive_files', 0),
        'remove_files': config.get('remove_files', 0),
    }
