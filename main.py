import sys
import random
import numpy as np
import bisect
import copy
import multiprocessing
import time
import Queue
import cPickle as pickle
from midiutil import MidiFile

from kivy.uix.floatlayout import FloatLayout

from common.core import *
from common.audio import Audio
from common.synth import Synth
from common.clock import SimpleTempoMap, AudioScheduler, Scheduler, Clock
from common.gfxutil import AnimGroup

from input import Input, input_config
from ui import UI
from autocomplete import autocomplete, autocomplete_config

config = __import__('jazz')

if len(sys.argv) >= 2:
    autocomplete_config(sys.argv[1])
    input_config(sys.argv[1])
    config = __import__(sys.argv[1])

QUIT = multiprocessing.Queue()

class BeatManager:
    def __init__(self, tempo=80, instruments={'s': 0, 'a': 0, 't': 0, 'b': 0}, on_beat_callback=lambda : None):

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
        self.PADDING = 17
        self.MAX_AUTOCOMPLETE = 5

        # Class variables
        self.on_beat_callback = on_beat_callback
        self.current_beat_index = 0
        self.needs_autocomplete_update = True
        self.current_playing_notes = set()
        self.autocomplete_data = multiprocessing.Queue()

        self.clock = Clock()
        self.last_tick = 0
        self.tempo = tempo
        self.tempo_map = SimpleTempoMap(tempo)
        self.sched = Scheduler(self.clock, self.tempo_map)
        self.sched.post_at_tick(480, self.on_beat)
        self.paused = False
        self.improv = False

        self.synth = Synth('data/FluidR3_GM.sf2')
        self.synth.program(0, 0, 0)
        self.set_instruments(instruments)

        self.note_queue = multiprocessing.Queue()
        self.note_on = multiprocessing.Queue()
        self.note_off = multiprocessing.Queue()
        self.tempo_queue = multiprocessing.Queue()
        print sys.platform
        if sys.platform == 'darwin':
        	# Use threads instead of processes (PyAudio on Mac doesn't support multiprocessing w/ forking)
        	from threading import Thread
        	audio_process = Thread(target=self.audio_process, args=(self.note_queue,))
        else:
        	audio_process = multiprocessing.Process(target=self.audio_process, args=(self.note_queue,))
        audio_process.start()
        
    def set_tempo(self, tempo):
        tempo = np.clip(tempo, 0, 200)
        self.tempo = tempo
        self.tempo_map.set_tempo(tempo, self.clock.get_time())
        self.tempo_queue.put(tempo)

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.tempo_map.set_tempo(0, self.clock.get_time())
            self.tempo_queue.put(1e-9)
        else:
            self.set_tempo(self.tempo)
            self.tempo_queue.put(self.tempo)

    def toggle_improv(self):
        self.improv = not self.improv

    def audio_process(self, note_queue):
        # Initialize audio
        audio = Audio(2)
        sched = Scheduler(Clock(), self.tempo_map)

        # Connect scheduler into audio system
        audio.set_generator(self.synth)

        active_notes = set()

        while True:
            try:
                channel, note, volume, start, length = note_queue.get(False)
                tick = sched.get_tick()
                sched.post_at_tick(tick + start * 480, self._noteon, (channel, note, volume))
                sched.post_at_tick(tick + length * 480, self._noteoff, (channel, note))
            except Queue.Empty:
                pass

            try:
                channel, note = self.note_off.get(False)
                self.synth.noteoff(channel, note)
                if (channel, note) in active_notes:
                    active_notes.remove((channel, note))
            except Queue.Empty:
                pass

            try:
                channel, note, volume = self.note_on.get(False)
                self.synth.noteon(channel, note, volume)
                active_notes.add((channel, note))
            except Queue.Empty:
                pass

            try:
                tempo = self.tempo_queue.get(False)
                if tempo < 1e-3:
                    for channel, note in active_notes:
                        self.synth.noteoff(channel, note)
                    active_notes = set()
                self.tempo_map.set_tempo(tempo, self.clock.get_time())
            except Queue.Empty:
                pass

            try:
                QUIT.get(False)
                QUIT.put(None)
                return
            except Queue.Empty:
                audio.on_update()
                sched.on_update()
                time.sleep(.01)

    def _noteon(self, tick, (channel, note, volume)):
        self.note_on.put((channel, note, volume))

    def _noteoff(self, tick, (channel, note), sleep=0):
        time.sleep(sleep)
        self.note_off.put((channel, note))

    def set_instruments(self, instruments):
        self.instruments = instruments
        for channel, part in enumerate('satb'):
            preset = self.instruments[part]
            self.synth.program(channel, 0, preset)

    def current_tempo(self):
        return self.tempo_map.bpm

    def current_key(self):
        return self.data[self.current_beat_index]['harmony'].split('|')[1]

    def beat_is_filled(self, beat_index):
        for key in ['s', 'a', 't', 'b', 'harmony']:
            if key not in self.data[beat_index]:
                return False
        return True

    def on_beat(self, tick, _ = None):
        # fill beat if not already autocompleted
        if not self.beat_is_filled(self.current_beat_index):
            self.data[self.current_beat_index].update(self.data[self.current_beat_index - 1])

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
                if self.improv:
                    volume = 0 if 'manual' in next_beat and part in next_beat['manual'] else 80 
                else:
                    volume = 100 if 'manual' in next_beat and part in next_beat['manual'] else 80
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
        process = multiprocessing.Process(target=self.autocomplete_thread, args=(beat_index, copy.deepcopy(self.data[beat_index - 1 :beat_index - 1 + self.MAX_AUTOCOMPLETE])))
        process.start()

    def on_update(self):
        #self.audio.on_update()
        self.sched.on_update()
        tick = self.tempo_map.time_to_tick(self.clock.get_time())
        self.tick_delta = tick - self.last_tick
        self.last_tick = tick

        # Fill in any autocompleted beats
        try:
            beat, autocomplete_data, random_state = self.autocomplete_data.get(False)
            np.random.set_state(random_state)
            if not self.beat_is_filled(beat):
                self.data[beat].update(autocomplete_data)
        except Queue.Empty:
            pass


