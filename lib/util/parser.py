#!/usr/bin/env python3

""" tigertamer - lib/util/parser.py
    CSV (.dat) parser to XML (.tiger) creator for TigerTamer.
    -Christopher Welborn 12-15-2018
"""

import csv
import os
import re
import shutil
import sys
from collections import UserDict
from contextlib import suppress

from colr import (
    auto_disable as colr_auto_disable,
    Colr as C,
)

from .config import (
    config_increment,
)
from .logger import (
    debug,
    debug_err,
    print_err,
    status,
)
from .format import create_xml

colr_auto_disable()

# Pattern to grab multiple cab quantities from a room/cab number.
cab_count_pat = re.compile(r'R?\d{1,3}?\:?\d{1,3}?\((\d{1,3})\)')
# Pattern to grab one or more quantities from a room/cab number.
cab_multi_count_pat = re.compile(r'\((\d{1,3})\)')

# Char for splitting/re-joining archive file paths.
archive_split_char = '__'


def archive_parent_file(datfile, archive_dir):
    """ Move the parent file of this MozaikFile to the archive dir,
        if not already done.
    """
    parentdir, parentname = os.path.split(datfile.parent_file)
    _, parentsubdir = os.path.split(parentdir)
    newparentname = archive_split_char.join((parentsubdir, parentname))
    archpath = os.path.join(archive_dir, newparentname)
    if not os.path.exists(datfile.parent_file):
        if os.path.exists(archpath):
            debug('Already archived: {}'.format(archpath))
            return 0
        debug_err('Missing parent file: {}'.format(datfile.parent_file))
        return 1

    # Create archive dir if needed.
    if not os.path.isdir(archive_dir):
        try:
            os.mkdir(archive_dir)
        except EnvironmentError as ex:
            print_err('Failed to create archive dir: {}'.format(ex))
            return 1
        else:
            debug('Created archive directory: {}'.format(archive_dir))

    # Move master file to archive.
    try:
        destfile = safe_move(datfile.parent_file, archpath)
    except EnvironmentError as ex:
        print_err('Failed to copy master file: {}\n{}'.format(
            datfile.parent_file,
            ex,
        ))
        return 1
    else:
        status('Archived', destfile)
        config_increment(archive_files=1, default=0)

    return remove_dir_if_empty(parentdir)


def get_archive_info(datdir, archdir):
    """ Get all file paths in the archive directory, and where they would
        be restored to.
        Returns [(archivefile, restoretofile), ...]
    """
    try:
        archfiles = os.listdir(archdir)
        origpaths = (os.path.join(archdir, s) for s in archfiles)
    except OSError as ex:
        raise OSError('Unable to unarchive files!: ({}) {}'.format(
            type(ex).__name__,
            ex,
        )) from ex

    if not archfiles:
        raise ValueError('No files to unarchive.')

    relpathpcs = (
        s.rsplit(archive_split_char, 1)
        for s in archfiles
    )
    relpaths = []
    datdirparent, datdirsub = os.path.split(datdir)
    if not datdirsub:
        datdirsub = datdirparent

    for relpathpc in relpathpcs:
        try:
            subdir, name = relpathpc
        except ValueError:
            debug_err('Not a valid archive file name: {!r}'.format(relpathpc))
            continue
        if datdirsub.endswith(subdir):
            relpaths.append(name)
        else:
            relpaths.append(os.path.join(subdir, name))
    destpaths = (
        os.path.join(datdir, s)
        for s in relpaths
    )
    # Sort files by destination path, for printing status.
    return sorted(
        zip(origpaths, destpaths),
        key=lambda tup: tup[1],
    )


def get_dir_files(
        dirpath, ignore_dirs=None, ignore_strs=None, ext='.dat', _level=0):
    """ Loads all MozaikFiles contained in a directory. """
    indent = '  ' * _level
    debug('{}Looking for {} files in: {}'.format(
        indent,
        ext,
        dirpath
    ))
    diritems = [
        os.path.join(dirpath, s)
        for s in os.listdir(dirpath)
    ]
    datfiles = []
    for diritem in diritems:
        ignore = is_ignored_dir(
            diritem,
            ignore_dirs=ignore_dirs,
            ignore_strs=ignore_strs,
        )
        if ignore:
            continue
        if diritem.endswith(ext):
            if is_valid_dat_file(diritem, _indent=indent):
                debug('{}Found {} file: {}'.format(indent, ext, diritem))
                datfiles.append(diritem)
        elif os.path.isdir(diritem):
            datfiles.extend(
                get_dir_files(
                    diritem,
                    ignore_dirs=ignore_dirs,
                    ignore_strs=ignore_strs,
                    ext=ext,
                    _level=_level + 1,
                )
            )
    filelen = len(datfiles)
    debug('Found {} {}.'.format(
        filelen,
        'file' if filelen == 1 else 'files',
    ))
    return datfiles


