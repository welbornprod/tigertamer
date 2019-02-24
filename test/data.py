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
    # No room number, multi-cabs.
    '3,2,42,BR,3&5&6,Frame': {
        'no_split': [
            MozaikMasterPart({
                'count': 3,
                'width': '2',
                'length': '42',
                'no': 'R1:3&5&6',
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
        ]
    },
    # One room, multi-cabs.
    '8,1.5,42.5,TR,R2:9&10&11&13&15&16&17&18,': {
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
        ]
    },
}
