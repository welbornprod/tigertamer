#!/usr/bin/env python3

""" tigertamer - lib/util/archive.py
    Handles archiving/unarchiving .dat files for TigerTamer.
    -Christopher Welborn 04-22-2019
"""

import os
import re
import shutil
from collections import UserDict

from colr import (
    Colr as C,
    auto_disable as colr_auto_disable,
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

colr_auto_disable()

# Char for splitting/re-joining archive file paths.
archive_split_char = '__'

# Map from parent file name to FinishedFile object. Used by archive_file().
_finished_files = {}


def archive_file(filepath, archive_dir, created_files=None):
    """ Archive a parent file. If it was already archived, it's created files
        are still added to it's `created_files` list.
    """
    existing = _finished_files.get(filepath, None)
    if existing is not None:
        existing.add_created(created_files)
        if existing.is_archived:
            debug('Already archived: {}'.format(filepath))
            return True
        debug('Already tried to archive: {}'.format(filepath))
        return False
    archfile = FinishedFile(filepath, archive_dir, created_files=created_files)
    _finished_files[filepath] = archfile
    return archfile.archive()


def get_archive_info(datdir, archdir, listdir=os.listdir):
    """ Get all file paths in the archive directory, and where they would
        be restored to.
        Returns [(archivefile, restoretofile), ...]
    """
    try:
        archfiles = listdir(archdir)
    except OSError as ex:
        raise OSError('Unable to unarchive files!: ({}) {}'.format(
            type(ex).__name__,
            ex,
        )) from ex

    if not archfiles:
        raise ValueError('No files to unarchive.')

    # TODO: This currently doesn't handle mixed-version archive files.
    #       The presence of one bad archive file ruins the whole thing
    #       because of the `zip(origpaths, destpaths)` call at the end.
    origpaths = (os.path.join(archdir, s) for s in archfiles)
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


def list_archive(arch_dir, dest_dir):
    """ Print all archive files, and return an exit status code. """
    archive = Archive(arch_dir, dest_dir)
    for archfile in sorted(archive.values()):
        print(C(archfile))
    return 0 if archive else 1


def remove_dir_if_empty(path):
    """ Remove a directory, if it's empty.
        Returns True if everything went well.
        Otherwise it returns False.
    """
    try:
        files = os.listdir(path)
    except OSError as ex:
        print_err('Unable to list files: {}\n{}'.format(path, ex))
        return False
    if files:
        debug('Directory not empty: {}'.format(path))
        return True
    debug('Directory is empty, removing it: {}'.format(path))
    try:
        os.rmdir(path)
    except OSError as ex:
        print_err('Cannot remove dir: {}\n{}'.format(path, ex))
        return False
    debug('Removed directory: {}'.format(path))
    return True


def safe_move(src, dest):
    """ Move a file, using shutil.copy2 without overwriting existing files.
        This function will rename the destination file to avoid clobbering.
    """
    # Don't clobber existing archives just because of poor naming.
    if os.path.exists(dest):
        dest = increment_file_path(dest)
        debug('Renaming file: {}'.format(dest))
    return shutil.move(src, dest)


class Archive(UserDict):
    """ A collection of ArchiveFiles, built from listing an archive dir. """
    def __init__(self, archive_dir, dest_dir, files=None):
        self.archive_dir = archive_dir
        self.dest_dir = dest_dir

        # Retrieve archive files if none were passed in.
        if files is None:
            self.data = self.get_files()
        else:
            self.data = self.build_files(files)

    def __bool__(self):
        return bool(self.data)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return '\n'.join((
            '{typ}(',
            '  archive_dir={s.archive_dir!r}',
            '     dest_dir={s.dest_dir!r}',
            '        files={s.files!r}',
        )).format(typ=type(self).__name__, s=self)

    def __str__(self):
        return '\n'.join(str(archfile) for archfile in self.values())

    def build_files(self, filepaths):
        """ Return  a dict of {filepath: ArchiveFile} for all files in
            `filepaths`.
        """
        archpaths = self.filter_files(filepaths)
        if not archpaths:
            return {}

        d = {s: ArchiveFile(s, self.dest_dir) for s in archpaths}
        return {k: v for k, v in d.items() if v.dest_path}

    @property
    def files(self):
        """ Convenience name for self.data.values() is self.files. """
        return self.data.values()

    def filter_files(self, filepaths):
        """ Return a list of valid archive files in `filepaths`. """
        return [s for s in filepaths if archive_split_char in s]

    def get_files(self):
        """ Return a dict of {filepath: ArchiveFile} for all files
            listed in `self.archive_dir`.
        """
        if not os.path.exists(self.archive_dir):
            return {}

        try:
            archfiles = [
                os.path.join(self.archive_dir, s)
                for s in os.listdir(self.archive_dir)
            ]
        except OSError as ex:
            raise OSError('Unable to unarchive files!: ({}) {}'.format(
                type(ex).__name__,
                ex,
            )) from ex

        return self.build_files(archfiles)


class ArchiveFile(object):
    """ A file from the archives, to view or unarchive, """
    def __init__(self, filepath, dest_dir):
        self.filepath = filepath
        self.dest_dir = dest_dir

        # Destination path when unarchived.
        self.dest_path = self.get_dest_path()

    def __colr__(self):
        filepath = C('/', style='bright').join(
            C(s, 'blue')
            for s in os.path.split(self.trim_path(self.filepath))
        )
        destpath = C('/', style='bright').join(
            C(s, 'cyan')
            for s in os.path.split(self.dest_path)
        )
        return C('\n ⮩ ', 'yellow', style='bright').join(
            filepath,
            destpath,
        )

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __gt__(self, other):
        if not isinstance(other, ArchiveFile):
            raise TypeError('Uncomparable types: {} > {}'.format(
                type(self).__name__,
                type(other).__name__,
            ))
        return self.filepath > other.filepath

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other):
        if not isinstance(other, ArchiveFile):
            raise TypeError('Uncomparable types: {} < {}'.format(
                type(self).__name__,
                type(other).__name__,
            ))
        return self.filepath < other.filepath

    def __repr__(self):
        return '\n'.join((
            '{typ}(',
            '  filepath={s.filepath!r}',
            '  dest_dir={s.dest_dir!r}',
            ' dest_path={s.dest_path!r}',
        )).format(typ=type(self).__name__, s=self)

    def __str__(self):
        return '{!r} ({!r})'.format(self.filepath, self.dest_path)

    def get_dest_path(self):
        destdirparent, destdirsub = os.path.split(self.dest_dir)
        if not destdirsub:
            destdirsub = destdirparent
        filename = os.path.split(self.filepath)[-1]
        try:
            subdir, name = filename.rsplit(archive_split_char, 1)
        except ValueError:
            debug_err('Not a valid archive file name: {}'.format(self.filepath))
            return None
        if destdirsub.endswith(subdir):
            # No sub directory for this file.
            relpath = name
        else:
            relpath = os.path.join(subdir, name)

        return os.path.join(self.dest_dir, relpath)

    @staticmethod
    def trim_path(filepath):
        path, fname = os.path.split(filepath)
        _, subdir = os.path.split(path)
        return os.path.join(subdir, fname)

    def unarchive(self):
        """ Unarchive this ArchiveFile. """
        if not self.dest_path:
            return False

        destdir = os.path.dirname(self.dest_path)
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
            shutil.move(self.filepath, self.dest_path)
        except OSError:
            msg = '\n'.join((
                'Unable to unarchive/move file:',
                '{src}',
                '-> {dest}',
            )).format(src=self.filepath, dest=self.dest_path)
            raise ValueError(msg)
        else:
            debug('Moved {} -> {}'.format(self.filepath, self.dest_path))
        return True


