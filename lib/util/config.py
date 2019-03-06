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
VERSION = '0.2.4'
AUTHOR = 'Christopher Joseph Welborn'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

CONFIGFILE = os.path.join(SCRIPTDIR, 'tigertamer.json')
LOCKFILE = os.path.join(SCRIPTDIR, 'tigertamer.lock')
ICONFILE = os.path.join(
    SCRIPTDIR,
    'resources',
    'tigertamer-icon.png'
)

# pid used for checking the file lock.
PID = os.getpid()

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
    global config
    default = kwargs.get('default', Nothing)
    if default is not Nothing:
        kwargs.pop('default')

    for key, value in kwargs.items():
        v = config.get(key, default)
        if v is Nothing:
            debug_err('Tried to increment invalid config key: {}'.format(key))
            return False
        if value == 0:
            debug_err('Tried to increment by 0. Cancelling.')
            return False
        debug(
            'Incrementing: {k!r:>16} =  {v!r} + {newv!r}'.format(
                k=key,
                v=v or '(default: {})'.format(
                    'Nothing' if default is Nothing else default
                ),
                newv=value,
            )
        )

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
        else:
            debug(
                ' Incremented: {k!r:>16} == {v!r}'.format(
                    k=key,
                    v=config[key],
                ),
                align=True,
            )

    # Multithreaded Tkinter windows are not using 'globals' like they should.
    return config_save(config)


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
        for val in d.values():
            if isinstance(val, dict):
                debug_err(
                    'Saving a dict in config!: {!r}'.format(val),
                    level=1,
                )
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


def lock_acquire():
    """ Try acquiring the file lock. Raise ValueError if the lock is already
        acquired.
    """
    if os.path.exists(LOCKFILE):
        debug('Lock already acquired: {}'.format(LOCKFILE), level=1)
        raise ValueError('File lock already acquired: {}'.format(LOCKFILE))
    with open(LOCKFILE, 'w') as f:
        f.write(str(PID))
    debug('Lock acquired: {}'.format(LOCKFILE), level=1)


def lock_release():
    """ Release the file lock. """
    if not os.path.exists(LOCKFILE):
        debug('Lock already released: {}'.format(LOCKFILE), level=1)
        return True

    with open(LOCKFILE, 'r') as f:
        pid = int(f.read())
    if pid != PID:
        debug(
            'Lock not owned by this process: {} != {}'.format(
                pid,
                PID,
            ),
            level=1
        )
        return False
    # Lock is owned by this process.
    os.remove(LOCKFILE)
    debug('Lock released: {}'.format(LOCKFILE), level=1)
    return True
