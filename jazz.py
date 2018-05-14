PIANO = {'s': 0, 'a': 0, 't': 0, 'b': 0}
STRING_QUARTET = {'s': 41, 'a': 41, 't': 42, 'b': 43} # 2 violins, viola, cello
WOODWIND_QUARTET = {'s': 74, 'a': 69, 't': 72, 'b': 72} # flute, oboe, clarinet, bassoon
SAX_QUARTET = {'s': 65, 'a': 66, 't': 67, 'b': 68} # soprano, alto, tenor, bari
BRASS_QUARTET = {'s': 57, 'a': 57, 't': 58, 'b': 59} # 2 trumpets, trombone, tuba
JAZZ_QUARTET = {'s': 57, 'a': 0, 't': 0, 'b': 33}
_instruments = JAZZ_QUARTET

_major_keys = [
    'C',
    'C#',
    'D',
    'Eb',
    'E',
    'F',
    'F#',
    'G',
    'Ab',
    'A',
    'Bb',
    'B',
]
_minor_keys = [
    key.lower()
    for key in _major_keys
]

_keys = {}
_keys.update({
    key: midi
    for midi, key in enumerate(_major_keys)
})
_keys.update({
    key: midi
    for midi, key in enumerate(_minor_keys)
})

_transitions = {}
_transitions.update({
    key: {
        'I': {
            'I7': 1,
        },
        'I7': {
            # 'VI7': 2,
            # 'vi7': 2,
            # 'iibdim7': 2,
            # 'IV7': 1,
            # 'V7|IV': 2,
            # 'V7|VI': 3,
            # 'ii7|VIIb': 3,
            # 'V7|VIIb': 3,
            'ii7b5|vi': 1,
        },

        'Ima7': {
            'VI7': 2,
            'vi7': 2,
            'iibdim7': 2,
            'iii7': 3,
            'IVma7': 1,
            'V7|IV': 2,
            'V7|VI': 3,
            'ii7|VIIb': 3,
            'V7|VIIb': 3,
        },
        'iibdim7': {
            'ii7': 1,
        },
        'II7': {
            'ii7': 1,
            'V7': 1,
        },
        'ii7': {
            'V7': 1,
        },
        'III7': {
            'VI7': 1,
            'vi7': 1,
        },
        'iii7': {
            'VI7': 1,
            'vi7': 1,
        },

        'IV7': {
            'I7': 1,
            'V7': 1,
        },
        'IVma7': {
            'Ima7': 1,
            'V7': 1,
        },

        'V7': {
            'I7': 1,
            'Ima7' : 1,
        },

        'VI7': {
            'ii7': 1,
        },

        'vi7': {
            'II7': 2,
            'ii7': 1,
        },
        
        'viidim7': {
            'III7': 1,
        }
    }
    for key in _major_keys
})
_transitions.update({
    key: {
        'i7': {
            'ii7b5': 1,
            'iv7': 1,
        },
        'ii7b5': {
            'V7': 1,
        },
        'iv7': {
            'i7': 1,
            'III7': 1
        },
        'V7': {
            'i7': 1
        },
        'III7': {
            'I|III': 1
        },
    }
    for key in _minor_keys
})

_notes = {}
_notes.update({
    key: {
        'I': {0, 4, 7},
        'Ima7': {0, 4, 7, 11},
        'I7': {0, 4, 7, 10},

        'iibdim7': {1, 4, 7, 10},

        'II7': {2, 6, 9, 0},
        'ii7': {2, 5, 9, 0},

        'III7': {4, 8, 11, 2},
        'iii7': {4, 7, 11, 2},

        'IVma7': {5, 9, 0, 4},
        'IV7': {5, 9, 0, 3},

        'V7': {7, 11, 2, 5},

        'VI7': {9, 1, 4, 7},
        'vi7': {9, 0, 4, 7},

        'viidim7': {11, 2, 5, 9}
    }
    for key in _major_keys
})
_notes.update({
    key: {
        'i7': {0, 3, 7, 10},

        'ii7b5': {2, 5, 8, 0},

        'iv7': {5, 8, 0, 3},

        'V7': {7, 11, 2, 5},
        'III7': {10, 2, 5, 8}
    }
    for key in _minor_keys
})
_notes = {
    key: {
        chord: {
            (note + _keys[key]) % 12
            for note in notes
        }
        for chord, notes in d.items()
    }
    for key, d in _notes.items()
}

def _scale(key):
    scale = [0, 2, 4, 5, 7, 9, 11] if key.isupper() else [0, 2, 3, 5, 7, 8, 11]
    return [
        (note + _keys[key]) % 12
        for note in scale
    ]

def _key_change(key, root):
    scale = _scale(key)
    num_to_roman = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii']
    roman_to_num = {
        roman: scale[num]
        for num, roman in enumerate(num_to_roman)
    }
    flat = 0
    if root[-1] == 'b':
        flat = -1
        root = root[:-1]
    tonic = (roman_to_num[root.lower()] + flat) % 12
    return _major_keys[tonic] if root.isupper() else _minor_keys[tonic]

_ranges = {
    's': list(range(60, 81)),
    'a': list(range(53, 74)),
    't': list(range(47, 67)),
    'b': list(range(40, 60)),
}

def _dissonance(harmony):
    chord = harmony.split('|')[0]
    return (1. if chord in {}
        else .8 if chord in {'vii'}
        else .4 if chord.lower()
        else 0.
    )

def _input_harmony(keys):
    major_chords = [
        'Ima7',
        'iibdim7',
        'ii',
        'IV7',
        'iii7',
        'IVma7',
        'II7',
        'V7',
        'I7',
        'vi7',
        'I7',
        'Ima7',
    ]

    minor_chords = [
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
        'i7',
    ]

    if len(keys) == 0:
        return 'I|C'
    elif len(keys) == 1:
        return "I|{}".format(_major_keys[keys[0] % 12])
    elif len(keys) == 2:
        return "{}|{}".format(
            major_chords[(keys[1] - keys[0]) % 12],
            _major_keys[keys[0] % 12],
        )
    elif len(keys) == 3:
        interval = (keys[1] - keys[0]) % 12
        if interval == 4:
            return "{}|{}".format(
                major_chords[(keys[2] - keys[0]) % 12],
                _major_keys[keys[0] % 12],
            )
        elif interval == 3:
            return "{}|{}".format(
                minor_chords[(keys[2] - keys[0]) % 12],
                _minor_keys[keys[0] % 12],
            )
        else:
            return 'I|C'
    elif len(keys) == 4:
        interval = (keys[1] - keys[0]) % 12
        base = (keys[2] - keys[0]) % 12
        secondary = (keys[3] - keys[2]) % 12 # assume V
        if interval == 4:
            return "{}|{}".format(
                "{}/{}".format(
                    'V',
                    major_chords[(keys[2] - keys[0]) % 12]
                ),
                _major_keys[keys[0] % 12],
            )
        elif interval == 3:
            return "{}|{}".format(
                "{}/{}".format(
                    'V',
                    minor_chords[(keys[2] - keys[0]) % 12]
                ),
                _minor_keys[keys[0] % 12],
            )
        else:
            return 'I|C'
    else:
        return 'I|C'
