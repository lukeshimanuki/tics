from kivy.graphics.instructions import InstructionGroup
from common.core import *
import copy

import classical as config

class Input(InstructionGroup):
    def __init__(self, on_beat_update_callback=lambda beat : None):
        super(Input, self).__init__()

        self.parts_enabled = set()
        self.input_notes = set()
        #self.beat = {}
        self.beat_needs_update = False
        self.on_beat_update = on_beat_update_callback

        self.velocity = 64

        try:
            # Attempt to set up MIDI input, if rtmidi is installed.
            import rtmidi
            #from rtmidi import midiconstants
            class midiconstants:
                NOTE_OFF = 0x80
                NOTE_ON = 0x90
            self.midi_in = rtmidi.MidiIn(name='TICS')
            available_ports = self.midi_in.get_ports()
            print(available_ports)
            self.midi_in.open_port(24)
            print('Opened MIDI port.')
            self.last_msg = None
            def midi_callback(msgtime, _ = None):
                msg, time = msgtime
                if msg[0] == midiconstants.NOTE_ON and msg[0:2] != self.last_msg:
                    self.on_midi_down(msg[1])
                    self.last_msg = msg[0:2]
                    # TODO: set velocity
                elif msg[0] == midiconstants.NOTE_OFF and msg[0:2] != self.last_msg:
                    self.on_midi_up(msg[1])
                    self.last_msg = msg[0:2]
            self.midi_in.set_callback(midi_callback)
        except Exception as e:
            print(e)
            print('MIDI support disabled.')

    def reset(self):
        self.input_notes = set()
        #self.beat = {}
        self.beat_needs_update = True

    def set_part_enabled(self, part, enabled):
        if enabled and part not in self.parts_enabled:
            self.parts_enabled.add(part)
        elif not enabled and part in self.parts_enabled:
            self.parts_enabled.remove(part)

    # Number of enabled note parts (i.e. 's', 'a', 't', 'b')
    def num_input_note_parts(self):
        return len([part for part in 'satb' if part in self.parts_enabled])

    def on_key_down(self, keycode, modifiers):
        midi_value = lookup(keycode[1], '1234567890', [72, 74, 76, 77, 79, 81, 83, 84, 86, 88])
        if midi_value is not None:
            self.on_midi_down(midi_value)

    def on_key_up(self, keycode):
        midi_value = lookup(keycode[1], '1234567890', [72, 74, 76, 77, 79, 81, 83, 84, 86, 88])
        if midi_value is not None:
            self.on_midi_up(midi_value)

    def on_midi_down(self, midi_value):
        if midi_value not in self.input_notes:
            self.input_notes.add(midi_value)
            self.beat_needs_update = True

    def on_midi_up(self, midi_value):
        if midi_value in self.input_notes:
            self.input_notes.remove(midi_value)

    def populate_beat_with_notes(self, notes):
        beat = {}

        sorted_notes = sorted(notes, reverse=True)

        # Assign notes for parts in descending order
        active_note_parts = [part for part in 'satb' if part in self.parts_enabled]
        for index, part in enumerate(active_note_parts):
            beat[part] = (sorted_notes[index],)

        sorted_notes = sorted_notes[len(active_note_parts):]

        if 'spacing' in self.parts_enabled and len(sorted_notes) >= 2:
            spacing_notes = sorted_notes[:2]
            spacing = spacing_notes[0] - spacing_notes[1]
            beat['spacing'] = spacing / 6. - 1.
            sorted_notes = sorted_notes[2:]

        if 'dissonance' in self.parts_enabled:
            beat['dissonance'] = self.velocity / 64. - 1

        if 'harmony' in self.parts_enabled:
            beat['harmony'] = config._input_harmony(sorted_notes[::-1])
        # don't support both harmony and rhythm setting at same time :(
        elif 'mel_rhythm' in self.parts_enabled:
            if len(sorted_notes) >= 2:
                base = sorted_notes[-1]
                end = sorted_notes[0]
                beat['mel_rhythm'] = tuple(
                    note in sorted_notes
                    for note in range(base + 1, end)
                )
        elif 'acc_rhythm' in self.parts_enabled:
            if len(sorted_notes) == 2:
                beat['acc_rhythm'] = {
                    'a': (False, True, True),
                    't': (False, True, True),
                    'b': (True, -1, -1),
                }
            if len(sorted_notes) == 3:
                beat['acc_rhythm'] = {
                    'a': (False, False, True),
                    't': (False, True, False),
                    'b': (True, False, False),
                }
            if len(sorted_notes) == 4:
                beat['acc_rhythm'] = {
                    'a': (False, True, False, True),
                    't': (False, False, True, False),
                    'b': (True, False, False, False),
                }
            if len(sorted_notes) == 5:
                beat['acc_rhythm'] = {
                    'a': (False, False, True, False),
                    't': (False, True, False, True),
                    'b': (True, False, False, False),
                }

        beat['manual'] = copy.deepcopy(self.parts_enabled)

        self.on_beat_update(beat)


    #def set_beat_chord(self, chord):
    #    self.beat['chord'] = chord
    #    self.on_beat_update(self.beat)

    #def set_beat_key(self, key):
    #    self.beat['key'] = key
    #    self.on_beat_update(self.beat)

    def update_input_notes(self):
        # Use the most recently entered input notes if we have more than we need
        if len(self.input_notes) > self.num_input_note_parts():
            self.input_notes = self.input_notes[-self.num_input_note_parts():]

    def update_beat(self):
        if self.beat_needs_update and len(self.input_notes) >= len(self.parts_enabled):
            self.populate_beat_with_notes(self.input_notes)
            #self.on_beat_update(self.beat)
            self.beat_needs_update = False

    def on_update(self):
        #self.update_input_notes()
        self.update_beat()