class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()

        self.beat_manager = BeatManager(tempo=60, on_beat_callback=self.on_beat, instruments=config._instruments)
        self.input = Input(self.update_beat_from_input)

        # Draw the UI
        self.ui = UI(self.input, spacing=30)
        layout = FloatLayout(size=Window.size)
        layout.add_widget(self.ui)
        self.add_widget(layout)

        self.record_index = None

    def draw_beats_on_staff(self):
        # Draw notes on the staff
        for i in range(self.ui.staff.beat - self.ui.staff.display_history, len(self.beat_manager.data)):
            beat = self.beat_manager.data[i]
            self.ui.staff.add_beat(i, beat)

    def on_beat(self):
        self.input.reset()
        self.draw_beats_on_staff()
        self.ui.on_beat(self.beat_manager.current_beat_index)

        FLAT_KEYS = ['F', 'Bb', 'Eb', 'Ab', 'd', 'g', 'c', 'f']
        if self.beat_manager.current_key() in FLAT_KEYS:
            self.ui.set_accidental_type(-1)
        else:
            self.ui.set_accidental_type(1)

    def update_beat_from_input(self, beat):
        if self.beat_manager.paused or self.beat_manager.improv:
            for channel, part in enumerate('satb'):
                if part in beat and 'manual' in beat and part in beat['manual']:
                    note = beat[part][0]
                    self.beat_manager.note_on.put((channel, note, 100))
                    process = multiprocessing.Process(target=self.beat_manager._noteoff, args=(0, (channel, note), .5))
                    process.start()

        selected_beat_index = self.beat_manager.current_beat_index + 1 + self.ui.selected_beat
        if 'manual' in beat and 'manual' in self.beat_manager.data[selected_beat_index]:
            beat['manual'].update(self.beat_manager.data[selected_beat_index]['manual'])
        self.beat_manager.data[selected_beat_index].update(beat)
        print("{}: {}".format(selected_beat_index, self.beat_manager.data[selected_beat_index])) # [DEBUGGING]
        self.ui.staff.add_beat(selected_beat_index, self.beat_manager.data[selected_beat_index])

    def on_key_down(self, keycode, modifiers):
        self.ui.on_key_down(keycode, modifiers)
        self.input.on_key_down(keycode, modifiers)

        if keycode[1] == 'up':
            tempo = self.beat_manager.current_tempo()
            self.beat_manager.set_tempo(tempo + 10)
            self.ui.tempo.text = 'Tempo : %d\n' % self.beat_manager.tempo
        if keycode[1] == 'down':
            tempo = self.beat_manager.current_tempo()
            self.beat_manager.set_tempo(tempo - 10)
            self.ui.tempo.text = 'Tempo : %d\n' % self.beat_manager.tempo
        if keycode[1] == 'left':
            self.ui.selected_beat = max(self.ui.selected_beat - 1, 0)
        if keycode[1] == 'right':
            self.ui.selected_beat = min(self.ui.selected_beat + 1, self.beat_manager.PADDING - 2)
        if keycode[1] == 'p':
            self.beat_manager.toggle_pause()
        if keycode[1] == 'i':
            self.beat_manager.toggle_improv()
        if keycode[1] == 'r':
            if self.record_index is None:
                self.record_index = self.beat_manager.current_beat_index + self.ui.selected_beat + 1
            else:
                pickle.dump(self.beat_manager.data[self.record_index:self.beat_manager.current_beat_index + self.ui.selected_beat + 2], open('recording.pickle', 'w'))
                self.record_index = None
        if keycode[1] == 'l':
            data = pickle.load(open('recording.pickle', 'r'))
            self.beat_manager.data += [{} for i in range(
                self.beat_manager.current_beat_index + self.ui.selected_beat + 1 + len(data) - len(self.beat_manager.data)
            )]
            for i, (existing, recorded) in enumerate(zip(self.beat_manager.data[self.beat_manager.current_beat_index + self.ui.selected_beat + 1:], data)):
                if 'manual' not in existing:
                    existing['manual'] = set()
                if 'manual' not in recorded:
                    recorded['manual'] = set()
                manual = {
                    key: recorded[key]
                    for key in recorded
                }
                existing.update(manual)
                existing['manual'].update(recorded['manual'])
                self.ui.staff.add_beat(self.beat_manager.current_beat_index + self.ui.selected_beat + 1 + i, existing)

        if keycode[1] == 'e':
            data = pickle.load(open('recording.pickle', 'r'))
            self.beat_manager.data += [{} for i in range(
                self.beat_manager.current_beat_index + self.ui.selected_beat + 1 + len(data) - len(self.beat_manager.data)
            )]
            for i, (existing, recorded) in enumerate(zip(self.beat_manager.data[self.beat_manager.current_beat_index + self.ui.selected_beat + 1:], data)):
                if 'manual' not in existing:
                    existing['manual'] = set()
                if 'manual' not in recorded:
                    recorded['manual'] = set()
                manual = {
                    key: recorded[key]
                    for key in recorded['manual']
                }
                existing.update(manual)
                existing['manual'].update(recorded['manual'])
                self.ui.staff.add_beat(self.beat_manager.current_beat_index + self.ui.selected_beat + 1 + i, existing)

        if keycode[1] == 'y':
            midi_file = MidiFile.MIDIFile(4)
            midi_file.addTrackName(0,0,"Soprano")
            midi_file.addTrackName(1,0,"Alto")
            midi_file.addTrackName(2,0,"Tenor")
            midi_file.addTrackName(3,0,"Bass")
            tempo = 120
            midi_file.addTempo(0,0,tempo)
            midi_file.addTempo(1,0,tempo)
            midi_file.addTempo(2,0,tempo)
            midi_file.addTempo(3,0,tempo)

            data = pickle.load(open('recording.pickle', 'r'))
            for beat_idx, beat in enumerate(data):
                for track, part in enumerate('satb'):
                    if part in beat:
                        num = len(beat[part])
                        notes = []
                        starts = []
                        lengths = []
                        for idx, note in enumerate(beat[part]):
                            if note == -1:
                                lengths[-1] += 1
                            elif note == None:
                                pass
                            else:
                                notes.append(note)
                                starts.append(idx)
                                lengths.append(1)
                        for idx, note in enumerate(notes):
                            midi_file.addNote(track, 0, note, beat_idx + float(starts[idx]) / num, float(lengths[idx]) / num, 127)
            diskfile = open("recording.mid", 'wb')
            midi_file.writeFile(diskfile)
            diskfile.close()

    def on_key_up(self, keycode):
        self.input.on_key_up(keycode)

    def on_touch_down(self, touch):
        super(MainWidget, self).on_touch_down(touch)

    def on_update(self):
        self.beat_manager.on_update()
        self.input.on_update()
        self.ui.on_update(self.beat_manager.tick_delta)

if __name__ == "__main__":
    run(MainWidget)
    QUIT.put(None)

