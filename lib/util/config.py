#!/usr/bin/env python3

""" tigertamer - util/config.py
    Holds configuration/settings for Tiger Tamer.
    -Christopher Welborn 12-22-2018
"""

import os
import sys
from platform import platform

from colr import (
    auto_disable as colr_auto_disable,
    Colr as C,
)
from easysettings import JSONSettings

from .logger import (
    debug,
    debug_err,
    debugprinter,
)

colr_auto_disable()
debugprinter.enable(('-D' in sys.argv) or ('--debug' in sys.argv))

NAME = 'Tiger Tamer'
VERSION = '0.2.9'
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


# Global JSONSettings() config object, available to other modules.
config = None


class _NotSet(object):
    def __bool__(self):
        return False

    def __colr__(self):
        return C('Not Set', 'red').join('<', '>', fore='dimgrey')

    def __str__(self):
        return '<Not Set>'


# Singleton instance for a None value that is not None.
NotSet = _NotSet()


def config_get(key, default=NotSet):
    """ Like config.get(), except it will load config if it hasn't been
        loaded yet.
    """
    global config
    if config is None:
        debug('Called config_get() before config was loaded.', level=1)
        config = config_load()
    try:
        val = config.get(key)
    except KeyError:
        if default is NotSet:
            raise
        return default
    return val


def config_increment(**kwargs):
    """ Retrieve a config key's value, and increment it by `value`,
        then save the config.
        Config keys/values are passed in by `kwargs`.
        A `default` key can be given, for default values.
    """
    global config
    default = kwargs.get('default', NotSet)
    if default is not NotSet:
        kwargs.pop('default')

    for key, value in kwargs.items():
        v = config_get(key, default)
        if v is NotSet:
            debug_err('Tried to increment invalid config key: {}'.format(key))
            return False
        if value == 0:
            debug_err('Tried to increment by 0. Cancelling.')
            return False
        debug(
            'Incrementing: {k!r:>16} =  {v!r} + {newv!r}'.format(
                k=key,
                v=v or '(default: {})'.format(default),
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
    return config_save(config, sub_dict_ok=True)


def config_load():
    """ Reload config from disk. """
    loadtype = 'load' if config is None else 'reload'
    try:
        c = JSONSettings.from_file(CONFIGFILE)
        debug('Config {}ed from: {}'.format(loadtype, CONFIGFILE))
    except FileNotFoundError:
        c = JSONSettings()
        c.filename = CONFIGFILE
        debug('No config to {}: {}'.format(loadtype, CONFIGFILE))
    return c


def config_save(d=None, sub_dict_ok=False):
    global config
    # Reload config from disk, because other threads may have changed it.
    config = config_load()
    subitemcnt = 0
    if d:
        for key, val in d.items():
            if isinstance(val, dict):
                subitemcnt += len(val)
                if (not sub_dict_ok):
                    debug_err(
                        'Saving a dict in config for {!r}!: {!r}'.format(
                            key,
                            val,
                        ),
                        level=1,
                    )
        config.update(d)
    # debug_obj(dict(config.items()), msg='Saving config:')
    debug('Saving config (items: {}{})'.format(
        len(d or config),
        ' + {} sub-item{}'.format(
            subitemcnt,
            '' if subitemcnt == 1 else 's',
        ) if subitemcnt else '',
    ))
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
        'runs': config_get('runs', 1),
        'runtime_secs': config_get('runtime_secs', 1),
        'master_files': config_get('master_files', 0),
        'tiger_files': config_get('tiger_files', 0),
        'archive_files': config_get('archive_files', 0),
        'unarchive_files': config_get('unarchive_files', 0),
        'remove_files': config_get('remove_files', 0),
        'fatal_errors': config_get('fatal_errors', 0),
    }


def lock_acquire():
    """ Try acquiring the file lock. Raise ValueError if the lock is already
        acquired.
    """
    if os.path.exists(LOCKFILE):
        msg = 'Lock already acquired: {}'.format(LOCKFILE)
        debug(msg, level=1)
        raise ValueError(msg)
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
