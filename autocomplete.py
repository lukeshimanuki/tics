import numpy as np
import copy

import collections
import time
prev_time = dict()
runtime = collections.defaultdict(int)
def atime(i):
    global prev_time
    #prev_time[i] = time.time()
    pass
def btime(i):
    #runtime[i] += time.time() - prev_time[i]
    pass

config = __import__('classical')

def autocomplete_config(name):
    global config
    config = __import__(name)

np.random.seed()

def transitions(harmony):
    chord, key = harmony.split('|')
    return config._transitions[key][chord]

def notes_fn(harmony):
    chord, key = harmony.split('|')
    return {
        (config._keys[key] + note) % 12
        for note in config._notes[key][chord]
    } if chord in config._notes[key] else []

all_chords = {
    chord
    for key in config._keys
    for chord in config._transitions[key]
}
harmonies = {
    "{}|{}".format(chord, key)
    for chord in all_chords
    for key in config._keys
}
notes = {
    harmony: notes_fn(harmony)
    for harmony in harmonies
}
dissonance = {
    harmony: config._dissonance(harmony)
    for harmony in harmonies
}

def apply_transition(key, transition):
    atime('apply_transition')
    key = key.split('|')[-1]
    if '|' in transition:
        new_chord, key_change = transition.split('|')
        retval = "{}|{}".format(new_chord, config._key_change(key, key_change))
    else:
        retval = "{}|{}".format(transition, key)
    btime('apply_transition')
    return retval

def get_first(notes):
    for note in notes:
        if note is not None and note != -1:
            return note
    return 60
def get_last(notes):
    return get_first(notes[::-1])
def get_voice(notes):
    l = len(notes)
    if len(notes) == 0:
        return 60
    elif len(notes) == 1:
        if not notes[0] is None and notes[0] != -1:
            return notes[0]
        else:
            return 60
    elif not notes[0] is None and notes[0] != -1:
        return notes[0]
    else:
        for i in range(2,l):
            if len(notes) % i == 0:
                for j in range(l / i):
                    if not notes[i * j] is None and notes[i * j] != -1:
                        return notes[i * j]
        return 60

def enumerate_paths(data, idx, harmony):
    if idx >= len(data):
        return [([], 0)]
    chord, key = harmony.split('|')
    beat = data[idx]
    if 'harmony' in beat and harmony != beat['harmony']:
        return [(harmony, float('inf'))]
    # dissonance coefficient
    coeff = -1. * beat['dissonance'] if 'dissonance' in beat else 0
    dissonance_cost = dissonance[harmony] * coeff
    hnotes = notes[harmony]
    vcost = sum(
        100 if part in beat and get_voice(beat[part]) % 12 not in hnotes else 0
        for part in 'satb'
    )
    return [
        (
            tail if idx == 0 else harmony,
            new_cost + dissonance_cost + tail_cost + vcost
        )
        for transition, new_cost in transitions(harmony).items()
        for tail, tail_cost in enumerate_paths(data, idx + 1, apply_transition(harmony, transition))
    ]

def softmax(x):
    r=np.exp(x - np.max(x))
    return r/r.sum(axis=0)

def voicing_line_cost(prev, this):
    diff = abs(get_last(prev) - get_first(this))
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

def voicing_spacing_cost(chord, beat):
    coeff = -.5 * beat['spacing'] if 'spacing' in beat else 0
    for i in 'satb':
        if i not in chord:
            return 0
    cost = 0
    s,a,t,b = [get_voice(chord[i]) for i in 'satb']
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
    cost *= 10

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
                if get_voice(this[i]) - get_voice(prev[i]) == get_voice(this[j]) - get_voice(prev[j]):
                    if (get_voice(this[i]) - get_voice(this[j])) % 12 in [7, 0]:
                        cost += 10
    return cost

def voicing_cost(prev, this, next, beat):
    atime('voicing_cost')
    voice_notes = [get_voice(this[part]) % 12 for part in 'satb']
    cost = sum([
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
        voicing_spacing_cost(this, beat),
        voicing_parallel_intervals_cost(prev, this),
    ] + [
        3. if note not in voice_notes else 0
        for note in notes[beat['harmony']]
    ]) * 5
    btime('voicing_cost')
    return cost

def enumerate_notes(prev, next, harmony, beat):
    atime('enumerate_notes')
    hranges = {
        part: [
            note
            for note in config._ranges[part]
            if note % 12 in notes[harmony]
        ]
        for part in 'satb'
    }
    l = [
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
        }, next, beat))
        for s in hranges['s']
        for a in hranges['a']
        for t in hranges['t']
        for b in hranges['b']
    ]
    btime('enumerate_notes')
    return l

def decorate(base, chord, scale):
    if np.random.randint(0,100) < 20:
        return [base]
    for i in range(100):
        next_note = np.random.randint(base - 5, base + 6)
        if next_note % 12 not in chord and not (abs(next_note - base) <= 2 and next_note % 12 in scale) or next_note not in config._ranges['s']:
            continue
        return [base] + decorate(next_note, chord, scale)
    return [base]

def autocomplete(data):
    atime('autocomplete')

    # retain rhythm
    if 'mel_rhythm' not in data[1]:
        if 'mel_rhythm' in data[0]:
            data[1]['mel_rhythm'] = copy.deepcopy(data[0]['mel_rhythm'])
        else:
            data[1]['mel_rhythm'] = (True,)

    if 'acc_rhythm' not in data[1]:
        if 'acc_rhythm' in data[0]:
            data[1]['acc_rhythm'] = copy.deepcopy(data[0]['acc_rhythm'])
        else:
            data[1]['acc_rhythm'] = {'a': (True,), 't': (True,), 'b': (True,)}

    atime(1)
    # find path in key/chord graph
    paths, costs = zip(*enumerate_paths(data, 0, data[0]['harmony']))
    np_costs = np.array(costs)
    probs = softmax(-np_costs)
    path_idx = np.random.choice(np.arange(len(paths)), p=probs)
    path = paths[path_idx]
    btime(1)

    # set next key/chord
    harmony = path
    if 'harmony' not in data[1]:
        data[1]['harmony'] = harmony

    atime(2)
    # pick notes based on key/chord
    voicings, costs = zip(*enumerate_notes(data[0], data[2], harmony, data[1]))
    np_costs = np.array(costs)
    probs = softmax(-np_costs)
    voicings_idx = np.random.choice(np.arange(len(voicings)), p=probs)
    voicing = voicings[voicings_idx]
    btime(2)

    # set notes
    data[1] = dict(voicing.items() + data[1].items())

    # decorations
    atime(3)
    decorated = tuple(decorate(get_first(data[1]['s']), notes[data[1]['harmony']], config._scale(data[1]['harmony'].split('|')[1])))
    data[1]['s'] = decorated
    btime(3)

    # apply rhythm to voices
    atime(4)
    print(data)
    for part in 'atb':
        p_notes = data[1][part]
        data[1][part] = tuple(
            p_notes[idx % len(p_notes)] if value == True else -1 if value == -1 else None
            for idx,value in enumerate(data[1]['acc_rhythm'][part])
        )
    s_notes = data[1]['s']
    data[1]['s'] = tuple(
        s_notes[idx % len(s_notes)] if value == True else -1 if value == -1 else None
        for idx,value in enumerate(data[1]['mel_rhythm'])
    )
    btime(4)

    btime('autocomplete')

    #print("RUNTIME\n-------")
    #for i, t in runtime.items():
    #    print("{}: {}".format(i, t))
    #print("-------")

    return data

