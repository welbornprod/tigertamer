#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" test_tigertamer.py
    Unit tests for tigertamer.py

    -Christopher Welborn 02-24-2019
"""
import os
import sys
import unittest

from colr import Colr as C
from printdebug import DebugColrPrinter

from ..lib.util.config import (
    NotSet,
)
from ..lib.util.parser import (
    MozaikMasterFile,
)

from ..test import (
    data,
)

debugprinter = DebugColrPrinter()
debugprinter.enable(bool(os.environ.get('TT_TEST_DEBUG', 0)))
debug = debugprinter.debug


def part_compare_fmt(a, b, mark_keys=None):
    """ Return a formatted string with two parts side by side. """
    maxwidth = 80
    halfwidth = maxwidth // 2
    itemwidth = maxwidth // 4
    mark_keys = set(mark_keys or [])
    lines = [
        '{typea:<{cols}}{typeb:<{cols}}'.format(
            typea=C('{}:'.format(type(a).__name__).center(halfwidth), 'blue'),
            typeb=C('{}:'.format(type(b).__name__).center(halfwidth), 'blue'),
            cols=maxwidth // 2,
        )
    ]
    aheader = getattr(a, 'header', [])
    header = set(aheader)
    bheader = getattr(b, 'header', [])
    header.update(set(bheader))
    fmt = '{key}={vala} {key}={valb}'
    for key in sorted(header):
        if (key not in aheader) or (key not in bheader):
            # Auto-mark missing header keys.
            mark_keys.add(key)

        if key in mark_keys:
            itemcolr = 'red'
            keyfmt = '*{}'.format(key)
        else:
            itemcolr = 'cyan'
            keyfmt = key
        lines.append(fmt.format(
            key=C(keyfmt, itemcolr).rjust(itemwidth),
            vala=C(repr(getattr(a, key, NotSet)), itemcolr).ljust(itemwidth),
            valb=C(repr(getattr(b, key, NotSet)), itemcolr).ljust(itemwidth),
        ))
    return '\n'.join(lines)


def partlist_compare_fmt(lista, listb):
    """ Show two parts lists side by side, highlighting any differences.
        Returns a formatted str if the lists differ, otherwise returns
        an empty str ('').
    """
    if lista == listb:
        return ''
    lena, lenb = len(lista), len(listb)
    maxwidth = 80
    halfwidth = maxwidth // 2
    lines = []
    for i in range(max(lena, lenb)):
        try:
            itema = lista[i]
        except IndexError:
            itema = NotSet
        try:
            itemb = listb[i]
        except IndexError:
            itemb = NotSet
        symbol = '==' if itema == itemb else '!='
        colora = 'red' if itema is NotSet else 'cyan'
        colorb = 'red' if itemb is NotSet or itemb != itema else 'cyan'
        lines.append(
            str(C('\n').join(
                '   {}'.format(C(itema, colora).ljust(halfwidth)),
                '{} {}'.format(symbol, C(itemb, colorb)),
            ))
        )

    return '\n'.join(lines)


def part_diff(a, b):
    """ Compare two parts, and return a formatted str with the difference.
        If there is no difference, then empty str is returned.
    """
    if not (a and b):
        return part_compare_fmt(a, b)
    if a.header != b.header:
        return part_compare_fmt(a, b)
    mark_keys = set()
    for key in a.header:
        vala = getattr(a, key, NotSet)
        valb = getattr(b, key, NotSet)
        if vala != valb:
            mark_keys.add(key)
    if not mark_keys:
        # No difference.
        return ''
    return part_compare_fmt(a, b, mark_keys=mark_keys)


class MozaikMasterFileTests(unittest.TestCase):

    def setUp(self):
        """ Set up test data for MozaikMasterPartTests. """
        self.testdata = data.mozmasterfile
        self.testdata_combined = data.mozmasterfile_combined

    def assertPartEqual(self, a, b, msg=None):
        """ Like assertEqual, but with better messages for MozaikParts. """
        try:
            self.assertEqual(a, b, msg=msg)
        except AssertionError:
            lines = [msg or 'Parts are not equal']
            lines.append(part_diff(a, b))
            raise AssertionError('\n'.join(lines))

    def assertPartListEqual(self, a, b, msg=None, desc=None):
        """ Like assertListEqual, but with better repr's for parts. """
        if a == b:
            return
        lena, lenb = len(a), len(b)
        diffindex = -1
        for i in range(min(lena, lenb)):
            itema = a[i]
            itemb = b[i]
            if itema != itemb:
                diffindex = i
                parta = itema
                partb = itemb
                diffmsg = 'Parts are not equal.'
                break
        else:
            # One is a subset of the other.
            diffindex = max(min(lena, lenb) - 1, 0)
            try:
                parta = a[diffindex]
            except IndexError:
                parta = None
            try:
                partb = b[diffindex]
            except IndexError:
                partb = None
            if lena > lenb:
                diffmsg = 'First list is larger.'
            elif lenb > lena:
                diffmsg = 'Second list is larger.'
            else:
                diffmsg = 'List lengths are the same.'

        lines = [
            str(C(msg or 'Lists are not equal.', 'red')),
        ]
        if desc:
            lines.append('   Description: {}'.format(C(desc, 'cyan')))
        lines.append('\n'.join((
            '      Length A: {}',
            '      Length B: {}',
        )).format(
            C(lena, 'blue'),
            C(lenb, 'blue')
        ))

        lines.append('\n{}'.format(partlist_compare_fmt(a, b)))
        lines.append(
            '{} First differing index: {}'.format(diffmsg, diffindex)
        )
        lines.append('\nFirst differing part:\n{}'.format(
            part_diff(parta, partb)
        ))
        raise AssertionError('\n'.join(lines))

    def test_parse_line(self):
        """ parse_line should create valid MozaikParts. """
        debug()
        for line, cases in self.testdata.items():
            # Test without split parts.
            mfile = MozaikMasterFile.from_line(line, split_parts=False)
            self.assertPartListEqual(
                mfile.parts,
                cases['no_split'],
                msg='from_line(split_parts=False) failed to parse correctly.',
                desc=cases['desc'],
            )
            debug('Passed: {}'.format(C(repr(line), 'cyan')))
            debug('No split:', cases['desc'], align=True)
            # Test with split parts.
            mfile = MozaikMasterFile.from_line(line, split_parts=True)
            self.assertPartListEqual(
                mfile.parts,
                cases['split'],
                msg='from_line(split_parts=True) failed to parse correctly.',
                desc=cases['desc'],
            )
            debug('Passed: {}'.format(C(repr(line), 'cyan')))
            debug('   Split:', cases['desc'], align=True)

    def test_parse_line_combined(self):
        """ parse_line should combine similar parts. """
        debug()
        for testitem in self.testdata_combined:
            mfile = MozaikMasterFile.from_lines(
                testitem.lines,
                split_parts=True,
                filepath='Test Data.dat',
            )
            mozfile = mfile.into_width_files()[0]
            self.assertPartListEqual(
                mozfile.parts,
                testitem.expected,
                msg='from_lines() failed to combine parts correctly.',
                desc=testitem.desc,
            )
            debug('Passed: {}'.format(testitem.desc))


if __name__ == '__main__':
    unittest.main(argv=sys.argv, verbosity=2)
