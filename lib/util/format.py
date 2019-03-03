#!/usr/bin/env python3

""" format.py
    Utilities for working with the TigerStop format (XML).
    -Christopher Welborn 12-16-2018
"""

import os

from lxml.builder import ElementMaker
from lxml import etree as ElementTree
from lxml.etree import tostring as et_tostring

from colr import (
    auto_disable as colr_auto_disable,
    Colr as C,
)

from .config import config

colr_auto_disable()

E = ElementMaker(
    nsmap={
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
    }
)

settings = {
        'style': config.get(
            'style',
            'Setpoint'
        ),
        'unit': config.get(
            'unit',
            'English'
        ),
        'isOptimized': config.get(
            'isOptimized',
            'true'
        ),
        'headCut': config.get(
            'headCut',
            '0'
        ),
        'tailCut': config.get(
            'tailCut',
            '0'
        ),
        'patternStockLength': config.get(
            'patternStockLength',
            '0'
        ),
        'sequenceNumber': config.get(
            'sequenceNumber',
            '1'
        ),
        'sortString': config.get(
            'sortString',
            None
        ),
        'sendFileName': config.get(
            'sendFileName',
            'true'
        ),
        'quantityMultiples': config.get(
            'quantityMultiples',
            'false'
        ),
        'isInfinite': config.get(
            'isInfinite',
            'false'
        ),
        'isCascade': config.get(
            'isCascade',
            'false'
        ),
}


def create_xml(mozfile, extra_data=False):
    return '\n'.join((
        '<?xml version="1.0" encoding="utf-8"?>',
        et_tostring(
            E.CutList(
                *create_settings(mozfile.filename, extra_data=extra_data),
                E.pieces(
                    *create_pieces(mozfile.parts, extra_data=extra_data),
                ),
            ),
            pretty_print=True,
        ).decode(),
    ))


def create_piece(mozpart, index, extra_data=False):
    part_strs = [
        E.string(str(index)),
        E.string(mozpart.type),
        E.string(mozpart.no),
    ]
    if extra_data:
        part_strs.append(E.string(mozpart.extra_data))

    return E.Piece(
        E.labelStrings(*part_strs),
        E.length(mozpart.length),
        E.quantity(str(mozpart.count)),
        E.completed('0'),
    )


def create_pieces(mozparts, extra_data=False):
    return (
        create_piece(part, i + 1, extra_data=extra_data)
        for i, part in enumerate(
            sorted(mozparts, key=lambda p: p.no)
        )
    )


def create_settings(filename, extra_data=False):
    tigername, _ = os.path.splitext(filename)
    labels = ['Index', 'Part', 'No']
    if extra_data:
        labels.append('Note')
    # Generate LabelField items programmatically.
    label_strs = [
        E.LabelField(
            E.header(header),
            E.fontSize('12'),
            E.x('0'),
            E.y(str(col * 20)),
            E.column(str(col)),
        )
        for col, header in enumerate(labels)
    ]

    return (
        E.style(settings['style']),
        E.unit(settings['unit']),
        E.isOptimized(settings['isOptimized']),
        E.headCut(settings['headCut']),
        E.tailCut(settings['tailCut']),
        E.patternStockLength(settings['patternStockLength']),
        E.sequenceNumber(settings['sequenceNumber']),
        (
            E.sortString(settings['sortString'])
            if settings['sortString']
            else E.sortString()
        ),
        E.sendFileName(settings['sendFileName']),
        E.fname(tigername),
        E.quantityMultiples(settings['quantityMultiples']),
        E.isInfinite(settings['isInfinite']),
        E.isCascade(settings['isCascade']),
        E.printStrings(*label_strs),
    )


