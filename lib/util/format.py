#!/usr/bin/env python3

""" format.py
    Utilities for working with the TigerStop format (XML).
    -Christopher Welborn 12-16-2018
"""

import os
from lxml.builder import ElementMaker
from lxml.etree import tostring as et_tostring
from .config import config

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


def create_xml(mozfile):
    return '\n'.join((
        '<?xml version="1.0" encoding="utf-8"?>',
        et_tostring(
            E.CutList(
                *create_settings(mozfile.filename),
                E.pieces(
                    *create_pieces(mozfile.parts),
                ),
            ),
            pretty_print=True,
        ).decode(),
    ))


def create_piece(mozpart, index):
    return E.Piece(
        E.labelStrings(
            E.string(str(index)),
            E.string(mozpart.type),
            E.string(mozpart.no),
        ),
        E.length(mozpart.length),
        E.quantity(str(mozpart.count)),
        E.completed('0'),
    )


def create_pieces(mozparts):
    return (
        create_piece(part, i + 1)
        for i, part in enumerate(
            sorted(mozparts, key=lambda p: p.no)
        )
    )


def create_settings(filename):
    tigername, _ = os.path.splitext(filename)
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
        E.printStrings(
            E.LabelField(
                E.header('Index'),
                E.fontSize('12'),
                E.x('0'),
                E.y('0'),
                E.column('0'),
            ),
            E.LabelField(
                E.header('Part'),
                E.fontSize('12'),
                E.x('0'),
                E.y('20'),
                E.column('3'),
            ),
            E.LabelField(
                E.header('No'),
                E.fontSize('12'),
                E.x('0'),
                E.y('40'),
                E.column('4'),
            ),
        ),
    )
