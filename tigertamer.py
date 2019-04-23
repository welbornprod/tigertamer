#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" tigertamer.py - TigerTamer
    Converts Mozaik cutlist files into TigerStop (.tiger) files.
    Mozaik is CSV, TigerStop is XML.
    This bridges the gap between the two so cutlists can be easily created
    from Mozaik.

    Copyright (C) 2019 Christopher Welborn

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program (gpl_v3.txt).
    If not, see <http://www.gnu.org/licenses/>.

    -Christopher Welborn 12-15-2018
"""

import os
import sys
from time import time

from colr import (
    auto_disable as colr_auto_disable,
    Colr as C,
    docopt,
)

from lib.util.config import (
    AUTHOR,
    config_get,
    config_increment,
    lock_acquire,
    lock_release,
    NAME,
    VERSIONSTR,
)
from lib.util.archive import (
    Archive,
    list_archive,
)
from lib.util.format import (
    TigerFile,
    list_labelconfig,
)
from lib.util.logger import (
    debug,
    print_err,
    set_debug_mode,
    status,
)
from lib.util.preview import (
    LargeFileError,
    TigerFiles,
    check_file,
)
from lib.gui.main import (
    list_funcs,
    load_gui,
)
from lib.util.parser import (
    MozaikMasterFile,
    create_xml,
    get_tiger_files,
    load_moz_files,
    write_tiger_file,
)

colr_auto_disable()

SCRIPT = os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}
    Created by: {author}

    Converts Mozaik (.dat) CSV files into TigerStop (.tiger) XML files for
    use with the TigerTouch software.

    Usage:
        {script} (-F | -h | -L | -v) [-D]
        {script} -f func [-e] [-s] [-D]
        {script} -g [-e] [-r] [-s] [-D]
        {script} [-g] -A [-D]
        {script} (-u | -U) [-a dir | ARCHIVE_FILE...] [-D]
        {script} [-g] (-p | -V) FILE... [-D]
        {script} (-m | -M | -t | -T) FILE... [-D]
        {script} [FILE...] [-e] [-i dir...] [-I text...]
                      [-n] [-s] [-D]
        {script} [FILE...] [-e] [-i dir...] [-I text...]
                      [-o dir [-a dir]] [-s] [-D]

    Options:
        ARCHIVE_FILE          : One or more archived file paths to unarchive.
        FILE                  : One or more CSV (.dat) files to parse,
                                or Tiger (.tiger) files to view with -V.
        -A,--ARCHIVE          : List archived files.
        -a dir,--archive dir  : Directory for completed master files, or for
                                unarchiving all files at once.
                                Use - to disable archiving when converting
                                files.
                                Disabled when printing to stdout.
        -D,--debug            : Show more info while running.
        -e,--extra            : Use extra data from Mozaik files.
        -F,--functions        : List all available functions for -f and exit.
        -f name, --func name  : Run a function from WinMain for debugging.
                                This automatically implies -g,--gui.
        -g,--gui              : Load the Tiger Tamer GUI.
        -h,--help             : Show this help message.
        -I str,--IGNORE str   : One or more strings to ignore when looking
                                for mozaik files (applies to full file path).
        -i dir,--ignore dir   : One or more directories to ignore when looking
                                for mozaik files.
                                The output and archive directories are
                                included automatically.
        -L,--labelconfig      : Print label config and exit.
        -M,--MASTERFILE       : Like -m, but separate into width files first.
        -m,--masterfile       : Parse, split parts, combine parts, and then
                                output another Mozaik master file (.dat) to
                                stdout.
        -n,--namesonly        : Just show which files would be generated.
        -o dir,--output dir   : Output directory.
                                Use - for stdout output.
        -p,--preview          : Preview output for a Mozaik (.dat) file.
                                This will not create any Tiger (.tiger) files.
        -r,--run              : Automatically run with settings in config.
        -s,--nosplit          : Do not split parts into single line items.
        -T,--TREE             : Like -t, but separate into width files first.
                                This adjusts the tree to width-first.
        -t,--tree             : Print parts in tree-form.
        -u,--unarchive        : Undo any archiving, if possible.
        -U,--UNARCHIVE        : Undo any archiving, and remove all output
                                files.
        -V,--view             : View a formatted .tiger file in the console,
                                or with the GUI if -g is also used.
        -v,--version          : Show version.
""".format(author=AUTHOR, script=SCRIPT, versionstr=VERSIONSTR)


