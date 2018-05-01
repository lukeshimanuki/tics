from kivy.graphics.instructions import InstructionGroup
from common.core import *

class Input(InstructionGroup):
    def __init__(self, on_beat_update_callback=lambda beat : None):
        super(Input, self).__init__()

        self.parts_enabled = set()
        self.input_notes = set()
        #self.beat = {}
        self.beat_needs_update = False
        self.on_beat_update = on_beat_update_callback

        try:
            # Attempt to set up MIDI input, if rtmidi is installed.
            import rtmidi
            from rtmidi import midiconstants
            self.midi_in = rtmidi.MidiIn(name='TICS')
            available_ports = self.midi_in.get_ports()
            print(available_ports)
            self.midi_in.open_port(1)
            print('Opened MIDI port.')
            self.last_msg = None
            def midi_callback(msgtime, _ = None):
                msg, time = msgtime
                if msg[0] == midiconstants.NOTE_ON and msg[0:2] != self.last_msg:
                    self.on_midi_down(msg[1])
                    self.last_msg = msg[0:2]
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

    # TODO: Handle input from MIDI keyboard
    def on_key_down(self, keycode, modifiers):
        midi_value = lookup(keycode[1], '1234567890', [72, 74, 76, 77, 79, 81, 83, 84, 86, 88])
        if midi_value is not None:
            self.on_midi_down(midi_value)

    # TODO: Handle input from MIDI keyboard
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

        # TODO: somehow allow minor keys?
        if 'key' in self.parts_enabled:
            beat['key'] = sorted_notes[-1] % 12
            sorted_notes = sorted_notes[:-1]

        if 'chord' in self.parts_enabled:
            # sort in increasing order
            sorted_notes = sorted_notes[::-1]
            # only take bottom 2
            if len(sorted_notes) > 2:
                sorted_notes = sorted_notes[:2]
            # take relative to key
            key = 0 # todo fix this
            sorted_notes = [
                (note - key) % 12
                for note in sorted_notes
            ]
            # if single note, assume diatonic chord
            chord_mapping = [
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
            if len(sorted_notes) == 1:
                beat['chord'] = chord_mapping[sorted_notes[0]]
            elif (sorted_notes[1] - sorted_notes[0]) % 12 == 7:
                base_tone = chord_mapping[sorted_notes[0]]
                if base_tone in ['ii', 'IV', 'V', 'vi']:
                    beat['chord'] = 'V/' + base_tone
                else:
                    beat['chord'] = 'I'
            else:
                beat['chord'] = 'I'

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

