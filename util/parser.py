#!/usr/bin/env python3

""" parser.py
    CSV (.dat) parser to XML (.tiger) creator for TigerTamer.
    -Christopher Welborn 12-15-2018
"""

import csv
import os
import re
import shutil
from contextlib import suppress

from .logger import (
    debug,
    debug_err,
    print_err,
    status,
)
from .format import create_xml


# Pattern to grab multiple cab quantities from a room/cab number.
cab_count_pat = re.compile(r'R?\d{1,3}?\:?\d{1,3}?\((\d{1,3})\)')


def archive_parent_file(datfile, archive_dir):
    """ Move the parent file of this MozaikFile to the archive dir,
        if not already done.
    """
    parentdir, parentname = os.path.split(datfile.parent_file)
    _, parentsubdir = os.path.split(parentdir)
    newparentname = '_'.join((parentsubdir, parentname))
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

    return remove_dir_if_empty(parentdir)


def get_dir_files(dirpath, ignore_dirs=None, ext='.dat', _level=0):
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
        if ignore_dirs and (diritem in ignore_dirs):
            debug('Ignoring directory: {}'.format(diritem))
            continue
        if diritem.endswith(ext):
            if is_valid_dat_file(diritem, _indent=indent):
                debug('{}Found {} file: {}'.format(indent, ext, diritem))
                datfiles.append(diritem)
        elif os.path.isdir(diritem):
            datfiles.extend(
                get_dir_files(diritem, ext=ext, _level=_level + 1)
            )
    return datfiles


