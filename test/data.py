#!/usr/bin/env python3
""" TigerTamer - Test - Data
    Test data for TigerTamer tests.
    -Christopher Welborn 2-24-19
"""

from ..lib.util.parser import (
    MozaikMasterPart,
)

# Test data for MozaikMasterFile:
mozmasterfile = {
    '1,2,42,BR,R1:1,Frame': {
        'desc': 'Basic single part with room number.',
        'no_split': [
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'type': 'BR',
                'no': 'R1:1',
                'extra_data': 'Frame',
            })
        ],
        'split': [
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'type': 'BR',
                'no': 'R1:1',
                'extra_data': 'Frame',
            }),
        ],
    },
    '2,2,42,BR,R1:1 R2:2&3,Frame': {
        'desc': 'Bad mozaik count, should be fixed automatically.',
        'no_split': [
            MozaikMasterPart({
                'count': 3,
                'width': '2',
                'length': '42',
                'type': 'BR',
                'no': 'R1:1 R2:2&3',
                'extra_data': 'Frame',
            })
        ],
        'split': [
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'type': 'BR',
                'no': 'R1:1',
                'extra_data': 'Frame',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'type': 'BR',
                'no': 'R2:2',
                'extra_data': 'Frame',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'type': 'BR',
                'no': 'R2:3',
                'extra_data': 'Frame',
            }),
        ],
    },
    '3,2,42,BR,3&5&6,Frame': {
        'desc': 'No room number, multi-cabs.',
        'no_split': [
            MozaikMasterPart({
                'count': 3,
                'width': '2',
                'length': '42',
                'no': '3&5&6',
                'type': 'BR',
                'extra_data': 'Frame',
            })
        ],
        'split': [
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'no': 'R1:3',
                'type': 'BR',
                'extra_data': 'Frame',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'no': 'R1:5',
                'type': 'BR',
                'extra_data': 'Frame',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '2',
                'length': '42',
                'no': 'R1:6',
                'type': 'BR',
                'extra_data': 'Frame',
            }),
        ],
    },
    '8,1.5,42.5,TR,R2:9&10&11&13&15&16&17&18,': {
        'desc': 'One room, multi-cabs.',
        'no_split': [
            MozaikMasterPart({
                'count': 8,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:9&10&11&13&15&16&17&18',
                'extra_data': '',
            })
        ],
        'split': [
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:9',
                'extra_data': '',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:10',
                'extra_data': '',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:11',
                'extra_data': '',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:13',
                'extra_data': '',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:15',
                'extra_data': '',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:16',
                'extra_data': '',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:17',
                'extra_data': '',
            }),
            MozaikMasterPart({
                'count': 1,
                'width': '1.5',
                'length': '42.5',
                'type': 'TR',
                'no': 'R2:18',
                'extra_data': '',
            }),
        ],
    },
}