class TigerFile(object):
    """ A tiger file (XML, .tiger) constructed from a file or XML string with
        a header and a parts list.

        Typical Header:
            Index, Quantity, Completed, Length, Part, No, Note
            ...where Quantity and Completed are TigerStop values, and the
            others are from the user's printStrings/labelField/labelStrings.

    """
    def __init__(self, filename=None, parts=None):
        self.filename = filename or None
        self.parts = parts or []
        # Header values always added by tigerstop.
        self.header_ts = ['Quantity', 'Completed', 'Length']
        # Header values added by the user through labelStrings.
        self.header_user = None
        # Final header for display, set in self.from_bytes().
        self.header = None
        self.root = None

    def __colr__(self):
        """ Format this TigerFile as a Colr when passed directly to Colr().
        """
        typename = C(type(self).__name__, 'blue')
        filename = C(self.filename, 'cyan')
        if not self.parts:
            return C('{typ}(filename={filename!r}, parts={parts!r})'.format(
                typ=typename,
                filename=filename,
                parts=C(self.parts, 'cyan'),
            ))
        return C('\n  '.join((
                '{typ}(',
                'filename={fname!r},',
                'parts=[',
                '{parts}',
                ']\n)'
        )).format(
            typ=typename,
            filename=filename,
            parts='\n  '.join(C(p) for p in self.parts),
        ))

    def __repr__(self):
        typename = type(self).__name__
        if not self.parts:
            return '{typ}(filename={filename!r}, parts={parts!r})'.format(
                typ=typename,
                filename=self.filename,
                parts=self.parts,
            )
        return '\n  '.join((
                '{typ}(',
                'filename={fname!r},',
                'parts=[',
                '{parts}',
                ']\n)'
        )).format(
            typ=typename,
            filename=self.filename,
            parts='\n  '.join(str(p) for p in self.parts),
        )

    def __str__(self):
        partlen = len(self.parts)
        singleitem = partlen == 1
        return '{}(filename={!r}, parts={})'.format(
            type(self).__name__,
            self.filename,
            '[{} {}{}]'.format(
                partlen,
                'part' if singleitem else 'parts',
                '' if singleitem else '..',
            ),
        )

    def _build_headers(self, rootelem):
        """ Set self.header with values from `header_ts` and `header_user`,
            calling `_parse_user_headers()` to get them.
        """
        # Get user headers.
        self.header_user = self._parse_user_headers(rootelem)
        if not self.header_user:
            raise ValueError(
                'No user headers!: {!r}'.format(self.header_user)
            )
        if self.header_user[0].lower() in ('index', 'count'):
            self.header = [self.header_user[0]]
            skip = 1
        else:
            self.header = []
            skip = 0
        self.header.extend(self.header_ts)
        self.header.extend(self.header_user[skip:])

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'rb') as f:
            tf = cls.from_bytes(f.read())
            tf.filename = filename
        return tf

    @classmethod
    def from_bytes(cls, b, filename=None):
        """ Create a TigerFile from XML bytes (a .tiger file's content). """
        tf = cls(filename=filename)
        root = ElementTree.fromstring(b)

        tf._build_headers(root)
        tf.parts = tf._parse_pieces(root)
        return tf

    def _parse_pieces(self, rootelem):
        # Parse parts in <pieces><Piece>..</Piece>..</pieces>
        if not self.header_user:
            raise ValueError('Headers not set (needs _build_headers())!')

        parts = []
        for piece in rootelem.iter('Piece'):
            partinfo = {
                'length': piece.find('length').text,
                'quantity': int(piece.find('quantity').text),
                'completed': int(piece.find('completed').text),

            }
            lblstrs = piece.find('labelStrings')
            # Expecting Index, Part, No, and optional Note <string>s.
            userstrs = [
                (i, string.text)
                for i, string in enumerate(lblstrs.findall('string'))
            ]
            for index, value in userstrs:
                lbl = self.header_user[index]
                if lbl.lower() in ('index', 'count'):
                    value = int(value)
                partinfo[lbl] = value

            parts.append(TigerPart(partinfo))
        return parts

    @classmethod
    def _parse_user_headers(cls, rootelem):
        """ Grab all <header>s from <printStrings>, and return the text
            in a list, using <column> for the list index.
            Returns a list of user headers from a .tiger file root element.
        """

        user_headers = []
        for lblfield in rootelem.find('printStrings'):
            index = int(lblfield.find('column').text)
            user_headers.insert(index, lblfield.find('header').text)
        return user_headers

    def print(self):
        """ Print a console-friendly version of this TigerFile. """
        if self.filename:
            fname = C(self.filename, 'lightskyblue')
        else:
            fname = C('Unknown TigerFile', 'red').join('<', '>')

        partlen = len(self.parts)
        print('\n{} ({} {}):'.format(
            C(fname),
            C(partlen, 'blue', style='bright'),
            C('part' if partlen == 1 else 'parts', 'blue'),
        ))
        if not self.parts:
            return False
        for p in self.parts:
            print('    {}'.format(C(p)))
        return True


class TigerPart(object):
    """ A single part, parsed from a .tiger file (XML), held in a TigerFile.
        It has attributes that match the TigerFile header.
    """
    # Header for this part. 'Note' may be added to the header if it is found
    # in the initialization dict.
    header = ['Index', 'Quantity', 'Completed', 'Length', 'Part', 'No']

    def __init__(self, data):
        """ Initialize a TigerPart with a dict of {lbl: val}, where lbl is
            in TigerFile.header.
        """
        for key, val in data.items():
            if val is not None:
                try:
                    val = int(val)
                except ValueError:
                    try:
                        val = float(val)
                    except ValueError:
                        val = str(val)
            setattr(self, key.lower(), val)
        if ('Note' in data) and ('Note' not in self.header):
            self.header.append('Note')
        if 'Count' in data:
            self.header[0] = 'Count'
        self.header = tuple(self.header)

    def __colr__(self):
        """ Format this TigerPart as a Colr when passed directly to Colr().
        """
        just_default = 3
        just = {
            'length': 7,
            'part': 5,
            'no': 10,
        }
        justtype_default = '>'
        justtype = {
            'part': '<',
            'no': '<',
        }
        missing_default = C('None', 'dimgrey').join('<', '>', fore='dimgrey')
        missing = {
            'completed': '0',
        }
        pcs = []
        for key in self.header:
            keylow = key.lower()
            val = getattr(self, keylow, None)
            if not val:
                val = missing.get(keylow, missing_default)
            if keylow == 'length':
                val = '{:0.2f}'.format(float(val))
            pcs.append(
                '{k}: {v:{justtype}{just}}'.format(
                    k=C(key, 'blue'),
                    v=C(val, 'cyan'),
                    justtype=justtype.get(keylow, justtype_default),
                    just=just.get(keylow, just_default),
                )
            )
        return C(' ').join(pcs)

    def __str__(self):
        return ', '.join(
            '{}: {}'.format(key, getattr(self, key.lower(), None))
            for key in self.header
        )
