import sys
import random
import numpy as np
import bisect
import copy

from common.core import *
from common.gfxutil import AnimGroup

from input import Input
from output import Output
from autocomplete import autocomplete

class MainWidget(BaseWidget) :
	def __init__(self):
		super(MainWidget, self).__init__()

		self.objects = AnimGroup()
		self.canvas.add(self.objects)

		# the data structure describing a partial or full composition
		# is just a list of dictionaries (each dict is a beat)
		# each beat consists of:
		# - the four lines (SATB), usually but not necessarily single notes
		# - harmony, or chord (in relation to the key)
		# - key
		# this reference should never change
		self.data = []

		# TODO: transform these from [0,1]^2 space to [0,Window.width]x[0,Window.height]
		self.input = Input(self.data)
		self.output = Output(self.data)

		self.objects.add(self.input)
		self.objects.add(self.output)

	def on_key_down(self, keycode, modifiers):
		self.input.on_key_down(keycode, modifiers)

	def on_key_up(self, keycode):
		self.input.on_key_up(keycode)

	def on_touch_move(self, touch):
		self.input.on_touch_move(touch)

	def on_touch_down(self, touch):
		self.input.on_touch_down(touch)

	def on_touch_up(self, touch):
		self.input.on_touch_up(touch)

	def on_update(self) :
		# TODO: update transformation if window resized

		self.objects.on_update()

		# TODO: do something to concurrently call the autocomplete algorithm
		copied_data = copy.deepcopy(self.data)
		filled_data = autocomplete(copied_data)
		for beat,filled_beat in zip(self.data, filled_data):
			beat.update(filled_beat)

		# TODO: remove beats that have already passed


if __name__ == "__main__":
	run(MainWidget)

