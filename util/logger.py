#!/usr/bin/env python3

""" tigertamer - util/logger.py
    Provides a global debug logger for TigerTamer.
    -Christopher Welborn 12-15-2018
"""

import json
import logging
import os
import sys
import traceback
from contextlib import suppress
from platform import platform

from colr import (
    auto_disable as colr_auto_disable,
    Colr as C,
)

from printdebug import get_lineinfo

if 'linux' in platform().lower():
    from printdebug import DebugColrPrinter as DebugPrinter
else:
    from printdebug import DebugPrinter


colr_auto_disable()

SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

LOGFILE = os.path.join(SCRIPTDIR, 'tigertamer.log')
DEBUG = False
debugprinter = DebugPrinter()
if not getattr(debugprinter, 'debug_err'):
    # Fixing old version of printdebug.
    def polyfill_debug_err(*args, **kwargs):
        kwargs['level'] = kwargs.get('level', 0) + 1
        args = (
            a if isinstance(a, C) else C(a, 'red')
            for a in args
        )
        return debugprinter.debug(*args, **kwargs)
    debugprinter.debug_err = polyfill_debug_err

logger = logging.getLogger('tigertamer')

formatter = logging.Formatter(
    '[%(levelname)s] %(message)s'
)
formatter.default_time_format = '%m-%e-%y'  # '%I:%M:%S%p'

filehandler = logging.FileHandler(filename=LOGFILE, mode='w')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)
logger.setLevel(logging.ERROR)


def _debug(*args, **kwargs):
    iserror = False
    with suppress(KeyError):
        iserror = kwargs.pop('is_error')
    kwargs['level'] = kwargs.get('level', 0) + 1
    if sys.stderr.isatty():
        if iserror:
            debugprinter.debug_err(*args, **kwargs)
        else:
            debugprinter.debug(*args, **kwargs)

    msg = fix_log_msg(*args, level=kwargs['level'])
    if iserror:
        logger.error(msg)
    else:
        logger.debug(msg)


def debug(*args, **kwargs):
    kwargs['level'] = kwargs.get('level', 0) + 1
    return _debug(*args, **kwargs)


def debug_attrs(o):
    """ Debug-print public attributes of an object. """
    Nothing = object()
    debug('Attributes for: {!r}'.format(
        type(o).__name__,
        o,
    ))
    for attrname in (s for s in dir(o) if not s.startswith('_')):
        try:
            attr = getattr(o, attrname)
        except Exception as ex:
            debug_err('Cannot get attr value for {}: {}'.format(
                type(o).__name__,
                ex,
            ))
            attr = Nothing
        else:
            if callable(attr):
                attrname = '{}()'.format(attrname)

        debug(
            '{:>20}: {!r}'.format(
                attrname,
                '<Nothing>' if attr is Nothing else attr,
            ),
            align=True
        )


def debug_err(*args, **kwargs):
    kwargs['is_error'] = True
    kwargs['level'] = kwargs.get('level', 0) + 1
    return _debug(*args, **kwargs)


def debug_exc(msg=None, suppress=None, suppress_strs=None):
    """ Print a formatted traceback for the last exception, if there is any.
        Arguments:
            msg            : Optional message to print before the traceback.
            suppress       : An iterable of exceptions to ignore.
                             If the last exception type is found in `suppress`
                             it will not be debug-printed.
            suppress_strs  : An iterable of strings. If str(last_exception)
                             contains any of these strings, it will not be
                             debug-printed.
    """
    if not debugprinter.enabled:
        # No debugging exceptions when debug is disabled.
        return None
    # Show actual exception tracebacks.
    ex_type, ex_value, ex_tb = sys.exc_info()
    if suppress and (ex_type in suppress):
        # Ignore this exception type.
        return None
    elif suppress_strs:
        if str_contains(str(ex_value), suppress_strs):
            # Exception message matched a substring, don't debug it.
            return None
    if any((ex_type, ex_value, ex_tb)):
        if msg:
            debug(msg, level=1)
        debug(
            ''.join(
                traceback.format_exception(ex_type, ex_value, ex_tb)
            ),
            level=1,
        )


