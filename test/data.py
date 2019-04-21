#!/usr/bin/env python3
""" TigerTamer - Test - Data
    Test data for TigerTamer tests.
    -Christopher Welborn 2-24-19
"""

from ..lib.util.parser import (
    MozaikPart,
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


def default_mozaikpart(**kwargs):
    """ Returns a default MozaikPart where pieces can be overwritten
        with kwargs.
    """
    d = default_partinfo(**kwargs)
    d.pop('width')
    return MozaikPart(d)


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


# Test data for MozaikMasterFile part combining.
class CombinedTestItem(object):
    def __init__(self, *, desc=None, lines=None, expected=None):
        self.desc = desc
        self.lines = lines
        self.expected = expected

    def __hash__(self):
        return hash(''.join(str(s) for s in self.lines))


# Test data for MozaikMasterFile room/part splitting:
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
    default_line(count=2, no='R2:9(2)'): {
        'desc': 'One room, one part, with part quantity.',
        'no_split': [
            default_masterpart(count=2, no='R2:9(2)'),
        ],
        'split': [
            default_masterpart(count=2, no='R2:9(2)'),
        ],
    },
    default_line(count=3, no='R2:9(2) R1:1'): {
        'desc': 'Two rooms, one part, with part quantity first.',
        'no_split': [
            default_masterpart(count=3, no='R2:9(2) R1:1'),
        ],
        'split': [
            default_masterpart(count=2, no='R2:9(2)'),
            default_masterpart(count=1, no='R1:1'),
        ],
    },
    default_line(count=3, no='R2:9 R1:1(2)'): {
        'desc': 'Two rooms, one part, with part quantity last.',
        'no_split': [
            default_masterpart(count=3, no='R2:9 R1:1(2)'),
        ],
        'split': [
            default_masterpart(count=1, no='R2:9'),
            default_masterpart(count=2, no='R1:1(2)'),
        ],
    },
    default_line(count=4, no='R3:1 R2:9(2) R1:1'): {
        'desc': 'Three rooms, one part, with part quantity middle.',
        'no_split': [
            default_masterpart(count=4, no='R3:1 R2:9(2) R1:1'),
        ],
        'split': [
            default_masterpart(count=1, no='R3:1'),
            default_masterpart(count=2, no='R2:9(2)'),
            default_masterpart(count=1, no='R1:1'),
        ],
    },
    # Issue #7
    default_line(count=4, no='R1:7(2)&8(2)'): {
        'desc': 'One room, two parts, both with quantity.',
        'no_split': [
            default_masterpart(count=4, no='R1:7(2)&8(2)'),
        ],
        'split': [
            default_masterpart(count=2, no='R1:7(2)'),
            default_masterpart(count=2, no='R1:8(2)'),
        ],
    },
    default_line(count=6, no='R1:7(2)&8(2) R2:3(2)'): {
        'desc': 'Two rooms, three parts, all with quantity.',
        'no_split': [
            default_masterpart(count=4, no='R1:7(2)&8(2) R2:3(2)'),
        ],
        'split': [
            default_masterpart(count=2, no='R1:7(2)'),
            default_masterpart(count=2, no='R1:8(2)'),
            default_masterpart(count=2, no='R2:3(2)'),
        ],
    },
    default_line(count=20, no='R1:7(2)&8(2) R2:3(2)&7(3)&8(5) R3:1 R4:4(5)'): {
        'desc': 'Four rooms, seven parts, with mixed quantity.',
        'no_split': [
            default_masterpart(
                count=20,
                no='R1:7(2)&8(2) R2:3(2)&7(3)&8(5) R3:1 R4:4(5)'
            ),
        ],
        'split': [
            default_masterpart(count=2, no='R1:7(2)'),
            default_masterpart(count=2, no='R1:8(2)'),
            default_masterpart(count=2, no='R2:3(2)'),
            default_masterpart(count=3, no='R2:7(3)'),
            default_masterpart(count=5, no='R2:8(5)'),
            default_masterpart(count=1, no='R3:1'),
            default_masterpart(count=5, no='R4:4(5)'),
        ],
    },
    default_line(
        count=20,
        no='R1:7(2)&8(2)&9 R2:3(2)&5&7(3)&8(5) R3:1&2 R4:3&4(5)'
    ): {
        'desc': 'Four rooms, twenty-four parts, with mixed quantity.',
        'no_split': [
            default_masterpart(
                count=24,
                no='R1:7(2)&8(2)&9 R2:3(2)&5&7(3)&8(5) R3:1&2 R4:3&4(5)'
            ),
        ],
        'split': [
            default_masterpart(count=2, no='R1:7(2)'),
            default_masterpart(count=2, no='R1:8(2)'),
            default_masterpart(count=1, no='R1:9'),
            default_masterpart(count=2, no='R2:3(2)'),
            default_masterpart(count=1, no='R2:5'),
            default_masterpart(count=3, no='R2:7(3)'),
            default_masterpart(count=5, no='R2:8(5)'),
            default_masterpart(count=1, no='R3:1'),
            default_masterpart(count=1, no='R3:2'),
            default_masterpart(count=1, no='R4:3'),
            default_masterpart(count=5, no='R4:4(5)'),
        ],
    },
}