class FinishedFile(object):
    """ A file to archive, because it has been processed. """
    def __init__(self, filepath, archive_dir, created_files=None):
        self.filepath = filepath
        self.parent_dir, self.parent_name = os.path.split(self.filepath)

        # A list of files that this master file created.
        self.created_files = created_files or []
        # The destination archive dir.
        self.archive_dir = archive_dir

        # Set on successful `archive()` call.
        self.is_archived = False
        # Destination/Archived file path.
        self.archived_path = self.get_archived_path()

    def add_created(self, created_files):
        """ Add some created_files to this FinishedFile.
            None/Falsey values are ignored.
        """
        if not created_files:
            return None
        self.created_files.append(created_files)

    def archive(self):
        """ Archive this file, if it is not archived already. """
        if self.archive_dir in (None, '', '-'):
            debug('Archiving disabled for: {}'.format(self.filepath))
            return False

        if not os.path.exists(self.filepath):
            if os.path.exists(self.archived_path):
                debug('Already archived: {}'.format(self.archived_path))
                self.is_archived = True
                return True
            debug_err('Missing parent file: {}'.format(self.filepath))
            return False

        # Create archive dir if needed.
        if not os.path.isdir(self.archive_dir):
            try:
                os.mkdir(self.archive_dir)
            except EnvironmentError as ex:
                print_err('Failed to create archive dir: {}'.format(ex))
                return False
            else:
                debug('Created archive directory: {}'.format(self.archive_dir))

        # Move master file to archive.
        try:
            destfile = safe_move(self.filepath, self.archived_path)
        except EnvironmentError as ex:
            print_err('Failed to copy master file: {}\n{}'.format(
                self.filepath,
                ex,
            ))
            return False
        else:
            status('Archived', destfile)
            config_increment(archive_files=1, default=0)
            self.is_archived = True

        return remove_dir_if_empty(self.parent_dir)

    def get_archived_path(self):
        parentsubdir = os.path.split(self.parent_dir)[-1]
        newparentname = archive_split_char.join((
            parentsubdir,
            self.parent_name
        ))
        return os.path.join(self.archive_dir, newparentname)
