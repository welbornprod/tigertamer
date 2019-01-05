#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" tigertamer.py
    Converts Mozaik cutlist files into TigerStop (.tiger) files.
    Mozaik is CSV, TigerStop is XML.
    This bridges the gap between the two so cutlists can be easily created
    from Mozaik.
    -Christopher Welborn 12-15-2018
"""

import os
import sys

from colr import (
    auto_disable as colr_auto_disable,
    Colr as C,
    docopt,
)

from lib.util.config import (
    config,
    VERSIONSTR,
)
from lib.gui.main import load_gui
from lib.util.logger import (
    debug,
    print_err,
    set_debug_mode,
    status,
)
from lib.util.parser import (
    create_xml,
    get_archive_info,
    get_tiger_files,
    load_moz_files,
    unarchive_file,
    write_tiger_file,
)

colr_auto_disable()

SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}

    Converts Mozaik (.dat) CSV files into TigerStop (.tiger) XML files for
    use with the TigerTouch software.

    Usage:
        {script} -h | -v
        {script} -g [-D] -f func
        {script} -g [-r] [-D]
        {script} (-u | -U) [ARCHIVE_DIR] [-D]
        {script} [FILE...] [-i dir...] [-n] [-D]
        {script} [FILE...] [-i dir...] [-o dir [-a dir]] [-D]

    Options:
        ARCHIVE_DIR           : Directory to look for archive files.
        FILE                  : One or more CSV (.dat) files to parse.
        -a dir,--archive dir  : Directory for completed master files.
                                Use - to disable archiving.
                                Disabled when printing to stdout.
        -D,--debug            : Show more info while running.
        -f name, --func name  : Run a function from WinMain for debugging.
        -g,--gui              : Load the Tiger Tamer GUI.
        -i dir,--ignore dir   : One or more directories to ignore when looking
                                for mozaik files.
                                The output and archive directories are
                                included automatically.
        -o dir,--output dir   : Output directory.
                                Use - for stdout output.
        -h,--help             : Show this help message.
        -n,--namesonly        : Just show which files would be generated.
        -r,--run              : Automatically run with settings in config.
        -u,--unarchive        : Undo any archiving, if possible.
        -U,--UNARCHIVE        : Undo any archiving, and remove all output
                                files.
        -v,--version          : Show version.
""".format(script=SCRIPT, versionstr=VERSIONSTR)


def main(argd):
    """ Main entry point, expects docopt arg dict as argd. """
    set_debug_mode(argd['--debug'])
    debug('Debugging enabled.')

    inpaths = argd['FILE'] or config.get('dat_dir', None)
    outdir = (
        argd['--output'] or config.get('tiger_dir', './tigertamer_output')
    )
    archdir = (
        argd['--archive'] or
        config.get('archive_dir', './tigertamer_archive') or
        argd['ARCHIVE_DIR']  # Only valid with -u or -U.
    )
    ignore_dirs = set(argd['--ignore'])
    if outdir and (outdir != '-'):
        ignore_dirs.add(outdir)
    if archdir and (archdir != '-'):
        ignore_dirs.add(archdir)

    if argd['--gui']:
        # The GUI handles arguments differently, send it the correct config.
        return load_gui(
            auto_exit=config.get('auto_exit', False),
            auto_run=argd['--run'],
            geometry=config.get('geometry', ''),
            geometry_report=config.get('geometry_report', ''),
            theme=config.get('theme', ''),
            archive_dir='' if archdir in (None, '-') else archdir,
            dat_dir=inpaths[0] if inpaths else '',
            tiger_dir='' if outdir in (None, '-') else outdir,
            ignore_dirs=tuple(ignore_dirs),
            run_function=argd['--func'],
        )

    if argd['--unarchive'] or argd['--UNARCHIVE']:
        if not options_are_set(inpaths, archdir):
            raise InvalidConfig(
                '.dat dir and archive dir must be set in config.'
            )
        errs = unarchive(inpaths[0], archdir)
        if argd['--unarchive']:
            return errs
        if not options_are_set(outdir):
            raise InvalidConfig(
                'Output directory must be set in config.'
            )
        return remove_tiger_files(outdir)

    # Run in console mode.
    if not inpaths:
        raise InvalidArg('No input files/directories!')
    mozfiles = load_moz_files(
        inpaths,
        ignore_dirs=ignore_dirs,
    )

    parentfiles = set()
    errs = 0
    for mfile in mozfiles:
        parentfiles.add(mfile.parent_file)
        errs += handle_moz_file(
            mfile,
            outdir,
            names_only=argd['--namesonly'],
            archive_dir=archdir,
            )

    parentlen = len(parentfiles)
    status(
        C(' ').join(
            C('Finished with', 'cyan'),
            C(parentlen, 'blue', style='bright'),
            C(' ').join(
                C('master', 'cyan'),
                C('file' if parentlen == 1 else 'files', 'cyan'),
            ),
            C(' ').join(
                C(errs, 'blue', style='bright'),
                C('error' if errs == 1 else 'errors', 'cyan'),
            ).join('(', ')', style='bright'),
        )
    )
    for pfile in sorted(parentfiles):
        debug(pfile, align=True)
    return errs


