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
        'ii': {2, 6, 9},
        'iv': {5, 9, 0},
        'V': {7, 11, 2},
        'VI': {8, 0, 3},
        'vii': {2, 5, 11},

        'V/iv': {0, 4, 7},
        'V/V': {2, 6, 9},
        'V/VI': {3, 7, 10},
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

def _key_change(key, root):
    scale = [0, 2, 4, 5, 7, 9, 11] if key.isupper() else [0, 2, 3, 5, 7, 8, 11]
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

################################

import numpy as np

np.random.seed()

def transitions(harmony):
    chord, key = harmony.split('|')
    return _transitions[key][chord]

def notes(harmony):
    chord, key = harmony.split('|')
    return {
        (_keys[key] + note) % 12
        for note in _notes[key][chord]
    }

def apply_transition(key, transition):
    key = key.split('|')[-1]
    if '|' in transition:
        new_chord, key_change = transition.split('|')
        return "{}|{}".format(new_chord, _key_change(key, key_change))
    else:
        return "{}|{}".format(transition, key)

def enumerate_paths(data, idx, harmony):
    if idx >= len(data):
        return [([], 0)]
    chord, key = harmony.split('|')
    beat = data[idx]
    # dissonance coefficient
    coeff = 1. * beat['dissonance'] if 'dissonance' in beat else 0
    return [
        (
            [harmony] + tail,
            new_cost + _dissonance(harmony) * coeff + tail_cost
            + (float('inf') if 'harmony' in beat and harmony != beat['harmony'] else 0)
            + (100 if 's' in beat and beat['s'][0] % 12 not in notes(harmony) else 0)
            + (100 if 'a' in beat and beat['a'][0] % 12 not in notes(harmony) else 0)
            + (100 if 't' in beat and beat['t'][0] % 12 not in notes(harmony) else 0)
            + (100 if 'b' in beat and beat['b'][0] % 12 not in notes(harmony) else 0)
        )
        for transition, new_cost in transitions(harmony).items()
        for tail, tail_cost in enumerate_paths(data, idx + 1, apply_transition(harmony, transition))
    ]

def softmax(x):
    r=np.exp(x - np.max(x))
    return r/r.sum(axis=0)

def voicing_line_cost(prev, this):
    diff = abs(prev[-1] - this[0])
    cost = 0
    if diff in [6, 10, 11]:
        cost += 2
    if diff > 0: # prefer common-tone
        cost += 1
    if diff > 1: # prefer half-steps
        cost += 1
    if cost > 3: # avoid leaps
        cost += 3
    cost += diff * .1
    return cost

def voicing_spacing_cost(chord):
    coeff = .1 * chord['spacing'] if 'spacing' in chord else 0
    for i in 'satb':
        if i not in chord:
            return 0
    cost = 0
    s,a,t,b = [chord[i][0] for i in 'satb']
    if s - a > 12:
        cost += 1
    if a - t > 12:
        cost += 1
    if a >= s:
        cost += 1
    if t >= a:
        cost += 1
    if b >= t:
        cost += 1

    cost += (s - a) * coeff
    cost += (a - t) * coeff
    cost += (t - b) * coeff

    return cost

def voicing_parallel_intervals_cost(prev, this):
    for i in 'satb':
        if i not in this or i not in prev:
            return 0
    cost = 0
    for i in 'satb':
        for j in 'satb':
            if i != j:
                if this[i][0] - prev[i][0] == this[j][0] - prev[j][0]:
                    if (this[i][0] - this[j][0]) % 12 in [7, 0]:
                        cost += 10
    return cost

def voicing_cost(prev, this, next):
    return sum([
        voicing_line_cost(prev[i], this[i])
        for i in 'satb'
        if i in prev
        and i in this
    ] + [
        voicing_line_cost(this[i], next[i])
        for i in 'satb'
        if i in this
        and i in next
    ] + [
        voicing_spacing_cost(this),
        voicing_parallel_intervals_cost(prev, this),
    ]) * 5

def enumerate_notes(prev, next, harmony):
    return [
        ({
            's': (s,),
            'a': (a,),
            't': (t,),
            'b': (b,),
        }, voicing_cost(prev, {
            's': (s,),
            'a': (a,),
            't': (t,),
            'b': (b,),
        }, next))
        for s in _ranges['s']
        for a in _ranges['a']
        for t in _ranges['t']
        for b in _ranges['b']
        if  s % 12 in notes(harmony)
        and a % 12 in notes(harmony)
        and t % 12 in notes(harmony)
        and b % 12 in notes(harmony)
    ]

def autocomplete(data):
    # find path in key/chord graph
    paths, costs = zip(*enumerate_paths(data, 0, data[0]['harmony']))
    np_costs = np.array(costs)
    probs = softmax(-np_costs)
    path_idx = np.random.choice(np.arange(len(paths)), p=probs)
    path = paths[path_idx]

    # set next key/chord
    harmony = path[1]
    if 'harmony' not in data[1]:
        data[1]['harmony'] = harmony

    # pick notes based on key/chord
    voicings, costs = zip(*enumerate_notes(data[0], data[2], harmony))
    np_costs = np.array(costs)
    probs = softmax(-np_costs)
    voicings_idx = np.random.choice(np.arange(len(voicings)), p=probs)
    voicing = voicings[voicings_idx]

    # set notes
    data[1] = dict(voicing.items() + data[1].items())

    return data

