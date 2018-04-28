import sys
import random
import numpy as np
import bisect
import copy
import multiprocessing
import Queue

from kivy.uix.floatlayout import FloatLayout

from common.core import *
from common.audio import Audio
from common.synth import Synth
from common.clock import SimpleTempoMap, AudioScheduler
from common.gfxutil import AnimGroup

from input import Input
from ui import UI
from autocomplete import autocomplete

PADDING = 8

class BeatManager:
    def __init__(self, tempo=80, on_beat_callback=lambda : None):

        # Data structure
        # This data structure describes a partial or full composition
        # It is just a list of "beats", where each "beat" is a dictionary of the following form:
        # {
        #   's' : midi-value (0-127) # Soprano note
        #   'a' : midi-value (0-127) # Alto note
        #   't' : midi-value (0-127) # Tenor note
        #   'b' : midi-value (0-127) # Bass note
        #   'key' : key (0-11)       # Current key
        #   'chord' : chord          # Harmony, or chord (in relation to the key)
        # }
        self.data = [{'s': 72, 'a': 67, 't': 64, 'b': 60, 'chord': 'I', 'key': 0}, {}, {}, {}, {}, {}, {}]

        # Add an initial chord

        # Class variables
        self.on_beat_callback = on_beat_callback
        self.current_beat_index = 0
        self.needs_autocomplete_update = True
        self.current_playing_notes = set()
        self.autocomplete_data = multiprocessing.Queue()

        # Initialize audio
        self.audio = Audio(2)
        self.synth = Synth('data/FluidR3_GM.sf2')
        self.synth.program(0, 0, 0)

        # Create TempoMap & AudioScheduler
        self.tempo_map  = SimpleTempoMap(tempo)
        self.sched = AudioScheduler(self.tempo_map)

        # Connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)
        self.sched.post_at_tick(480, self.on_beat)

    def beat_is_filled(self, beat_index):
        for key in ['s', 'a', 't', 'b', 'chord', 'key']:
            if key not in self.data[beat_index]:
                return False
        return True

    def on_beat(self, tick, _ = None):
        self.play_next_beat()
        self.sched.post_at_tick(tick + 480, self.on_beat)
        self.on_beat_callback()
        self.current_beat_index += 1
        self.autocomplete_beat(self.current_beat_index)

    def play_next_beat(self):
        # Stop playing any previous notes
        for channel, note in self.current_playing_notes:
            self.synth.noteoff(channel, note)
        self.current_playing_notes.clear()

        # Start playing notes in the next beat
        next_beat = self.data[self.current_beat_index]
        print next_beat # [DEBUGGING]
        for part in 'satb':
            if part in next_beat:
                self.synth.noteon(0, next_beat[part], 100)
                self.current_playing_notes.add((0, next_beat[part]))

    def autocomplete_thread(self, beat_index, data):
        autocomplete_data = autocomplete(data)[1]
        self.autocomplete_data.put((beat_index, autocomplete_data, np.random.get_state()))

    def autocomplete_beat(self, beat_index):
        # Pad data with empty beats
        while len(self.data) < beat_index + PADDING:
            self.data.append({})

        # Don't autocomplete if beat is already filled in
        if self.beat_is_filled(beat_index):
            return

        # Fill in beat based on the beats immediately before & after
        process = multiprocessing.Process(target=self.autocomplete_thread, args=(beat_index, copy.deepcopy(self.data[beat_index - 1 :])))
        process.start()

    def on_update(self):
        self.audio.on_update()

        # Fill in any autocompleted beats
        try:
            beat, autocomplete_data, random_state = self.autocomplete_data.get(False)
            np.random.set_state(random_state)
            self.data[beat].update(autocomplete_data)
        except Queue.Empty:
            pass


class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()

        self.beat_manager = BeatManager(tempo=60, on_beat_callback=self.on_beat)
        self.input = Input(self.update_beat_from_input)

        # Draw the UI
        self.ui = UI(self.beat_manager.data, self.input)
        layout = FloatLayout(size=Window.size)
        layout.add_widget(self.ui)
        self.add_widget(layout)

    def draw_beats_on_staff(self):
        # Draw notes on the staff
        for i in range(len(self.ui.staff.notes) / 4, self.beat_manager.current_beat_index + 1):
            beat = self.beat_manager.data[i]
            for (voice, color, stem_direction) in self.ui.voice_info:
                if voice in beat:
                    self.ui.staff.add_note(i, beat[voice], color, stem_direction) 
        if self.ui.staff.beat != self.beat_manager.current_beat_index:
            self.ui.staff.beat = self.beat_manager.current_beat_index
            self.ui.staff.draw()

    def on_beat(self):
        self.input.reset()
        self.draw_beats_on_staff()
        
    def update_beat_from_input(self, beat):
        selected_beat_index = self.beat_manager.current_beat_index + 1 + self.ui.selected_beat # TODO: make this whichever beat index is actually selected by UI 
        self.beat_manager.data[selected_beat_index].update(beat)
        print("{}: {}".format(selected_beat_index, beat))
        for (voice, color, stem_direction) in self.ui.voice_info:
            if voice in beat:
                self.ui.staff.add_note(selected_beat_index, beat[voice], color, stem_direction)

    def on_key_down(self, keycode, modifiers):
        self.input.on_key_down(keycode, modifiers)

        if keycode[1] == 'left':
            self.ui.selected_beat = max(self.ui.selected_beat - 1, 0)
        if keycode[1] == 'right':
            self.ui.selected_beat = min(self.ui.selected_beat + 1, PADDING - 2)

    def on_key_up(self, keycode):
        self.input.on_key_up(keycode)

    def on_touch_down(self, touch):
        super(MainWidget, self).on_touch_down(touch)

    def on_update(self):
        self.beat_manager.on_update()
        self.input.on_update()
        self.ui.on_update()
        # self.draw_beats_on_staff()

if __name__ == "__main__":
    run(MainWidget)