def get_tiger_files(outdir):
    """ Return a list of .tiger files in a directory. """
    try:
        filepaths = [
            os.path.join(outdir, s)
            for s in sorted(os.listdir(outdir))
            if s.endswith('.tiger')
        ]
    except OSError as ex:
        raise OSError(
            'Can\'t list files in: {}\n{}'.format(outdir, ex)
        ) from ex
    return filepaths


def increment_file_path(path):
    """ Turns file paths like: /dir/filepath.ext into /dir/filepath(2).ext
    """
    numpat = re.compile(r'.+(\(\d+\))\.\w{1,5}$')
    match = numpat.search(path)

    fpath, ext = os.path.splitext(path)
    if (match is None) or (not match):
        # First file.
        newpath = ''.join((fpath, '(1)', ext))
        if os.path.exists(newpath):
            return increment_file_path(newpath)
        return newpath

    # Get the (num) part and strip the parens.
    numpart = match.groups()[0]
    num = int(numpart[1:-1])
    # Rebuild the number, and replace the old one.
    newnum = '({})'.format(num + 1)
    newpath = path.replace(numpart, newnum)
    if os.path.exists(newpath):
        return increment_file_path(newpath)
    return newpath


def is_ignored_dir(dirpath, ignore_dirs=None, ignore_strs=None):
    """ Return True if this `dirpath` should be ignored. """
    if not (ignore_dirs or ignore_strs):
        return False
    if not ignore_dirs:
        ignore_dirs = []
    if ignore_strs:
        ignore_strs = [s.lower() for s in ignore_strs]
    else:
        ignore_strs = []
    dirpathlower = dirpath.lower()
    for s in ignore_strs:
        if s in dirpathlower:
            debug('Ignoring matched string ({!r}): {}'.format(s, dirpath))
            return True

    if dirpath.rstrip('/') in ignore_dirs:
        debug('Ignoring matched dir: {}'.format(dirpath))
        return True
    for ignorepath in ignore_dirs:
        if dirpath.startswith(ignorepath):
            debug('Ignoring partial-match dir: {}'.format(dirpath))
            return True
    return False


def is_valid_dat_file(filepath, _indent=''):
    """ Returns True if this file has the proper column count for a .dat
        file.
    """
    validlen = len(MozaikMasterFile.header)
    with open(filepath, 'r') as f:
        # read only the first line.
        for row in csv.reader([f.readline()]):
            collen = len(row)
            if collen != validlen:
                debug_err(
                    '{}Invalid column count (Need {}, Got {}): {}'.format(
                        _indent,
                        validlen,
                        collen,
                        filepath
                    )
                )
                return False
    return True


def load_moz_file(filepath, split_parts=True):
    """ Loads a single MozaikMasterFile, and splits it into multiple Mozaik
        width files.
    """
    master = MozaikMasterFile.from_file(filepath, split_parts=split_parts)
    debug('Creating width files from: {}'.format(master))
    return master.into_width_files()


def load_moz_files(
        filepaths, ignore_dirs=None, ignore_strs=None,
        ext='.dat', split_parts=True):
    """ Loads multiple MozaikFiles from file names, and returns a list of
        MozaikFiles.
    """
    if isinstance(filepaths, str):
        filepaths = [filepaths]

    files = []
    for filepath in filepaths:
        if os.path.isdir(filepath):
            ignore = is_ignored_dir(
                filepath,
                ignore_dirs=ignore_dirs,
                ignore_strs=ignore_strs,
            )
            if ignore:
                continue
            # A directory, possibly containing .dat files
            # or sub-dirs with .dat files.
            files.extend(
                load_moz_files(
                    get_dir_files(
                        filepath,
                        ignore_dirs=ignore_dirs,
                        ignore_strs=ignore_strs,
                        ext=ext,
                    ),
                    ignore_dirs=ignore_dirs,
                    ignore_strs=ignore_strs,
                    ext=ext,
                    split_parts=split_parts,
                )
            )

        elif filepath.endswith(ext):
            # A mozaik face-frame.dat file.
            files.extend(load_moz_file(filepath, split_parts=split_parts))
        else:
            raise ValueError(
                'Invalid extension for Mozaik CSV file: {}'.format(
                    filepath,
                )
            )
    return files


def remove_dir_if_empty(path):
    """ Remove a directory, if it's empty.
        Returns an exit status code of 0 if everything went well.
        Otherwise it returns 1.
    """
    try:
        files = os.listdir(path)
    except OSError as ex:
        print_err('Unable to list files: {}\n{}'.format(path, ex))
        return 1
    if files:
        debug('Directory not empty: {}'.format(path))
        return 0
    debug('Directory is empty, removing it: {}'.format(path))
    try:
        os.rmdir(path)
    except OSError as ex:
        print_err('Cannot remove dir: {}\n{}'.format(path, ex))
        return 1
    debug('Removed directory: {}'.format(path))
    return 0


