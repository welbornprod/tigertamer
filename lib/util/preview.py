#!/usr/bin/env python3

""" format.py
    Utilities for previewing MozaikMasterFiles/TigerFiles.
    -Christopher Welborn 04-15-2019
"""

import os
from collections import UserList

from colr import Colr as C

from .format import TigerFile
from .parser import MozaikMasterFile


def check_file(filepath, max_size=16000):
    """ Check if a file exists, and is not larger than `max_size` bytes.
        Raises FileNotFoundError if the file cannot be found.
        Raises LargeFileError if the file is over `max_size` bytes.
        Returns None.
    """
    filesize = is_large_file(filepath, max_size=max_size)
    if filesize:
        raise LargeFileError(filepath, filesize)
    return None


def is_large_file(filepath, max_size=4000):
    """ Return the file's size in bytes if it is over `max_size`, otherwise
        return 0.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError('File does not exist: {}'.format(filepath))

    st = os.stat(filepath)
    bytesize = st.st_size
    if bytesize > max_size:
        return bytesize
    return 0


class TigerFiles(UserList):
    """ A list of TigerFiles constructed from a MozaikMasterFile. """
    def __init__(self, iterable):
        super().__init__(iterable)

    @classmethod
    def from_file(cls, filepath, split_parts=True):
        """ Construct a list of TigerFiles from a Mozaik master file path. """
        if not os.path.exists(filepath):
            raise FileNotFoundError('File does not exist: {}'.format(filepath))
        return cls(
            TigerFile.from_mozfile(m)
            for m in MozaikMasterFile.from_file(
                filepath,
                split_parts=split_parts,
            ).into_width_files()
        )

    @classmethod
    def from_files(cls, filepaths, split_parts=True):
        """ Construct a list of TigerFiles from Mozaik master file paths. """
        tigerfiles = []
        for filepath in filepaths:
            tigerfiles.extend(
                cls.from_file(filepath, split_parts=split_parts)
            )
        return cls(tigerfiles)

    def print(self):
        """ Print a console-friendly version of these TigerFiles. """
        # Returns the number of errors that occurred.
        return sum(int(not tf.print()) for tf in self)


class LargeFileError(ValueError):
    def __init__(self, filepath, size):
        self.filepath = filepath
        self.size = size

    def __colr__(self):
        return C(': ').join(
            C('Large file', 'red'),
            C(' ').join(
                C('{} bytes'.format(self.size), 'blue').join('(', ')'),
                C(self.filepath, 'cyan'),
            )
        )

    def __str__(self):
        return 'Large file: ({} bytes) {}'.format(self.size, self.filepath)
