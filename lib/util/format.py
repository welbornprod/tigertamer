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