def safe_move(src, dest):
    """ Move a file, using shutil.copy2 without overwriting existing files.
        This function will rename the destination file to avoid clobbering.
    """
    # Don't clobber existing archives just because of poor naming.
    if os.path.exists(dest):
        dest = increment_file_path(dest)
        debug('Renaming file: {}'.format(dest))
    return shutil.move(src, dest)


def strip_words(s, words):
    """ Strip several words from a string. """
    pat = '|'.join('({})'.format(word) for word in words)
    return re.sub(pat, '', s)


def trim_cab_count(cabno):
    return re.sub(r'\(\d{1,3}\)', '', cabno)


def unarchive_file(src, dest):
    """ Unarchive a .dat file, restoring it to it's destination.
        Returns the destination path on success.
    """
    destdir = os.path.dirname(dest)
    if not os.path.exists(destdir):
        try:
            debug('Creating directory: {}'.format(destdir))
            os.mkdir(destdir)
        except OSError as ex:
            raise OSError(
                'Cannot create directory: {}\n{}'.format(destdir, ex)
            ) from ex
        else:
            debug('Created directory: {}'.format(destdir))
    try:
        shutil.move(src, dest)
    except OSError:
        msg = '\n'.join((
            'Unable to unarchive/move file:',
            '{src}',
            '-> {dest}',
        )).format(src=src, dest=dest)
        raise ValueError(msg)
    else:
        debug('Moved {} -> {}'.format(src, dest))
    return dest


def write_tiger_file(
        mozfile, outdir, archive_dir=None, extra_data=False,
        error_cb=None, success_cb=None):
    """ Write a .tiger file from a MozaikFile.
        Without callbacks given, it returns an exit status (0 or 1).
        With callbacks it returns `error_cb(mozfile, msg)` or
        `success_cb(mozfile, tigerpath)`

    """
    tigerpath = os.path.join(outdir, mozfile.filepath)
    use_err_cb = callable(error_cb)
    use_success_cb = callable(success_cb)

    if os.path.exists(tigerpath):
        debug_err('Tiger file already exists: {}'.format(tigerpath))
        tigerpath = increment_file_path(tigerpath)
        debug_err('Made new tiger file path: {}'.format(tigerpath))
    try:
        with open(tigerpath, 'w') as f:
            f.write(create_xml(mozfile, extra_data=extra_data))
    except EnvironmentError as ex:
        msg = 'Cannot write tiger file: {}\n{}'.format(
            tigerpath,
            ex,
        )
        print_err(msg)
        return error_cb(mozfile, msg) if use_err_cb else 1
    partlen = len(mozfile.parts)
    plural = 'part' if partlen == 1 else 'parts'
    msg = C(' ').join(
        C('Created', 'blue'),
        C(partlen, 'blue', style='bright'),
        C(plural, 'blue'),
        C('parts in', 'blue'),
    )
    status(msg, tigerpath)
    if archive_dir in (None, '', '-'):
        # No archiving was requested/set.
        debug('No archiving {}.'.format(
            'requested' if archive_dir == '-' else 'set up',
        ))
        return success_cb(mozfile, tigerpath) if use_success_cb else 0
    if outdir in (None, '-'):
        debug('Archiving disabled due to output style.')
        return success_cb(mozfile, tigerpath) if use_success_cb else 0
    exitstatus = archive_parent_file(mozfile, archive_dir)
    return success_cb(mozfile, tigerpath) if use_success_cb else exitstatus