def handle_moz_file(mozfile, outdir, archive_dir=None, names_only=False):
    """ Handle the processing of one MozaikFile. """
    tigerpath = os.path.join(outdir, mozfile.filename)

    if names_only:
        print(tigerpath)
        return 0
    elif outdir in (None, '-'):
        print(create_xml(mozfile))
        return 0

    return write_tiger_file(mozfile, outdir, archive_dir=archive_dir)


def options_are_set(*args):
    # Returns True if all args have a value, and the '-' flag wasn't used.
    return all(((s and s != '-') for s in args))


def remove_tiger_files(outdir):
    """ Deletes all .tiger files in `outdir`. """
    if not os.path.exists(outdir):
        raise InvalidArg('Output directory doesn\'t exist: {}'.format(
            outdir,
        ))
    try:
        filepaths = get_tiger_files(outdir)
    except OSError as ex:
        print_err(ex)
        return 1

    if not filepaths:
        print_err('No files to remove: {}'.format(outdir))
        return 1

    errs = 0
    success = 0
    for filepath in filepaths:
        try:
            os.remove(filepath)
        except OSError as ex:
            print_err('Can\'t remove file: {}\n{}'.format(filepath, ex))
            errs += 1
        else:
            success += 1
            status('Removed', filepath)

    status(
        'Removed Files',
        '{} ({} {})'.format(
            success,
            errs,
            'Error' if errs == 1 else 'Errors',
        )
    )
    return errs


def unarchive(datdir, archdir):
    """ Unarchive all dat files in `archdir`, and put them in `datdir`. """
    try:
        files = get_archive_info(datdir, archdir)
    except (OSError, ValueError) as ex:
        print_err(ex)
        return 1
    errs = 0
    success = 0
    for src, dest in files:
        try:
            finalpath = unarchive_file(src, dest)
        except OSError as ex:
            print_err(ex)
            errs += 1
        else:
            status('Unarchived', finalpath)
            success += 1
    status(
        'Unarchived Files',
        '{} ({} {})'.format(
            success,
            errs,
            'Error' if errs == 1 else 'Errors',
        )
    )
    return errs


class InvalidArg(ValueError):
    """ Raised when the user has used an invalid argument. """
    def __init__(self, msg=None):
        self.msg = msg or ''

    def __str__(self):
        if self.msg:
            return 'Invalid argument, {}'.format(self.msg)
        return 'Invalid argument!'


class InvalidConfig(InvalidArg):
    def __str__(self):
        if self.msg:
            return self.msg
        return 'Invalid config!'


if __name__ == '__main__':
    try:
        mainret = main(docopt(USAGESTR, version=VERSIONSTR, script=SCRIPT))
    except InvalidArg as ex:
        print_err(ex)
        mainret = 1
    except (EOFError, KeyboardInterrupt):
        print_err('\nUser cancelled.\n')
        mainret = 2
    except BrokenPipeError:
        print_err('\nBroken pipe, input/output was interrupted.\n')
        mainret = 3
    sys.exit(mainret)