mozmasterfile_combined = [
    CombinedTestItem(
        desc='No parts to combine.',
        lines=[
            default_line(count=1, no='R1:1'),
            default_line(count=2, no='R1:2(2)'),
        ],
        expected=[
            default_mozaikpart(count=1, no='R1:1'),
            default_mozaikpart(count=2, no='R1:2(2)'),
        ],
    ),
    CombinedTestItem(
        desc='Missing quantity, no parts to combine.',
        lines=[
            default_line(count=2, no='R1:1'),
            default_line(count=2, no='R1:2'),
        ],
        expected=[
            default_mozaikpart(count=2, no='R1:1(2)'),
            default_mozaikpart(count=2, no='R1:2(2)'),
        ],
    ),
    CombinedTestItem(
        desc='Missing quantity.',
        lines=[
            default_line(count=2, no='R1:1'),
            default_line(count=2, no='R1:1'),
        ],
        expected=[
            default_mozaikpart(count=4, no='R1:1(4)'),
        ],
    ),
    CombinedTestItem(
        desc='Basic part combining.',
        lines=[
            default_line(count=1, no='R1:1'),
            default_line(count=2, no='R1:1(2)'),
        ],
        expected=[
            default_mozaikpart(count=3, no='R1:1(3)'),
        ],
    ),
    CombinedTestItem(
        desc='Multiple part combining.',
        lines=[
            default_line(count=1, no='R1:1'),
            default_line(count=2, no='R1:1(2)'),
            default_line(count=3, no='R1:1(3)'),
            default_line(count=4, no='R1:1(4)'),
        ],
        expected=[
            default_mozaikpart(count=10, no='R1:1(10)'),
        ],
    ),
    CombinedTestItem(
        desc='Multiple room, multiple part combining.',
        lines=[
            default_line(count=1, no='R1:1'),
            default_line(count=2, no='R1:1(2)'),
            default_line(count=1, no='R2:1'),
            default_line(count=2, no='R2:1(2)'),
        ],
        expected=[
            default_mozaikpart(count=3, no='R1:1(3)'),
            default_mozaikpart(count=3, no='R2:1(3)'),
        ],
    ),
    CombinedTestItem(
        desc='Multiple room, multiple part, mixed line combining.',
        lines=[
            default_line(count=17, no='R1:1 R2:2(2)&3(3)&4 R3:1(10)'),
            default_line(count=22, no='R1:1(2)&2&3(7) R3:3(6)&1(1) R2:3(5)'),
            default_line(count=1, no='R1:1'),
            default_line(count=3, no='R1:1(3)'),
            default_line(count=1, no='R2:2'),
            default_line(count=3, no='R2:2(3)'),
            default_line(count=1, no='R3:1'),
            default_line(count=1, no='R3:1(1)'),
        ],
        expected=[
            default_mozaikpart(count=7, no='R1:1(7)'),
            default_mozaikpart(count=1, no='R1:2'),
            default_mozaikpart(count=7, no='R1:3(7)'),
            default_mozaikpart(count=6, no='R2:2(6)'),
            default_mozaikpart(count=8, no='R2:3(8)'),
            default_mozaikpart(count=1, no='R2:4'),
            default_mozaikpart(count=13, no='R3:1(13)'),
            default_mozaikpart(count=6, no='R3:3(6)'),
        ],
    ),
]
