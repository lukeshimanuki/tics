import sys
import random
import numpy as np
import bisect
import copy
import multiprocessing
import time
import Queue

from kivy.uix.floatlayout import FloatLayout

from common.core import *
from common.audio import Audio
from common.synth import Synth
from common.clock import SimpleTempoMap, AudioScheduler, Scheduler, Clock
from common.gfxutil import AnimGroup

from input import Input, input_config
from ui import UI
from autocomplete import autocomplete, autocomplete_config

if len(sys.argv) >= 2:
    autocomplete_config(sys.argv[1])
    input_config(sys.argv[1])

# Instrument groups
PIANO = {'s': 0, 'a': 0, 't': 0, 'b': 0}
STRING_QUARTET = {'s': 41, 'a': 41, 't': 42, 'b': 43} # 2 violins, viola, cello
WOODWIND_QUARTET = {'s': 74, 'a': 69, 't': 72, 'b': 72} # flute, oboe, clarinet, bassoon
SAX_QUARTET = {'s': 65, 'a': 66, 't': 67, 'b': 68} # soprano, alto, tenor, bari

class BeatManager:
    def __init__(self, tempo=80, instruments=STRING_QUARTET, on_beat_callback=lambda : None):

        # Data structure
        # This data structure describes a partial or full composition
        # It is just a list of "beats", where each "beat" is a dictionary of the following form:
        # {
        #   's' : tuple              # Soprano note, (None) is rest, (-1) is hold previous
        #   'a' : tuple              # Alto note
        #   't' : tuple              # Tenor note
        #   'b' : tuple              # Bass note
        #   'harmony' : string         # Harmony (in relation to the key), of the form "chord|key" (eg "I|C")
        #   'spacing' : float (-1 - 1)  # how much spacing is preferred
        #   'dissonance': float(-1 - 1) # how much dissonance is preferred
        #   'manual' : set           # which keys were set manually by the user
        #   'mel_rhythm' : tuple     # template for s line, but with boolean values
        #   'acc_rhythm' : dict         # template for atb lines, but with booleans (-1 is hold previous)
        # }

        # Set initial data
        self.data = [{'s': (72,), 'a': (67,), 't': (64,), 'b': (60,), 'harmony': 'I|C'}, {}, {}, {}, {}, {}, {}]

        # Class constants
        self.PADDING = 5

        # Class variables
        self.on_beat_callback = on_beat_callback
        self.current_beat_index = 0
        self.needs_autocomplete_update = True
        self.current_playing_notes = set()
        self.autocomplete_data = multiprocessing.Queue()

        self.tempo_map  = SimpleTempoMap(tempo)
        self.sched = Scheduler(Clock(), self.tempo_map)
        self.sched.post_at_tick(480, self.on_beat)

        self.synth = Synth('data/FluidR3_GM.sf2')
        self.synth.program(0, 0, 0)
        self.set_instruments(instruments)

        self.note_queue = multiprocessing.Queue()
        audio_process = multiprocessing.Process(target=self.audio_process, args=(self.note_queue,))
        audio_process.start()

    def audio_process(self, note_queue):
        # Initialize audio
        audio = Audio(2)

        sched = AudioScheduler(self.tempo_map)

        # Connect scheduler into audio system
        audio.set_generator(sched)
        sched.set_generator(self.synth)

        while True:
            try:
                channel, note, volume, start, length = note_queue.get(False)
                tick = sched.get_tick()
                channel = 0 # comment out if not luke
                sched.post_at_tick(tick + start * 480, self._noteon, (channel, note, volume))
                sched.post_at_tick(tick + length * 480, self._noteoff, (channel, note))

            except Queue.Empty:
                audio.on_update()
                time.sleep(.01)

    def _noteon(self, tick, (channel, note, volume)):
        self.synth.noteon(channel, note, volume)

    def _noteoff(self, tick, (channel, note)):
        self.synth.noteoff(channel, note)

    def set_instruments(self, instruments):
        self.instruments = instruments
        for channel, part in enumerate('satb'):
            preset = self.instruments[part]
            self.synth.program(channel, 0, preset)

    def beat_is_filled(self, beat_index):
        for key in ['s', 'a', 't', 'b', 'harmony']:
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
        ## Stop playing any previous notes
        #for channel, note in self.current_playing_notes:
        #    self.synth.noteoff(channel, note)
        #self.current_playing_notes.clear()

        # Start playing notes in the next beat
        next_beat = self.data[self.current_beat_index]
        print next_beat # [DEBUGGING]
        for channel, part in enumerate('satb'):
            if part in next_beat:
                num = len(next_beat[part])
                notes = []
                starts = []
                lengths = []
                for idx, note in enumerate(next_beat[part]):
                    if note == -1:
                        lengths[-1] += 1
                    elif note == None:
                        pass
                    else:
                        notes.append(note)
                        starts.append(idx)
                        lengths.append(1)
                volume = 100 if 'manual' in next_beat and part in next_beat['manual'] else 50
                for idx, note in enumerate(notes):
                    self.note_queue.put((channel, note, volume, float(starts[idx]) / num, float(lengths[idx]) / num))
                #self.synth.noteon(channel, next_beat[part][0], 100)
                #self.current_playing_notes.add((channel, next_beat[part][0]))

    def autocomplete_thread(self, beat_index, data):
        autocomplete_data = autocomplete(data)[1]
        self.autocomplete_data.put((beat_index, autocomplete_data, np.random.get_state()))

    def autocomplete_beat(self, beat_index):
        # Pad data with empty beats
        while len(self.data) < beat_index + self.PADDING:
            self.data.append({})

        # Don't autocomplete if beat is already filled in
        if self.beat_is_filled(beat_index):
            return

        # Fill in beat based on the beats immediately before & after
        process = multiprocessing.Process(target=self.autocomplete_thread, args=(beat_index, copy.deepcopy(self.data[beat_index - 1 :])))
        process.start()

    def on_update(self):
        #self.audio.on_update()
        self.sched.on_update()

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
        self.ui = UI(self.beat_manager.data, self.input, spacing=30)
        layout = FloatLayout(size=Window.size)
        layout.add_widget(self.ui)
        self.add_widget(layout)

    def draw_beats_on_staff(self):
        # Draw notes on the staff
        for i in range(len(self.ui.staff.notes) / 4, self.beat_manager.current_beat_index + 1):
            beat = self.beat_manager.data[i]
            for (voice, color, stem_direction) in self.ui.voice_info:
                if voice in beat:
                    self.ui.staff.add_note(i, beat[voice][0], color, stem_direction) 
        if self.ui.staff.beat != self.beat_manager.current_beat_index:
            self.ui.staff.beat = self.beat_manager.current_beat_index
            self.ui.staff.draw()

    def on_beat(self):
        self.input.reset()
        self.draw_beats_on_staff()

    def update_beat_from_input(self, beat):
        selected_beat_index = self.beat_manager.current_beat_index + 1 + self.ui.selected_beat # TODO: make this whichever beat index is actually selected by UI 
        self.beat_manager.data[selected_beat_index].update(beat)
        print("{}: {}".format(selected_beat_index, beat)) # [DEBUGGING]
        for (voice, color, stem_direction) in self.ui.voice_info:
            if voice in beat:
                self.ui.staff.add_note(selected_beat_index, beat[voice][0], color, stem_direction)

    def on_key_down(self, keycode, modifiers):
        self.ui.on_key_down(keycode, modifiers)
        self.input.on_key_down(keycode, modifiers)

        if keycode[1] == 'left':
            self.ui.selected_beat = max(self.ui.selected_beat - 1, 0)
        if keycode[1] == 'right':
            self.ui.selected_beat = min(self.ui.selected_beat + 1, self.beat_manager.PADDING - 2)

    def on_key_up(self, keycode):
        self.input.on_key_up(keycode)

    def on_touch_down(self, touch):
        super(MainWidget, self).on_touch_down(touch)

    def on_update(self):
        self.beat_manager.on_update()
        self.input.on_update()
        self.ui.on_update()

if __name__ == "__main__":
    run(MainWidget)

