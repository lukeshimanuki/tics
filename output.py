from kivy.graphics.instructions import InstructionGroup

from common.audio import Audio
from common.synth import Synth
from common.clock import SimpleTempoMap, AudioScheduler

class Output(InstructionGroup):
	def __init__(self, data):
		super(Output, self).__init__()

		self.data = data

		self.audio = Audio(2)
		self.synth = Synth('data/FluidR3_GM.sf2')

		# create TempoMap, AudioScheduler
		self.tempo_map	= SimpleTempoMap(120)
		self.sched = AudioScheduler(self.tempo_map)

		# connect scheduler into audio system
		self.audio.set_generator(self.sched)
		self.sched.set_generator(self.synth)

	def on_update(self, dt):
		self.audio.on_update()

