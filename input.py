from kivy.graphics.instructions import InstructionGroup
from common.core import *

class Input(InstructionGroup):
    def __init__(self, on_beat_update_callback=lambda beat : None):
        super(Input, self).__init__()

        self.parts_enabled = {'s' : False, 'a' : False, 't' : False, 'b' : False, 'chord' : False, 'key' : False}
        self.input_notes = []
        self.beat = {}
        self.beat_needs_update = False
        self.on_beat_update = on_beat_update_callback

    def reset(self):
        self.input_notes = []
        self.beat = {}
        self.beat_needs_update = True

    def set_part_enabled(self, part, enabled):
        self.parts_enabled[part] = enabled

    # Number of enabled note parts (i.e. 's', 'a', 't', 'b')
    def num_input_note_parts(self):
        return len([part for part in 'satb' if self.parts_enabled[part]])

    # TODO: Handle input from MIDI keyboard
    def on_key_down(self, keycode, modifiers):
        midi_value = keycode[0] # This will do for now
        midi_value = lookup(keycode[1], 'asdfghjkl', [72, 74, 76, 77, 79, 81, 83, 84, 86])
        self.on_midi_input(midi_value)

    # TODO: Handle input from MIDI keyboard
    def on_key_up(self, keycode):
        pass

    def on_midi_input(self, midi_value):
        if midi_value not in self.input_notes:
            self.input_notes.append(midi_value)
            self.beat_needs_update = True

    def populate_beat_with_notes(self, notes):
        sorted_notes = sorted(notes, reverse=True)

        # Assign notes for parts in descending order
        active_note_parts = [part for part in 'satb' if self.parts_enabled[part]]
        for index, part in enumerate(active_note_parts):
            if index < len(sorted_notes):
                self.beat[part] = sorted_notes[index]

    def set_beat_chord(self, chord):
        self.beat['chord'] = chord
        self.on_beat_update(self.beat)

    def set_beat_key(self, key):
        self.beat['key'] = key
        self.on_beat_update(self.beat)

    def update_input_notes(self):
        # Use the most recently entered input notes if we have more than we need
        if len(self.input_notes) > self.num_input_note_parts():
            self.input_notes = self.input_notes[-self.num_input_note_parts():]

    def update_beat(self):
        if self.beat_needs_update:
            self.populate_beat_with_notes(self.input_notes)
            self.on_beat_update(self.beat)
            self.beat_needs_update = False

    def on_update(self):
        self.update_input_notes()
        self.update_beat()