class MozaikMasterFile(object):
    """ Parses Mozaik .dat files and holds information about the file. """
    header = ('count', 'width', 'length', 'type', 'no', 'extra_data')
    count = 0

    def __init__(self, filepath=None, parts=None):
        self.filepath = filepath or None
        self.parts = parts or []
        self.count = sum(p.count for p in self.parts)

    def __bool__(self):
        """ A MozaikMasterFile is truthy if it has parts. """
        return bool(self.parts)

    def __len__(self):
        """ The length MozaikMasterFile is the length of it's parts. """
        return len(self.parts)

    def __repr__(self):
        """ Stringify this MozaikMasterFile for debug printing. """
        lines = [str(self)]

        if self.parts:
            lines.extend(
                '    {}'.format(p)
                for p in sorted(self.parts, key=lambda prt: prt.no)
            )
        else:
            lines.append('    <Empty>')
        return '\n'.join(lines)

    def __str__(self):
        keys = 'count={s.count}, filepath={s.filepath!r},'.format(s=self)
        return '{}({}):'.format(
            type(self).__name__,
            keys,
        )

    @classmethod
    def from_file(cls, filepath, split_parts=True):
        """ Creates a MozaikMasterFile, and loads/parses a file to
            populate it.
        """
        mp = cls()
        mp.parse(filepath, split_parts=split_parts)
        return mp

    @classmethod
    def from_line(cls, line, filepath=None, split_parts=True):
        """ Parse a single line from a Mozaik .dat file into a
            MozaikMasterFile with optional filepath.
        """
        parts = cls.parse_row(line.split(','), split_parts=split_parts)
        return cls(filepath=filepath, parts=parts)

    @classmethod
    def from_lines(cls, lines, filepath=None, split_parts=True):
        """ Parse a single line from a Mozaik .dat file into a
            MozaikMasterFile with optional filepath.
        """
        parts = []
        for line in lines:
            parts.extend(
                cls.parse_row(line.split(','), split_parts=split_parts)
            )
        return cls(filepath=filepath, parts=parts)

    def parse(self, filepath, split_parts=True):
        """ Parses a Mozaik CSV (.dat) file, and populates the
            MozaikMasterFile class.
        """
        debug('Parsing: {}'.format(filepath))
        self.filepath = filepath
        with open(filepath) as f:
            for row in csv.reader(f):
                parts = self.parse_row(row, split_parts=split_parts)
                self.count += sum(p.count for p in parts)
                self.parts.extend(parts)
        debug('Parsed into: {}'.format(self))
        return self

    @classmethod
    def parse_row(cls, row, split_parts=True):
        """ Parse a list/row of part info into a list of parts.
            The list can come from csv.reader() or s.split(','), as long
            as len(row) == len(self.header).
            Returns [MozaikMasterPart(), ..]
        """
        rowlen = len(row)
        if len(row) != len(cls.header):
            raise ValueError('Invalid number of columns: ({}) {!r}'.format(
                rowlen,
                row,
            ))
        partinfo = {
            cls.header[i]: value
            for i, value in enumerate(row)
        }
        partinfo['count'] = int(partinfo['count'])
        parts = []
        part = MozaikMasterPart(partinfo)
        if split_parts:
            parts.extend(part.split_parts())
        else:
            parts.append(part)
        return parts

    def into_width_files(self):
        """ Split this MozaikMasterFile into seperate MozaikFiles, each
            with their own width.
        """
        if not self.parts:
            return []
        filedata = {}
        for part in self.parts:
            newpart = MozaikPart({
                field: getattr(part, field) for field in MozaikFile.header
            })
            if filedata.get(part.width, None) is None:
                # New width file.
                filedata[part.width] = MozaikFile(self.filepath, part.width)
            # Append part to this width file.
            filedata[part.width].parts.append(newpart)
            filedata[part.width].count += newpart.count

        mozfiles = [filedata[width] for width in sorted(filedata)]
        for mozfile in mozfiles:
            mozfile.parent_file = self.filepath
            mozfile.combine_parts()

        mozfilecount = sum(mozfile.count for mozfile in mozfiles)
        if self.count == mozfilecount:
            debug('Part count is same: Master={}, MozFiles={}'.format(
                self.count,
                mozfilecount,
            ))
        else:
            debug_err('Part count is off: Master={}, MozFiles={}'.format(
                self.count,
                mozfilecount,
            ))

        return mozfiles

    def to_csv(self):
        """ Convert to csv file. """
        return '\n'.join(p.to_csv() for p in self.parts)

    def tree(self):
        """ Return a tree/dict of parts for this master file. """
        tree = MozaikPartTree({}, label='room', filepath=self.filepath)
        for part in self.parts:
            parttree = part.tree()
            tree.update(parttree)

        return tree


