#!/usr/bin/env python3
""" TigerTamer - Test - Data
    Test data for TigerTamer tests.
    -Christopher Welborn 2-24-19
"""

from ..lib.util.parser import (
    MozaikMasterPart,
)


def default_line(**kwargs):
    """ Returns a default mozaik .dat line, where pieces can be overwritten
        with kwargs.
    """
    defaults = default_partinfo(**kwargs)
    return ','.join(
        str(defaults[key])
        for key in MozaikMasterPart.header
    )


def default_masterpart(**kwargs):
    """ Returns a default MozaikMasterPart where pieces can be overwritten
        with kwargs.
    """
    return MozaikMasterPart(default_partinfo(**kwargs))


def default_partinfo(**kwargs):
    """ Returns a default dict of kwargs for constructing MozaikMasterParts,
        where pieces can be overwritten with kwargs.
    """
    return {
        'count': kwargs.get('count', 1),
        'width': str(kwargs.get('width', 2)),
        'length': str(kwargs.get('length', 42)),
        'type': str(kwargs.get('type', 'BR')),
        'no': str(kwargs.get('no', 'R1:1')),
        'extra_data': str(kwargs.get('extra_data', 'Frame')),
    }


# Test data for MozaikMasterFile:
mozmasterfile = {
    default_line(): {
        'desc': 'Basic single part with room number.',
        'no_split': [
            default_masterpart()
        ],
        'split': [
            default_masterpart(),
        ],
    },
    default_line(count=99): {
        'desc': 'Basic single part with count > 1.',
        'no_split': [
            default_masterpart(count=99),
        ],
        'split': [
            default_masterpart(count=99),
        ],
    },
    default_line(count=99, no='R1:1 R2:2'): {
        'desc': 'Basic double part with room number, bad cab count.',
        'no_split': [
            default_masterpart(count=2, no='R1:1 R2:2'),
        ],
        'split': [
            default_masterpart(count=1, no='R1:1'),
            default_masterpart(count=1, no='R2:2'),
        ],
    },
    default_line(count=2, no='R1:1 R2:2&3'): {
        'desc': 'Bad mozaik count, should be fixed automatically.',
        'no_split': [
            default_masterpart(count=3, no='R1:1 R2:2&3'),
        ],
        'split': [
            default_masterpart(count=1, no='R1:1'),
            default_masterpart(count=1, no='R2:2'),
            default_masterpart(count=1, no='R2:3'),
        ],
    },
    default_line(count=3, no='3&5&6'): {
        'desc': 'No room number, multi-cabs.',
        'no_split': [
            default_masterpart(count=3, no='3&5&6'),
        ],
        'split': [
            default_masterpart(count=1, no='R1:3'),
            default_masterpart(count=1, no='R1:5'),
            default_masterpart(count=1, no='R1:6'),
        ],
    },
    default_line(count=8, no='R2:9&10&11&13&15&16&17&18'): {
        'desc': 'One room, multi-cabs.',
        'no_split': [
            default_masterpart(count=8, no='R2:9&10&11&13&15&16&17&18'),
        ],
        'split': [
            default_masterpart(count=1, no='R2:9'),
            default_masterpart(count=1, no='R2:10'),
            default_masterpart(count=1, no='R2:11'),
            default_masterpart(count=1, no='R2:13'),
            default_masterpart(count=1, no='R2:15'),
            default_masterpart(count=1, no='R2:16'),
            default_masterpart(count=1, no='R2:17'),
            default_masterpart(count=1, no='R2:18'),
        ],
    },
}