def debug_obj(o, msg=None, is_error=False):
    """ Pretty print an object, using JSON. """
    alignfirst = False
    debugfunc = debug_err if is_error else debug
    if msg:
        debugfunc(msg, level=1)
        alignfirst = True

    try:
        # Try sorting first.
        lines = json.dumps(o, indent=4, sort_keys=True).split('\n')
    except (TypeError, ValueError):
        try:
            lines = json.dumps(o, indent=4).split('\n')
        except (TypeError, ValueError) as ex:
            # Not serializable, just use repr.
            debug_err('Can\'t serialize object: ({}) {!r}'.format(
                type(o).__name__,
                o,
            ))
            debug_err('Error was: {}'.format(ex))
            lines = [repr(o)]

    for i, s in enumerate(lines):
        debugfunc(s, level=1, align=(i > 0) or alignfirst)


def fix_log_msg(*args, **kwargs):
    # Since I'm wrapping the logger.debug() call, func name and line num is
    # lost. I'm prepending that info to the beginning of the message.
    lineinfo = get_lineinfo(level=kwargs['level'] + 1)
    _, filename = os.path.split(lineinfo.filename)
    filename = '{:>16}'.format(filename)
    funcname = '{:>24}'.format(
        lineinfo.name
        if '<' in lineinfo.name
        else '{}()'.format(lineinfo.name)
    )
    lineno = '{:>5}'.format(lineinfo.lineno)
    funcinfo = ':'.join((filename, lineno, funcname))
    msg = ' '.join(str(a) for a in args)
    return ': '.join((funcinfo, msg))


def get_debug_mode():
    """ Access DEBUG and debugprinter.enabled """
    return DEBUG or getattr(debugprinter, 'enabled', False)


def pop_or(dct, key, default=None):
    """ Like dict.get, except it pops the key afterwards.
        This also works for lists and sets.
    """
    val = default
    with suppress(IndexError, KeyError, TypeError):
        val = dct.pop(key)
    return val


def print_err(*args, **kwargs):
    """ A wrapper for print() that uses stderr by default. """
    ignore_excs = pop_or(kwargs, 'suppress_exc', set())

    if kwargs.get('file', None) is None:
        kwargs['file'] = sys.stderr

    color = pop_or(kwargs, 'color', True)
    logmsg = kwargs.get('sep', ' ').join(
        str(a.stripped() if isinstance(a, C) else a)
        for a in args
    )
    # Use color if asked, but only if the file is a tty.
    if color and kwargs['file'].isatty():
        # Keep any Colr args passed, convert strs into Colrs.
        msg = kwargs.get('sep', ' ').join(
            str(a) if isinstance(a, C) else str(C(a, 'red'))
            for a in args
        )
    else:
        # The file is not a tty anyway, no escape codes.
        msg = logmsg
    newline = pop_or(kwargs, 'newline', False)
    if newline:
        msg = '\n{}'.format(msg)

    print(msg, **kwargs)
    logger.error(logmsg)

    # Debug any exceptions that were not suppressed.
    ex_type, _, _ = sys.exc_info()
    if (ignore_excs != 'all') and (ex_type not in ignore_excs):
        debug_exc()


def set_debug_mode(enabled):
    global DEBUG, debugprinter, logger
    DEBUG = enabled
    debugprinter.enable(DEBUG)
    logger.setLevel(
        logging.DEBUG if DEBUG else logging.INFO
    )
    if (not DEBUG) and (not set_debug_mode.warned):
        logger.critical('Only errors will be logged...')
        set_debug_mode.warned = True
    logger.info('Debug mode set: {}'.format(enabled))


set_debug_mode.warned = False


def status(label=None, msg=None):
    """ Print a status message if running in the console, and log it also. """
    if msg:
        line = C(': ').join(
            C(label, 'blue'),
            C(msg, 'cyan'),
        )
    else:
        line = C(label, 'cyan')
    if sys.stdout.isatty():
        print(line)
    logger.info(fix_log_msg(line.stripped(), level=1))


def str_contains(s, substrs):
    """ Returns True if the str `s` contains any substrings in `substrs`.
        Like `substr in s`, except you can use an iterable of strings instead
        if just one.

        Arguments:
            s        : The string to search.
            substrs  : An iterable of substrings to find.
    """
    if isinstance(substrs, str):
        # Not supposed to pass a str in, but okay.
        return (substrs in s)
    try:
        return any((substr in s) for substr in substrs)
    except TypeError:
        raise ValueError(': '.join((
            'Expecting an iterable of `str` for `substr`, got',
            type(substrs).__name__,
        )))
    return False