class MozaikFile(object):
    """ Holds a Mozaik file of a predetermined width. """
    header = ('count', 'length', 'type', 'no', 'extra_data')
    count = 0

    def __init__(self, filepath, width):
        """ Initialize a MozaikFile of a certain width from keys/values. """
        self.width = width or 0
        self.filepath = self.fix_filepath(filepath, width)
        self.parts = []
        # This is set by the parent 'MozaikMasterFile' that creates these.
        self.parent_file = None

    def __bool__(self):
        """ A MozaikFile is truthy if it has parts. """
        return bool(self.parts)

    def __len__(self):
        """ The length MozaikFile is the length of it's parts. """
        return len(self.parts)

    def __repr__(self):
        """ Stringify this MozaikFile for debug printing. """
        lines = [str(self)]
        if self.parts:
            lines.extend(
                '    {}'.format(p)
                for p in sorted(self.parts, key=lambda prt: prt.no)
            )
        else:
            lines.append('    <Empty>')
        return '\n'.join(lines)

    def __str__(self):
        keys = ', '.join((
            'count={s.count}',
            'width={s.width}',
            'filepath={s.filepath!r}',
        )).format(s=self)
        return '{}({}):'.format(
            type(self).__name__,
            keys,
        )

    def combine_parts(self):
        """ Combine parts that are the same, but have 2 line items for
            some reason.
        """
        # Look for single lines, with a matching multi line:
        # like: 1,5,TR,R1:1
        #       2,5,TR,R1:1(2)
        # and combine them into: 3,5,TR,R1:1(3)
        debug('Combining parts in: {}'.format(self))
        length = len(self)
        tree = self.tree()
        self.parts = tree.to_mozaikparts()
        debug('Parts combined: {}'.format(length - len(self)), align=True)

    def fix_filepath(self, filepath, width):
        """ Fix the file name to contain more information. """
        jobname = self.job_name_from_path(filepath)

        _, fname = os.path.split(filepath)
        fname, _ = os.path.splitext(fname)
        fname = strip_words(
            fname,
            (
                r'\(Face Frames\)',
                r'3-4 Maple Board'
            )
        )

        if jobname and (not fname):
            # Managed to guess job name from dir.
            if filepath not in self.fix_filepath.reported:
                debug_err(
                    'No good file name, using job name: {!r}'.format(jobname)
                )
                self.fix_filepath.reported.add(filepath)
            fname = jobname
            jobname = None
        elif not (jobname or fname):
            # No good job name or dir name.
            if filepath not in self.fix_filepath.reported:
                debug_err(
                    'No good file name or job name: {}'.format(filepath)
                )
                self.fix_filepath.reported.add(filepath)
            fname = 'Unknown Job'
            jobname = None
        if jobname:
            fname = ' '.join((jobname, fname)).strip()
        else:
            fname = fname.strip()
        return '{}[{}in]{}'.format(fname or '', width, '.tiger')

    fix_filepath.reported = set()

    @staticmethod
    def job_name_from_path(filepath):
        """ Try to get the 'job name' portion of the file path. """
        fpath, fname = os.path.split(filepath)
        _, jobdir = os.path.split(fpath)
        words = ('cutlists', 'tigerstop')
        return strip_words(jobdir.lower(), words).strip().title()

    def tree(self):
        """ Return a tree/dict of parts for this file. """
        tree = MozaikPartTree({}, label='room')
        for part in self.parts:
            parttree = part.tree()
            tree.update(parttree)

        return MozaikPartTree(
            {self.width: tree},
            label='width',
            filepath=self.filepath,
        )


