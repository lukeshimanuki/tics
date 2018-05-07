PIANO = {'s': 0, 'a': 0, 't': 0, 'b': 0}
STRING_QUARTET = {'s': 41, 'a': 41, 't': 42, 'b': 43} # 2 violins, viola, cello
WOODWIND_QUARTET = {'s': 74, 'a': 69, 't': 72, 'b': 72} # flute, oboe, clarinet, bassoon
SAX_QUARTET = {'s': 65, 'a': 66, 't': 67, 'b': 68} # soprano, alto, tenor, bari
_instruments = PIANO

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
            'ii': 1,
            'iii': 1,
            'IV': 1,
            'V': 1,
            'vi': 1,

            'V/ii': 1,
            'V/IV': 1,
            'V/V': 1,
            'V/vi': 1,

            'iii|IV': 1, # modulate to IV
            'ii|V': 1, # modulate to V
            'iv|vi': 1, # modulate to vi
        },
        'ii': {
            'V': 1,
            'vii': 1,
        },
        'iii': {
            'I': 1,
            'vi': 1,
        },
        'IV': {
            'I': 1,
            'V': 1,
        },
        'V': {
            'I': 1,
            'vi': 1,
        },
        'vi': {
            'ii': 1,
            'IV': 1,
        },
        'vii': {
            'I': 1,
        },

        'V/ii': {
            'ii': 1,
        },
        'V/IV': {
            'IV': 1,
        },
        'V/V': {
            'V': 1,
        },
        'V/vi': {
            'vi': 1,
        },
    }
    for key in _major_keys
})
_transitions.update({
    key: {
        'i': {
            'ii': 1,
            'iv': 1,
            'V': 1,
            'VI': 1,

            'V/iv': 1,
            'V/V': 1,
            'V/VI': 1,

            'V|iv': 1, # modulate to iv
            'iv|v': 1, # modulate to v
            'ii|III': 1, # modulate to III

            'N': 1,
            'It+6': 1,
            'Fr+6': 1,
            'Ger+6': 1,
        },
        'ii': {
            'V': 1,
            'vii': 1,
        },
        'iv': {
            'i': 1,
            'V': 1,
        },
        'V': {
            'i': 1,
            'VI': 1,
        },
        'VI': {
            'ii': 1,
            'iv': 1,
        },
        'vii': {
            'i': 1,
        },

        'V/iv': {
            'iv': 1,
        },
        'V/V': {
            'V': 1,
        },
        'V/VI': {
            'VI': 1,
        },

        'N': {
            'V': 1,
            'vii': 1,
            'V/V': 1,
        },
        'It+6': {
            'V': 1,
            'vii': 1,
            'V/V': 1,
        },
        'Fr+6': {
            'V': 1,
            'vii': 1,
            'V/V': 1,
        },
        'Ger+6': {
            'vii': 1,
            'V/V': 1,
        },
    }
    for key in _minor_keys
})

_notes = {}
_notes.update({
    key: {
        'I': {0, 4, 7},
        'ii': {2, 5, 9},
        'iii': {4, 7, 11},
        'IV': {5, 9, 0},
        'V': {7, 11, 2},
        'vi': {9, 0, 4},
        'vii': {2, 5, 11},

        'V/ii': {9, 1, 4},
        'V/IV': {0, 4, 7},
        'V/V': {2, 6, 9},
        'V/vi': {4, 8, 11},
    }
    for key in _major_keys
})
_notes.update({
    key: {
        'i': {0, 3, 7},
        'ii': {2, 5, 8},
        'iv': {5, 8, 0},
        'V': {7, 11, 2},
        'VI': {8, 0, 3},
        'vii': {2, 5, 11},

        'V/iv': {0, 4, 7},
        'V/V': {2, 6, 9},
        'V/VI': {3, 7, 10},

        'N': {1, 5, 8},
        'It+6': {6, 8, 0},
        'Fr+6': {6, 8, 0, 2},
        'Ger+6': {6, 8, 0, 3},
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
    tonic = (_keys[key] + roman_to_num[root.lower()]) % 12
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
        'I',
        'I',
        'ii',
        'I',
        'iii',
        'IV',
        'I',
        'V',
        'I',
        'vi',
        'I',
        'vii',
    ]

    minor_chords = [
        'i',
        'N',
        'ii',
        'i',
        'Fr+6',
        'iv',
        'i',
        'V',
        'VI',
        'i',
        'i',
        'vii',
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

