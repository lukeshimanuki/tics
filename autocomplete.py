import numpy as np

np.random.seed()

# {chord: (key_change, new_chord): cost}
transitions = {
	'I': {
		(0, 'ii'): 1,
		(0, 'IV'): 1,
		(0, 'V'): 1,
		(0, 'vi'): 1,
	},
	'ii': {
		(0, 'V'): 1,
	},
	'IV': {
		(0, 'I'): 1,
		(0, 'V'): 1,
	},
	'V': {
		(0, 'I'): 1,
		(0, 'vi'): 1,
	},
	'vi': {
		(0, 'ii'): 1,
		(0, 'IV'): 1,
	},
}

notes = {
	'I': {0, 4, 7},
	'ii': {2, 5, 9},
	'IV': {5, 9, 0},
	'V': {7, 11, 2},
	'vi': {9, 0, 4},
}

ranges = {
	's': list(range(60, 81)),
	'a': list(range(53, 74)),
	't': list(range(47, 67)),
	'b': list(range(40, 60)),
}

def enumerate_paths(data, idx, key, chord):
	if idx >= len(data):
		return [([], 0)]
	return [
		(
			[(key, chord)] + tail,
			new_cost + tail_cost
			+ (float('inf') if 'chord' in data[idx] and chord != data[idx]['chord'] else 0)
			+ (float('inf') if 'key' in data[idx] and key != data[idx]['key'] else 0)
			+ (100 if 's' in data[idx] and (data[idx]['s'] - key) % 12 not in notes[chord] else 0)
			+ (100 if 'a' in data[idx] and (data[idx]['a'] - key) % 12 not in notes[chord] else 0)
			+ (100 if 't' in data[idx] and (data[idx]['t'] - key) % 12 not in notes[chord] else 0)
			+ (100 if 'b' in data[idx] and (data[idx]['b'] - key) % 12 not in notes[chord] else 0)
		)
		for (new_key, new_chord), new_cost in transitions[chord].items()
		for tail, tail_cost in enumerate_paths(data, idx + 1, (key + new_key) % 12, new_chord)
	]

def softmax(x):
    r=np.exp(x - np.max(x))
    return r/r.sum(axis=0)

def voicing_cost(prev, this, next):
	return 1

def enumerate_notes(prev, next, key, chord):
	return [
		({
			's': s,
			'a': a,
			't': t,
			'b': b,
		}, voicing_cost(prev, notes, next))
		for s in ranges['s']
		for a in ranges['a']
		for t in ranges['t']
		for b in ranges['b']
		if (s - key) % 12 in notes[chord]
		and (a - key) % 12 in notes[chord]
		and (t - key) % 12 in notes[chord]
		and (b - key) % 12 in notes[chord]
	]

def autocomplete(data):
	# find path in key/chord graph
	paths, costs = zip(*enumerate_paths(data, 0, data[0]['key'], data[0]['chord']))
	np_costs = np.array(costs)
	probs = softmax(-np_costs)
	path_idx = np.random.choice(np.arange(len(paths)), p=probs)
	path = paths[path_idx]

	# set next key/chord
	key, chord = path[1]
	data[1]['key'] = key
	data[1]['chord'] = chord

	# pick notes based on key/chord
	voicings, costs = zip(*enumerate_notes(data[0], data[2], key, chord))
	np_costs = np.array(costs)
	probs = softmax(-np_costs)
	voicings_idx = np.random.choice(np.arange(len(voicings)), p=probs)
	voicing = voicings[voicings_idx]

	# set notes
	data[1]['s'] = voicing['s']
	data[1]['a'] = voicing['a']
	data[1]['t'] = voicing['t']
	data[1]['b'] = voicing['b']

	return data