class MozaikMasterPart(object):
    """ Holds info about a single part to be cut. """
    header = MozaikMasterFile.header

    # Corrections/replacements for certain values (for certain attributes).
    value_map = {
        'type': {
            '{Drawer Front Size}': 'Drawer Front',
        },
    }

    def __init__(self, data):
        # Set attributes based on the header.
        for field in self.header:
            setattr(self, field, None)

        try:
            # Dict of {field: value}?
            for k, v in data.items():
                if k not in self.header:
                    raise ValueError(
                        'Initialized with unknown header: {!r}={!r}'.format(
                            k,
                            v,
                        )
                    )
                replacements = self.value_map.get(k, None)
                if replacements:
                    val = self.value_map[k].get(v, v)
                else:
                    val = v
                with suppress(AttributeError):
                    val = val.strip()
                setattr(self, k, val)
        except AttributeError as ex:
            debug_err('Not a dict: {} ({})'.format(
                type(data).__name__,
                ex,
            ))
            raise TypeError('Expected dict, got: {}'.format(
                type(data).__name__,
            ))
        try:
            self.count = int(self.count)
        except (TypeError, ValueError):
            raise ValueError(
                'Expected str/int for count, got: {}'.format(
                    type(data['count'])
                ),
            )
        # Fix cab no? This may be deleted in the future.
        cabno = getattr(self, 'no', None)
        if not cabno:
            if cabno is None:
                debug_err('No cab number at all:')
            else:
                debug_err('Empty cab number:')
            debug_err(self, align=True)
            self.no = ''
        self.fix_cab_count()

    def __bool__(self):
        return any(getattr(self, k, None) for k in self.header)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        """ String representation of this MozaikMasterPart. """
        return str(self)

    def __str__(self):
        """ Stringify this MozaikMasterPart for debug printing. """
        clsname = type(self).__name__
        if not self:
            return '{}()'.format(clsname)
        items = ', '.join((
            '{}={}'.format(k, repr(getattr(self, k)))
            for k in self.header
        ))
        return '{}({})'.format(clsname, items)

    def copy(self):
        """ Return a copy of this instance. """
        data = {
            field: getattr(self, field)
            for field in self.header
        }
        return self.__class__(data)

    def find_similar(self, parts):
        """ Yield all similar parts to this one from the `parts` list. """
        yield from (p for p in parts if self.similar_part(p))

    def fix_cab_count(self):
        """ Make sure multi-room/multi-cab parts have a correct count.
            For a single-room/single-cab part a count > 1 may be valid,
            but for multi-room/multi-cab mozaik must be specific, by marking
            the duplicate parts with (n).
            If this is a multi-room/multi-cab part, self.count will be set
            to the actual cab count including any (n) markers.
        """
        if not self.has_multi():
            return None
        # Only "fix" the cab count for multiple rooms/cabs.
        # Having a count > 1 for a single part is a valid use case.
        # However, with multiple rooms/cabs the count must match the
        # rooms + cab_count (n), otherwise a user wouldn't know
        # which part is supposed to be duplicated.
        #   3,<width>,<length>,<type>,R1:1,<extra>      <- Valid
        #   3,<width>,<length>,<type>,R1:1 R2:2,<extra> <- Invalid
        # ...The second case causes confusion. Which part has a count
        #    of two?
        # Mozaik usually does the right thing and marks the cab num:
        #   3,<width>,<length>,<type>,R1:1 R2:2(2),<extra>
        # ...but it still may count the parts wrong:
        #   2,<width>,<length>,<type>,R1:1 R2:2(2),<extra>
        # This next bit of code fixes that when needed.
        self.count = sum(
            self.get_cab_count(cab)
            for room in self.no.split(' ')
            for cab in room.split('&')
        )
        return self.count

    @staticmethod
    def get_cab_count(cabno, multi_allowed=False):
        """ Parse out multiple cab counts from a `no` string (like: R1:1(2)).
            Returns the number inside the parenthesis or 1.
        """
        allcounts = cab_multi_count_pat.findall(cabno)
        if allcounts:
            cabcount = sum(int(s) for s in allcounts)
            debug(
                'Found multi {}: {} in {!r}'.format(
                    'count' if len(allcounts) == 1 else 'counts',
                    cabcount,
                    cabno,
                )
            )
            return cabcount

        if ('(' in cabno):
            if ((' ' in cabno) or ('&' in cabno)) and multi_allowed:
                debug('Missed cab count for multi-room: {!r}'.format(cabno))
            else:
                debug_err(
                    'Missed cab count?: {!r}'.format(cabno),
                    file=sys.stderr,
                )
                debug_err(
                    '<-- get_cab_count() called from.',
                    level=1,
                    file=sys.stderr,
                )
        return 1

    def has_multi(self):
        """ Return True if this MozaikPart has multiple cabs or rooms in
            the cab no.
        """
        if not self.no:
            return False
        return self.has_multi_cab() or self.has_multi_room()

    def has_multi_cab(self):
        """ Return True if this MozaikPart has multiple cabs in the cab no.
        """
        return '&' in self.no

    def has_multi_room(self):
        """ Return True if this MozaikPart has multiple rooms in the cab no.
        """
        return (self.no.lower().count('r') > 1) and (' ' in self.no)

    def similar_part(self, other):
        """ Returns True if `other` is the same exact part as this,
            except for the count.
        """
        if other is self:
            return False
        if not other:
            return False
        fields = list(self.header)
        fields.remove('count')
        for field in fields:
            if field == 'no':
                if trim_cab_count(self.no) != trim_cab_count(other.no):
                    return False
            else:
                if getattr(self, field) != getattr(other, field):
                    return False
        debug('Same part:')
        debug(str(self), align=True)
        debug(str(other), align=True)
        return True

    def split_parts(self):
        """ If this MozaikPart has multiple rooms/cabs, split it into
            multiple MozaikParts.
            Otherwise returns a list with [self].
        """
        if not self.has_multi():
            debug('Single part: {}'.format(self))
            return [self]

        # Split rooms.
        roomparts = self.split_rooms()
        # Split cabs.
        return self.split_room_cabs(roomparts)

    def split_room_cabs(self, roomparts):
        """ Split each single-room part, with possibly multiple parts on one
            line, into separate parts for each cabinet number.
            Returns a list of parts, possible just [self] for single room and
            single cab parts.

            Raises ValueError if a multi-room part is encountered.
            Arguments:
                roomparts  : A list of MozaikParts with only a single-room
                             number for each part.
        """
        cabparts = []
        multiroom = []
        for roompart in roomparts:
            if roompart.has_multi_room():
                multiroom.append(roompart)
                debug_err('Got multi-room part: {}'.format(roompart))
                continue
            if ':' not in roompart.no:
                debug_err('No room number: {}'.format(roompart))
                roompart.no = 'R1:{}'.format(roompart.no)
            roomno, sep, cabs = roompart.no.partition(':')

            cabnos = cabs.split('&')
            if len(cabnos) == 1:
                roompart.count = self.get_cab_count(roompart.no)
                cabparts.append(roompart)
                debug('Added single cab part: {}'.format(roompart))
                continue
            # Parse multiple cab nos.
            debug('Multiple cabs: {}'.format(cabs))
            for cab in cabs.split('&'):
                debug('Parsing cab part: {!r}'.format(cab))
                part = roompart.copy()
                part.no = ':'.join((roomno, cab))
                part.count = self.get_cab_count(cab)
                cabparts.append(part)
                debug(
                    'Added separate cab part: {}'.format(part),
                    align=True,
                )
        if multiroom:
            debug_err('Handling mistaken multi-room parts:')
            deferredroomparts = []
            for part in multiroom:
                deferredroomparts.extend(part.split_rooms())
            deferredcabparts = self.split_room_cabs(deferredroomparts)
            debug_err('Re-split cabs ({}) for {} multi-room parts.'.format(
                len(deferredcabparts),
                len(deferredroomparts),
            ))
            cabparts.extend(deferredcabparts)
        return cabparts

    def split_rooms(self):
        """ Split this part, with possibly multiple rooms, into separate
            parts for each room number.
            See also: self.split_parts and self.split_room_cabs
            Returns a list of parts, possibly just [self] for single rooms.
        """
        if not self.has_multi_room():
            return [self]

        originalcnt = self.count
        roomparts = []
        roomnos = self.no.split(' ')
        if len(roomnos) == 1:
            part = self.copy()
            roomparts.append(part)
            debug('Added single room part: {}'.format(part))
        else:
            debug('Multiple rooms: {}'.format(self.no))
            for roomno in roomnos:
                part = self.copy()
                part.no = roomno
                part.count = roomno.count('&') + self.get_cab_count(roomno)
                roomparts.append(part)
                debug('Added separate room part: {}'.format(part), align=True)
            roomsplitcnt = sum(p.count for p in roomparts)
            if roomsplitcnt != originalcnt:
                debug_err('Splitting rooms changed count:', align=True)
                debug_err('Original: {}'.format(originalcnt), align=True)
                debug_err('   Split: {}'.format(roomsplitcnt), align=True)
        return roomparts

    def to_csv(self):
        """ Convert back into a csv line. """
        return ','.join(
            str(getattr(self, field, ''))
            for field in self.header
        )

    def tree(self):
        """ Return this mozaik master part in tree-style:
                {
                    width: {
                        room: {
                            cab_no: {
                                part_type: {
                                    extra_data: {
                                        length: count
                                    }
                                }
                            }
                        }
                    }
                }
        """
        tree = {}
        for part in self.split_parts():
            # room, cab, width, length, extra, part
            room, cab = part.no.split(':')
            cab = trim_cab_count(cab)
            tree.setdefault(
                room,
                MozaikPartTree({}, label='cab')
            )
            tree[room].setdefault(
                cab,
                MozaikPartTree({}, label='width')
            )
            tree[room][cab].setdefault(
                part.width,
                MozaikPartTree({}, label='length')
            )
            w = part.width
            tree[room][cab][w].setdefault(
                part.length,
                MozaikPartTree({}, label='extra_data')
            )
            tree[room][cab][w][part.length].setdefault(
                part.extra_data,
                MozaikPartTree({}, label='type')
            )
            tree[room][cab][w][part.length][part.extra_data].setdefault(
                part.type,
                0
            )
            tree[room][cab][w][part.length][part.extra_data][part.type] += (
                part.count
            )

        return MozaikPartTree(tree, label='room')