def increment_file_path(path):
    """ Turns file paths like: /dir/filename.ext into /dir/filename(2).ext
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


def is_valid_dat_file(filename, _indent=''):
    """ Returns True if this file has the proper column count for a .dat
        file.
    """
    validlen = len(MozaikMasterFile.header)
    with open(filename, 'r') as f:
        # read only the first line.
        for row in csv.reader([f.readline()]):
            collen = len(row)
            if collen != validlen:
                debug_err(
                    '{}Invalid column count (Need {}, Got {}): {}'.format(
                        _indent,
                        validlen,
                        collen,
                        filename
                    )
                )
                return False
    return True


def load_moz_file(filename):
    """ Loads a single MozaikMasterFile, and splits it into multiple Mozaik
        width files.
    """
    master = MozaikMasterFile.from_file(filename)
    debug('Creating width files from: {}'.format(master))
    return master.into_width_files()


def load_moz_files(filepaths, ignore_dirs=None, ext='.dat'):
    """ Loads multiple MozaikFiles from file names, and returns a list of
        MozaikFiles.
    """
    if isinstance(filepaths, str):
        filepaths = [filepaths]

    files = []
    for filepath in filepaths:
        if os.path.isdir(filepath):
            if ignore_dirs and (filepath in ignore_dirs):
                debug('Ignoring directory: {}'.format(filepath))
                continue
            # A directory, possibly containing .dat files
            # or sub-dirs with .dat files.
            files.extend(
                load_moz_files(
                    get_dir_files(
                        filepath,
                        ignore_dirs=ignore_dirs,
                        ext=ext,
                    )
                )
            )

        elif filepath.endswith(ext):
            # A mozaik face-frame.dat file.
            files.extend(load_moz_file(filepath))
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


def write_tiger_file(
        mozfile, outdir, archive_dir=None,
        error_cb=None, success_cb=None):
    """ Write a .tiger file from a MozaikFile.
        Without callbacks given, it returns an exit status (0 or 1).
        With callbacks it returns `error_cb(mozfile, msg)` or
        `success_cb(mozfile, tigerpath)`

    """
    tigerpath = os.path.join(outdir, mozfile.filename)
    use_err_cb = callable(error_cb)
    use_success_cb = callable(success_cb)

    if os.path.exists(tigerpath):
        debug_err('Tiger file already exists: {}'.format(tigerpath))
        tigerpath = increment_file_path(tigerpath)
        debug_err('Made new tiger file path: {}'.format(tigerpath))
    try:
        with open(tigerpath, 'w') as f:
            f.write(create_xml(mozfile))
    except EnvironmentError as ex:
        msg = 'Cannot write tiger file: {}\n{}'.format(
            tigerpath,
            ex,
        )
        print_err(msg)
        return error_cb(mozfile, msg) if use_err_cb else 1
    status('Created', tigerpath)
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

    def __init__(self):
        self.filename = None
        self.parts = []

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
        keys = 'count={s.count}, filename={s.filename!r},'.format(s=self)
        return '{}({}):'.format(
            type(self).__name__,
            keys,
        )

    @classmethod
    def from_file(cls, filename):
        """ Creates a MozaikFile, and loads/parses a file to populate it.
        """
        mp = cls()
        mp.parse(filename)
        return mp

    def parse(self, filename):
        """ Parses a Mozaik CSV (.dat) file, and populates the MozaikFile
            class.
        """
        debug('Parsing: {}'.format(filename))
        self.filename = filename
        with open(filename) as f:
            for row in csv.reader(f):
                partinfo = {
                    self.header[i]: value
                    for i, value in enumerate(row)
                }
                partinfo['count'] = int(partinfo['count'])
                self.count += partinfo['count']
                self.parts.extend(MozaikMasterPart(partinfo).split_parts())
        return self

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
                filedata[part.width] = MozaikFile(self.filename, part.width)
            # Append part to this width file.
            filedata[part.width].parts.append(newpart)
            filedata[part.width].count += newpart.count

        mozfiles = [filedata[width] for width in sorted(filedata)]
        for mozfile in mozfiles:
            mozfile.parent_file = self.filename
            mozfile.combine_parts()
        return mozfiles

    def to_csv(self):
        """ Convert to csv file. """
        return '\n'.join(p.to_csv() for p in self.parts)


class MozaikFile(object):
    """ Holds a Mozaik file of a predetermined width, without extra data. """
    header = ('count', 'length', 'type', 'no')
    count = 0

    def __init__(self, filename, width):
        """ Initialize a MozaikFile of a certain width from keys/values. """
        self.width = width or 0
        self.filename = self.fix_filename(filename, width)
        self.parts = []
        # This is set by the parent 'MozaikMasterFile' that creates these.
        self.parent_file = None

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
            'filename={s.filename!r}',
        )).format(s=self)
        return '{}({}):'.format(
            type(self).__name__,
            keys,
        )

    def combine_parts(self):
        """ Combine parts that are the same, but have 2 line items for
            some reason.
        """
        debug('Combining parts in: {}'.format(self))
        count = 0

        # Look for single lines, with a matching multi line:
        # like: 1,5,TR,R1:1
        #       2,5,TR,R1:1(2)
        # and combine them into: 3,5,TR,R1:1(3)
        for i, part in enumerate(self.parts[:]):
            if '(' not in part.no:
                continue
            for j, otherpart in enumerate(self.parts[:]):
                if not part.similar_part(otherpart):
                    continue
                # Found one.
                newpart = part.copy()
                newpart.count = part.count + otherpart.count
                newpart.no = '{}({})'.format(
                    trim_cab_count(newpart.no),
                    newpart.count,
                )
                debug('Created combined part: {}'.format(newpart))
                newpart.combined = True
                self.parts[i] = newpart
                self.parts[j] = None
                count += 1
                continue
        try:
            while self.parts:
                self.parts.remove(None)
        except ValueError:
            # No more dead parts to remove.
            pass

        # Look for pure duplicates:
        for i, part in enumerate(self.parts[:]):
            for j, otherpart in enumerate(self.parts[:]):
                if i == j:
                    continue
                if part == otherpart:
                    newpart = part.copy()
                    newpart.count += otherpart.count
                    newpart.no = '{}({})'.format(
                        trim_cab_count(otherpart.no),
                        newpart.count,
                    )
                    debug('Combined simple part: {}'.format(newpart))
                    debug('Duplicates: {}'.format(part), align=True)
                    self.parts[i] = newpart
                    self.parts[j] = None
                    count += 1
                    continue

        try:
            while self.parts:
                self.parts.remove(None)
        except ValueError:
            # No more dead parts to remove.
            pass

        if count:
            debug('Parts combined: {}'.format(count), align=True)

    def fix_filename(self, filename, width):
        """ Fix the file name to contain more information. """
        jobname = self.job_name_from_path(filename)

        _, fname = os.path.split(filename)
        fname, _ = os.path.splitext(fname)
        fname = strip_words(
            fname,
            (
                '\(Face Frames\)',
                '3-4 Maple Board'
            )
        )

        if jobname and (not fname):
            # Managed to guess job name from dir.
            if filename not in self.fix_filename.reported:
                debug_err(
                    'No good file name, using job name: {!r}'.format(jobname)
                )
                self.fix_filename.reported.add(filename)
            fname = jobname
            jobname = None
        elif not (jobname or fname):
            # No good job name or dir name.
            if filename not in self.fix_filename.reported:
                debug_err(
                    'No good file name or job name: {}'.format(filename)
                )
                self.fix_filename.reported.add(filename)
            fname = 'Unknown Job'
            jobname = None
        if jobname:
            fname = ' '.join((jobname, fname)).strip()
        else:
            fname = fname.strip()
        return '{}[{}in]{}'.format(fname or '', width, '.tiger')

    fix_filename.reported = set()

    @staticmethod
    def job_name_from_path(filepath):
        """ Try to get the 'job name' portion of the file path. """
        fpath, fname = os.path.split(filepath)
        _, jobdir = os.path.split(fpath)
        words = ('cutlists', 'tigerstop')
        return strip_words(jobdir.lower(), words).strip().title()


class MozaikMasterPart(object):
    """ Holds info about a single part to be cut. """
    header = MozaikMasterFile.header

    def __init__(self, data):
        for field in self.header:
            setattr(self, field, None)
        try:
            # Dict of {field: value}?
            for k, v in data.items():
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

    def __bool__(self):
        return any(getattr(self, k, None) for k in self.header)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        """ Stringify this MozaikPart for debug printing. """
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

    @staticmethod
    def get_cab_count(cabno):
        """ Parse out multiple cab counts from a `no` string (like: (2)).
            Returns the number inside the parenthesis or 1.
        """
        countmatch = cab_count_pat.match(cabno)
        if (countmatch is not None) and countmatch.groups():
            cabcount = int(countmatch.groups()[0])
            debug(
                'Found multi count: {}'.format(cabcount),
                align=True,
            )
            return cabcount
        return 1

    def split_parts(self):
        """ If this MozaikPart has multiple rooms/cabs, split it into
            multiple MozaikParts. Otherwise returns a list with [self].
        """
        cabno = getattr(self, 'no', None)
        if not cabno:
            return [self]
        has_multiple = (' ' in cabno) or ('&' in cabno)
        if not has_multiple:
            debug('Single part: {}'.format(self))
            return [self]

        # Split rooms.
        roomparts = []
        roomnos = cabno.split(' ')
        if len(roomnos) == 1:
            part = self.copy()
            roomparts.append(part)
            debug('Added single room part: {}'.format(part))
        else:
            debug('Multiple rooms: {}'.format(cabno))
            for roomno in roomnos:
                part = self.copy()
                part.no = roomno
                part.count = roomno.count('&') + 1
                roomparts.append(part)
                debug('Added separate room part: {}'.format(part), align=True)

        # Split cabs.
        cabparts = []
        for roompart in roomparts:
            roomno, sep, cabs = roompart.no.partition(':')
            cabnos = cabs.split('&')
            if len(cabnos) == 1:
                roompart.count = self.get_cab_count(roompart.no)
                cabparts.append(roompart)
                debug(
                    'Added single cab part: {}'.format(roompart),
                    align=True,
                )
                continue
            # Parse multiple cab nos.
            debug('Multiple cabs: {}'.format(cabs), align=True)
            for cab in cabs.split('&'):
                part = roompart.copy()
                part.no = ':'.join((roomno, cab))
                part.count = self.get_cab_count(cab)
                cabparts.append(part)
                debug(
                    'Added separate cab part: {}'.format(part),
                    align=True,
                )
        return cabparts

    def to_csv(self):
        """ Convert back into a csv line. """
        return ','.join(
            str(getattr(self, field, ''))
            for field in self.header
        )


class MozaikPart(MozaikMasterPart):
    """ A part with a width that depends on the MozaikFile's width. """
    header = MozaikFile.header
