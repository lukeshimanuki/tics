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
        self.data = []

        self.input = Input(self.data)
        layout = FloatLayout(size=Window.size)
        self.add_widget(layout)
        self.ui = UI(self.data, self.input)
        layout.add_widget(self.ui)

        self.audio = Audio(2)
        self.synth = Synth('data/FluidR3_GM.sf2')

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(120)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)
        self.sched.post_at_tick(480 * 4, self.on_beat)

    def on_beat(self, tick, _ = None):
        self.ui.on_beat(tick)
        self.sched.post_at_tick(tick + 480 * 4, self.on_beat)

    def on_key_down(self, keycode, modifiers):
        self.input.on_key_down(keycode, modifiers)

    def on_key_up(self, keycode):
        self.input.on_key_up(keycode)

    def on_touch_down(self, touch):
        super(MainWidget, self).on_touch_down(touch)

    def on_update(self):
        self.audio.on_update()
        self.ui.on_update()

        # TODO: do something to concurrently call the autocomplete algorithm
        copied_data = copy.deepcopy(self.data)
        # Autocomplete breaks if data is empty, or data[0]['key']/data[0]['chord'] aren't defined.
        filled_data = copied_data # autocomplete(copied_data)
        for beat,filled_beat in zip(self.data, filled_data):
            beat.update(filled_beat)

        # TODO: remove beats that have already passed


if __name__ == "__main__":
    run(MainWidget)

