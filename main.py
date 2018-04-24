import sys
import random
import numpy as np
import bisect
import copy

from kivy.uix.floatlayout import FloatLayout

from common.core import *
from common.audio import Audio
from common.synth import Synth
from common.clock import SimpleTempoMap, AudioScheduler
from common.gfxutil import AnimGroup

from input import Input
from ui import UI
from autocomplete import autocomplete

class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()

        # the data structure describing a partial or full composition
        # is just a list of dictionaries (each dict is a beat)
        # each beat consists of:
        # - the four lines (SATB), usually but not necessarily single notes
        # - harmony, or chord (in relation to the key)
        # - key
        # this reference should never change
        self.data = [{}, {}, {}, {}, {}]

        # Add an initial chord
        self.data[0] = {'s': 71, 'a': 67, 't': 64, 'b': 60, 'chord': 'I', 'key': 0}

        self.input = Input(self.data)
        layout = FloatLayout(size=Window.size)
        self.add_widget(layout)
        self.ui = UI(self.data, self.input)
        layout.add_widget(self.ui)

        self.audio = Audio(2)
        self.synth = Synth('data/FluidR3_GM.sf2')

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(480)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)
        self.sched.post_at_tick(480 * 4, self.on_beat)

        self.current_beat_index = -1
        self.needs_autocomplete_update = True

    def play_next_beat(self):
        # Stop playing the previous beat
        if self.current_beat_index > 0:
            current_beat = self.data[self.current_beat_index]
            for part in 'satb':
                self.synth.noteoff(0, current_beat[part])

        # Start playing the current beat
        next_beat = self.data[self.current_beat_index + 1]
        for part in 'satb':
            self.synth.noteon(0, next_beat[part], 100)  

    def on_beat(self, tick, _ = None):
        self.play_next_beat()
        self.ui.on_beat(tick)
        self.sched.post_at_tick(tick + 480 * 4, self.on_beat)
        self.data.append({})
        self.current_beat_index += 1
        self.needs_autocomplete_update = True

    def on_key_down(self, keycode, modifiers):
        self.input.on_key_down(keycode, modifiers)
        self.needs_autocomplete_update = True

    def on_key_up(self, keycode):
        self.input.on_key_up(keycode)
        self.needs_autocomplete_update = True

    def on_touch_down(self, touch):
        super(MainWidget, self).on_touch_down(touch)

    def beat_is_filled(self, beat_index):
        for key in ['s', 'a', 't', 'b', 'chord', 'key']:
            if key not in self.data[beat_index]:
                return False
        return True

    def autocomplete_beat(self, beat_index):
        # Pad data with empty beats
        while len(self.data) < beat_index + 2:
            self.data.append({})

        # Don't autocomplete if beat is already filled in
        if self.beat_is_filled(beat_index):
            return

        # Fill in beat based on the beats immediately before & after
        partial_data = copy.deepcopy(self.data[beat_index - 1 :])
        filled_data = autocomplete(partial_data)
        self.data[beat_index] = filled_data[1]

    def on_update(self):
        self.audio.on_update()
        self.ui.on_update()

        # Draw notes on the staff
        for i in range(len(self.ui.staff.notes) / 4, self.current_beat_index + 1):
            beat = self.data[i]
            for (voice, color, stem_direction) in self.ui.voice_info:
                if voice in beat:
                    self.ui.staff.add_note(i, beat[voice], color, stem_direction) 
        self.ui.staff.beat = self.current_beat_index

        if self.needs_autocomplete_update:
            # Autocomplete next beat
            self.autocomplete_beat(self.current_beat_index + 1)
            self.needs_autocomplete_update = False

            # Debugging [REMOVE THIS]
            for beat in self.data:
                print beat

            # TODO: do something to concurrently call the autocomplete algorithm
            #copied_data = copy.deepcopy(self.data)

            # Autocomplete breaks if data is empty, or data[0]['key']/data[0]['chord'] aren't defined.
            #filled_data = autocomplete(copied_data)
            #for beat,filled_beat in zip(self.data, filled_data):
            #    beat.update(filled_beat)

            

        # TODO: remove beats that have already passed


if __name__ == "__main__":
    run(MainWidget)