class MozaikPart(MozaikMasterPart):
    """ A part with a width that depends on the MozaikFile's width. """
    header = MozaikFile.header

    def __init__(self, data):
        super().__init__(data)

    def tree(self):
        """ Return this mozaik part in tree-style:
                {
                    room: {
                        cab_no: {
                            part_type: {
                                extra_data: {
                                    length: count
                                }
                            }
                        }
                    }
                }
        """
        tree = {}
        for part in self.split_parts():
            # room, cab, width, length, extra, part
            room, cab = part.no.split(':')
            cab = trim_cab_count(cab)
            tree.setdefault(
                room,
                MozaikPartTree({}, label='cab')
            )
            tree[room].setdefault(
                cab,
                MozaikPartTree({}, label='length')
            )
            tree[room][cab].setdefault(
                part.length,
                MozaikPartTree({}, label='extra_data')
            )
            tree[room][cab][part.length].setdefault(
                part.extra_data,
                MozaikPartTree({}, label='type')
            )
            tree[room][cab][part.length][part.extra_data].setdefault(
                part.type,
                0
            )
            tree[room][cab][part.length][part.extra_data][part.type] += (
                part.count
            )

        return MozaikPartTree(tree, label='room')


class MozaikPartTree(UserDict):
    # Whether to print labels when printing the tree.
    print_labels = True

    level_colors = {
        0: {'fore': 'blue', 'style': 'bright'},
        1: {'fore': 'blue'},
        2: {'fore': 'cyan'},
        3: {'fore': 'green'},
        4: {'fore': 'lightblue'},
        5: {'fore': 'yellow'},
        6: {'fore': 'magenta'},
    }
    level_colors_len = len(level_colors)

    def __init__(self, data, label=None, filepath=None):
        self.data = dict(data) or {}
        self.label = str(label) if label else None
        self.filepath = (filepath or getattr(data, 'filepath', None)) or None

    def __bool__(self):
        return bool(self.data)

    def __repr__(self):
        return '\n'.join((
            '{typ}(',
            '  data={s.data!r}',
            '  label={s.label!r}',
            '  filepath={s.filepath!r}',
            ')',
        )).format(typ=type(self).__name__, s=self)

    def __str__(self):
        return repr(self)

    @classmethod
    def color_args(cls, index):
        return cls.level_colors[index % cls.level_colors_len]

    @classmethod
    def format_label(cls, item, default='None'):
        """ Format a label for printing, if it hasn't been printed yet. """
        if not cls.print_labels:
            return ''
        return '{}: '.format(
            C(cls.get_label(item, default=default), 'dimgrey')
        )

    @classmethod
    def get_label(cls, item, default='None'):
        """ If the item has a `label` attribute, return it.
            Otherwise, return a default value.
        """
        label = getattr(item, 'label', None)
        if not label:
            return default
        return label

    @classmethod
    def iter_lines(cls, d):
        """ Iterate over master file lines created from this tree. """
        for partinfo in cls.iter_part_info(d):
            # count, width, length, type, no, extra_data
            line = ','.join((
                str(partinfo['count']),
                partinfo['width'],
                partinfo['length'],
                partinfo['type'],
                partinfo['no'],
                partinfo['extra_data'],
            ))
            yield line

    @classmethod
    def iter_part_info(cls, d):
        partinfo = {}
        for value in cls.iter_tree(d):
            if value is None:
                # One complete part has been yielded.
                no = '{}:{}'.format(partinfo['room'], partinfo['cab'])
                if partinfo['count'] > 1:
                    no = '{}({})'.format(no, partinfo['count'])
                # count, width, length, type, no, extra_data
                yield {
                    'count': str(partinfo['count']),
                    'width': partinfo['width'],
                    'length': partinfo['length'],
                    'type': partinfo['type'],
                    'no': no,
                    'extra_data': partinfo['extra_data'],
                }
                continue
            _, label, val = value
            partinfo[label] = val or ''

    @classmethod
    def iter_tree(cls, d, level=0):
        for k, v in d.items():
            if not isinstance(v, (cls, dict)):
                # End of the nests, just a key/value pair.
                label = cls.get_label(d)
                yield level, label, k
                yield level, 'count', v
                yield None
                continue
            label = cls.get_label(d)
            yield level, label, k
            yield from cls.iter_tree(v, level=level + 1)

    @classmethod
    def merge_dicts(cls, d1, d2):
        notset = object()
        d = {k: v for k, v in d1.items()}

        for k, v in d2.items():
            if d.get(k, notset) is notset:
                d[k] = d2[k]
                continue
            if isinstance(v, (cls, dict)):
                d[k] = cls(
                    cls.merge_dicts(d[k], d2[k]),
                    label=getattr(d[k], 'label', None),
                )
            elif isinstance(v, (float, int)):
                d[k] += v
        return d

    def print(self):
        self.labels_printed = set()
        if self.filepath:
            print('{}:'.format(C(self.filepath, **self.color_args(0))))
            level = 1
        else:
            level = 0
        self.print_tree(self, level=level)

    @classmethod
    def print_tree(cls, d, level=0):
        for value in cls.iter_tree(d):
            if value is None:
                continue
            lvl, lbl, val = value
            indent = '    ' * lvl
            end = '\n'
            lblfmt = '{}: '.format(C(lbl.title(), 'dimgrey'))
            valfmt = C(val or 'None', **cls.color_args(lvl))
            if lbl == 'type':
                end = ': '
            elif lbl == 'count':
                indent = ''
                lblfmt = ''
                valfmt = C(val or 0, **cls.color_args(lvl + 1))
            print(
                '{}{}{}'.format(
                    indent,
                    lblfmt,
                    valfmt,
                ),
                end=end,
            )

    def to_lines(self):
        """ Convert this MozaikPartTree back into master file lines """
        return list(self.iter_lines(self))

    def to_mozaikparts(self):
        """ Convert this MozaikPartTree back into a list of MozaikParts. """
        parts = []
        for d in self.iter_part_info(self):
            d.pop('width')
            parts.append(MozaikPart(d))
        return parts

    def update(self, data):
        """ Merge `data` into `self.data`. """
        self.data = self.merge_dicts(self.data, data)