def main(argd):
    """ Main entry point, parses arguments and dispatches accordingly.
        Arguments:
            argd  : Docopt arg dict.
    """
    set_debug_mode(argd['--debug'])
    debug('Debugging enabled.')
    # Get input paths, with no blanks (mainly for testing error messages).
    argd['FILE'] = [s for s in argd['FILE'] if s.strip()]
    inpaths = argd['FILE'] or config_get('dat_dir', [])
    debug('Input paths for conversion: {}'.format(inpaths))
    if all(s.lower().endswith('.tiger') for s in inpaths):
        # If all input files are tiger files, --view is implicit.
        argd['--view'] = True

    outdir = (
        argd['--output'] or config_get('tiger_dir', './tigertamer_output')
    )
    archdir = (
        argd['--archive'] or
        config_get('archive_dir', './tigertamer_archive')
    )
    ignore_dirs = set(config_get('ignore_dirs', []))
    ignore_dirs.update(set(argd['--ignore']))
    ignore_strs = set(config_get('ignore_strs', []))
    ignore_strs.update(set(argd['--IGNORE']))

    if outdir and (outdir != '-'):
        ignore_dirs.add(outdir)
    if archdir and (archdir != '-'):
        ignore_dirs.add(archdir)

    # Handle config/arg flags.
    argd['--extra'] = config_get('extra_data', argd['--extra'])
    argd['--nosplit'] = config_get('no_part_split', argd['--nosplit'])
    if argd['--gui'] and argd['--ARCHIVE']:
        # Little hack to force calling `cmd_menu_unarchive` on load.
        argd['--func'] = 'cmd_menu_unarchive'

    if argd['--gui'] or argd['--func']:
        # The GUI handles arguments differently, send it the correct config.
        if argd['--view'] or argd['--preview']:
            # Supply input paths from config. They won't be used.
            # It keeps the GUI from overwriting the last known dat dir
            # when viewing/previewing files.
            inpaths = config_get('dat_dir', [])
            debug('Input paths reloaded/saved: {}'.format(inpaths))
        return load_gui(
            auto_exit=config_get('auto_exit', False),
            auto_run=argd['--run'],
            extra_data=argd['--extra'],
            no_part_split=argd['--nosplit'],
            geometry=config_get('geometry', ''),
            geometry_about=config_get('geometry_about', ''),
            geometry_labels=config_get('geometry_labels', ''),
            geometry_report=config_get('geometry_report', ''),
            geometry_unarchive=config_get('geometry_unarchive', ''),
            geometry_viewer=config_get('geometry_viewer', ''),
            theme=config_get('theme', ''),
            archive_dir='' if archdir in (None, '-') else archdir,
            dat_dir=inpaths[0] if inpaths else '',
            tiger_dir='' if outdir in (None, '-') else outdir,
            ignore_dirs=tuple(ignore_dirs),
            ignore_strs=tuple(ignore_strs),
            run_function=argd['--func'],
            tiger_files=argd['FILE'] if argd['--view'] else None,
            preview_files=argd['FILE'] if argd['--preview'] else None,
        )

    # Console mode, need a lock.
    try:
        lock_acquire()
    except ValueError:
        print_err('{} already running.'.format(NAME))
        return 3

    if argd['--ARCHIVE']:
        # List archive files.
        return list_archive(archdir, inpaths[0])

    if argd['--functions']:
        # List functions available for -f.
        return list_funcs()

    if argd['--labelconfig']:
        # List label config being used.
        return list_labelconfig()

    if argd['--masterfile'] or argd['--MASTERFILE']:
        return view_lines_files(
            argd['FILE'],
            separate_widths=argd['--MASTERFILE']
        )

    if argd['--preview']:
        # Preview a .dat file as a .tiger file.
        return preview_files(argd['FILE'])

    if argd['--tree'] or argd['--TREE']:
        return view_tree_files(argd['FILE'], separate_widths=argd['--TREE'])

    if argd['--view']:
        # View a tiger file.
        return view_tigerfiles(argd['FILE'])

    if argd['--unarchive'] or argd['--UNARCHIVE']:
        if not (argd['ARCHIVE_FILE'] or options_are_set(inpaths, archdir)):
            raise InvalidConfig(
                '.dat dir and archive dir must be set in config.'
            )
        errs = unarchive(inpaths[0], archdir, filepaths=argd['ARCHIVE_FILE'])
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

    time_start = time()

    mozfiles = load_moz_files(
        inpaths,
        ignore_dirs=ignore_dirs,
        ignore_strs=ignore_strs,
        split_parts=not argd['--nosplit'],
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
            extra_data=argd['--extra'],
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
        debug('Parent file: {}'.format(pfile))

    config_increment(
        master_files=parentlen,
        tiger_files=len(mozfiles),
        runs=1,
        runtime_secs=time() - time_start,
        default=0,
    )
    return errs


def confirm(s, default=False):
    """ Confirm a yes/no question. """
    if default:
        defaultstr = C('/', style='bright').join(
            C('Y', 'green'),
            C('n', 'red')
        )
    else:
        defaultstr = C('/', style='bright').join(
            C('y', 'green'),
            C('N', 'red')
        )
    s = '{} ({}): '.format(C(s, 'cyan'), defaultstr)
    try:
        answer = input(s).strip().lower()
    except EOFError:
        # Handled at the end of this script.
        raise
    if answer:
        return answer.startswith('y')

    # no answer, return the default.
    return default


def handle_moz_file(
        mozfile, outdir,
        archive_dir=None, names_only=False, extra_data=False):
    """ Handle the processing of one MozaikFile. """
    tigerpath = os.path.join(outdir, mozfile.filepath)

    if names_only:
        print(tigerpath)
        return 0
    elif outdir in (None, '-'):
        print(create_xml(mozfile, extra_data=extra_data))
        return 0

    return write_tiger_file(
        mozfile,
        outdir,
        archive_dir=archive_dir,
        extra_data=extra_data,
    )


def options_are_set(*args):
    # Returns True if all args have a value, and the '-' flag wasn't used.
    return all(((s and s != '-') for s in args))


def preview_file(filepath):
    """ Preview a Mozaik file as a Tiger file. """
    try:
        check_file(filepath)
    except LargeFileError as ex:
        msg = '\n'.join((
            str(C(ex)),
            '',
            str(C('Continue anyway?', 'cyan')),
        ))
        if not confirm(msg):
            return 1
    return TigerFiles.from_file(filepath, split_parts=True).print()


def preview_files(filepaths):
    """ Preview multiple Mozaik files as Tiger files. """
    return sum(preview_file(s) for s in filepaths)


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
    config_increment(remove_files=success, default=0)
    return errs


def unarchive(datdir, archdir=None, filepaths=None):
    """ Unarchive all dat files in `archdir`, and put them in `datdir`. """
    if not (archdir or filepaths):
        print_err('No file paths or archive directory specified!')
        return 1

    try:
        # Known archived files.
        archive = Archive(archdir, datdir)
    except (OSError, ValueError) as ex:
        print_err(ex)
        return 1
    if filepaths:
        filepath_errs = 0
        for filepath in filepaths:
            if filepath not in archive:
                print_err('Not an archived file: {}'.format(filepath))
                filepath_errs += 1
        if filepath_errs:
            return filepath_errs

    errs = 0
    success = 0
    for archfile in archive.files:
        if filepaths and (archfile.filepath not in filepaths):
            debug('Archive file not selected: {}'.format(archfile.filepath))
            continue
        try:
            archfile.unarchive()
        except OSError as ex:
            print_err(ex)
            errs += 1
        else:
            status('Unarchived', archfile.dest_path)
            success += 1
    status(
        'Unarchived Files',
        '{} ({} {})'.format(
            success,
            errs,
            'Error' if errs == 1 else 'Errors',
        )
    )
    config_increment(unarchive_files=success, default=0)
    return errs


def view_lines_file(filepath, separate_widths=False):
    """ Parse a master file, with part splitting/combining, and then
        print it out.
    """
    masterfile = MozaikMasterFile.from_file(filepath, split_parts=True)
    if separate_widths:
        mozfiles = masterfile.into_width_files()
        for mozfile in mozfiles:
            tree = mozfile.tree()
            for line in tree.to_lines():
                print(line)
        return 0 if mozfiles else 1

    # Whole master file.
    tree = masterfile.tree()
    for line in tree.to_lines():
        print(line)
    return 0 if tree else 1


def view_lines_files(filepaths, separate_widths=False):
    """ Parse several master files, with part splitting/combining, and then
        print them out.
    """
    return sum(
        view_lines_file(s, separate_widths=separate_widths)
        for s in filepaths
    )


def view_tigerfile(filepath):
    """ View a single tiger file in the console.
        Returns an exit status code.
    """
    if not filepath:
        raise ValueError('No filepath provided!')
    if not filepath.lower().endswith('.tiger'):
        raise InvalidArg('not a valid tiger file: {}'.format(filepath))
    tf = TigerFile.from_file(filepath)
    return 0 if tf.print() else 1


def view_tigerfiles(filepaths):
    """ View tiger files in the console.
        Returns an exit status code.
    """
    return sum(view_tigerfile(s) for s in filepaths)


def view_tree_file(filepath, separate_widths=False):
    """ View a Mozaik file as a tree of parts. """
    masterfile = MozaikMasterFile.from_file(filepath, split_parts=True)
    if separate_widths:
        mozfiles = masterfile.into_width_files()
        for mozfile in mozfiles:
            tree = mozfile.tree()
            tree.print()
        return 0 if mozfiles else 1
    # Whole master file.
    tree = masterfile.tree()
    tree.print()
    return 0 if tree else 1


def view_tree_files(filepaths, separate_widths=False):
    """ View multiple Mozaik files as a tree of parts. """
    return sum(
        view_tree_file(s, separate_widths=separate_widths)
        for s in filepaths
    )


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


def entry_point(argv=None):
    """ Actual entry point for execution, wrapped in a function for testing.
    """
    try:
        mainret = main(docopt(
            USAGESTR,
            argv=argv or sys.argv[1:],
            version=VERSIONSTR,
            script=SCRIPT,
        ))
    except InvalidArg as ex:
        print_err(ex)
        mainret = 1
    except FileNotFoundError as ex:
        print_err('File not found: {}'.format(ex.filename))
        mainret = 2
    except (EOFError, KeyboardInterrupt):
        print_err('\nUser cancelled.\n')
        mainret = 2
    except BrokenPipeError:
        print_err('\nBroken pipe, input/output was interrupted.\n')
        mainret = 3
    finally:
        lock_release()
    sys.exit(mainret)


if __name__ == '__main__':
    entry_point()
