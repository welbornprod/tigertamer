#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" test_tigertamer.py
    Unit tests for tigertamer.py

    -Christopher Welborn 02-24-2019
"""

import sys
import unittest

from ..lib.util.parser import (
    MozaikMasterFile,
)

from ..test import data


class MozaikMasterPartTests(unittest.TestCase):

    def setUp(self):
        """ Set up test data for MozaikMasterPartTests. """
        self.testdata = data.mozmasterfile

    def assertPartEqual(self, a, b, **kwargs):
        """ Like assertEqual, but has better messages for MozaikParts. """
        try:
            self.assertEqual(a, b, **kwargs)
        except AssertionError:
            lines = [kwargs.get('msg', 'Parts are not equal')]
            for key in a.header:
                lines.append('{}={:<30} {}={}'.format(
                    key,
                    getattr(a, key, None),
                    key,
                    getattr(b, key, None),
                ))
            raise AssertionError('\n'.join(lines))

    def test_parse_line(self):
        """ parse_line should create valid MozaikParts. """

        for line, cases in self.testdata.items():
            # Test without split parts.
            mfile = MozaikMasterFile.from_line(line, split_parts=False)
            self.assertListEqual(
                mfile.parts,
                cases['no_split'],
                msg='from_line(split_parts=False) failed to parse correctly.',
            )

            # Test with split parts.
            mfile = MozaikMasterFile.from_line(line, split_parts=True)
            self.assertListEqual(
                mfile.parts,
                cases['split'],
                msg='from_line(split_parts=True) failed to parse correctly.',
            )


if __name__ == '__main__':
    unittest.main(argv=sys.argv, verbosity=2)
