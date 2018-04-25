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
        self.data = []

        # Add an initial chord
        self.data.append({'s': 72, 'a': 67, 't': 64, 'b': 60, 'chord': 'I', 'key': 0})

        self.input = Input(self.on_beat_update_from_input)
        layout = FloatLayout(size=Window.size)
        self.add_widget(layout)
        self.ui = UI(self.data, self.input)
        layout.add_widget(self.ui)

        self.audio = Audio(2)
        self.synth = Synth('data/FluidR3_GM.sf2')
        self.synth.program(0, 0, 0)

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(80)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)
        self.sched.post_at_tick(480, self.on_beat)

        self.current_beat_index = 0
        self.needs_autocomplete_update = True

        self.current_played_notes = []

        self.autocomplete_data = multiprocessing.Queue()

    def on_beat_update_from_input(self, beat):
        pass
        # print beat
        # TODO: get whatever beat index is selected by UI 
        #       and set that beat to the given one

    def play_next_beat(self):
        # Stop playing the previous beat
        #if self.current_beat_index > 0:
        #    current_beat = self.data[self.current_beat_index]
        #    for part in 'satb':
        #        self.synth.noteoff(0, current_beat[part])

        for channel, note in self.current_played_notes:
            self.synth.noteoff(channel, note)
        self.current_played_notes = []

        # Start playing the current beat
        next_beat = self.data[self.current_beat_index]
        print(next_beat)
        for part in 'satb':
            self.synth.noteon(0, next_beat[part], 100)  
            self.current_played_notes.append((0, next_beat[part]))

    def on_beat(self, tick, _ = None):
        self.play_next_beat()
        #self.ui.on_beat(tick)
        self.sched.post_at_tick(tick + 480, self.on_beat)
        #self.data.append({})
        self.current_beat_index += 1
        self.autocomplete_beat(self.current_beat_index)
        #self.needs_autocomplete_update = True
        pass

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

    def autocomplete_thread(self, beat, data):
        autocomplete_data = autocomplete(data)[1]
        self.autocomplete_data.put((beat, autocomplete_data, np.random.get_state()))

    def autocomplete_beat(self, beat_index):
        # Pad data with empty beats
        while len(self.data) < beat_index + 4:
            self.data.append({})

        # Don't autocomplete if beat is already filled in
        if self.beat_is_filled(beat_index):
            return

        # Fill in beat based on the beats immediately before & after
        process = multiprocessing.Process(target=self.autocomplete_thread, args=(beat_index, copy.deepcopy(self.data[beat_index - 1 :])))
        process.start()

    def on_update(self):
        self.audio.on_update()
        self.input.on_update()
        self.ui.on_update()

        # Draw notes on the staff
        for i in range(len(self.ui.staff.notes) / 4, self.current_beat_index + 1):
            beat = self.data[i]
            for (voice, color, stem_direction) in self.ui.voice_info:
                if voice in beat:
                    self.ui.staff.add_note(i, beat[voice], color, stem_direction) 
        if self.ui.staff.beat != self.current_beat_index:
            self.ui.staff.beat = self.current_beat_index
            self.ui.staff.draw()

        #if self.needs_autocomplete_update:
        #    # Autocomplete next beat
        #    self.autocomplete_beat(self.current_beat_index + 1)
        #    self.needs_autocomplete_update = False

        #    # Debugging [REMOVE THIS]
        #    for beat in self.data:
        #        #print beat
        #        pass

        try:
            beat, autocomplete_data, random_state = self.autocomplete_data.get(False)
            np.random.set_state(random_state)
            self.data[beat].update(autocomplete_data)
        except Queue.Empty:
            pass

            # TODO: do something to concurrently call the autocomplete algorithm
            #copied_data = copy.deepcopy(self.data)

            # Autocomplete breaks if data is empty, or data[0]['key']/data[0]['chord'] aren't defined.
            #filled_data = autocomplete(copied_data)
            #for beat,filled_beat in zip(self.data, filled_data):
            #    beat.update(filled_beat)

            

        # TODO: remove beats that have already passed


if __name__ == "__main__":
    run(MainWidget)

