from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Mesh, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.core.image import Image

from common.core import *
from common.audio import Audio
from common.synth import Synth
from common.clock import SimpleTempoMap, AudioScheduler
from common.gfxutil import KFAnim, AnimGroup, CEllipse, CRectangle

# TODO: Barlines, stems, standard accidentals, bass clef. Move more stuff into
# Staff (i.e. vertical and horizontal positioning, probably insantiation of
# VisualNotes).

def pitch_to_staff(pitch, accidental_type=1):
    # Convert a pitch to a height in treble cleff. E4 is 0, as it corresponds
    # to the lowest non-ledger line in the staff. Also returns an accidental: 0
    # for natural, 1 for sharp, -1 for flat. Decides whether to use sharps or
    # flats based on accidental_type.
    octave, offset = divmod(pitch, 12)
    naturals = [0, 2, 4, 5, 7, 9, 11]
    if offset in naturals: # Return a natural.
        return (octave * 7 + naturals.index(offset) - 37, 0)
    else: # Return a sharp/flat.
        return (octave * 7 + naturals.index(offset-accidental_type) - 37, accidental_type)

class Staff(AnimGroup):
    def __init__(self, pos, size, accidental_type):
        super(Staff, self).__init__()
        self.pos = pos
        self.spacing = size[1] / 10
        self.size = size
        self.accidental_type = accidental_type
        for i in range(5):
            height = pos[1] + i * size[1] / 5
            self.add(Line(points=(pos[0], height, pos[0] + size[0], height)))
        self.add(CRectangle(cpos=(pos[0] + size[0] / 10, pos[1] + self.spacing * 3.5), size=(self.spacing * 5, self.spacing * 12), texture=Image('data/treble.png').texture))
        self.add(PushMatrix())
        self.translation = Translate(self.pos[0] + self.size[0] * 0.25, self.pos[1])
        self.add(self.translation)
        self.moving_objects = AnimGroup()
        self.add(self.moving_objects)
        self.add(PopMatrix())

    def add_note(self, note):
        self.moving_objects.add(note)

    def on_update(self, dt):
        super(Staff, self).on_update(dt)
        #self.translation.x -= dt * 100


# Alternate animation class that loops rather than becoming inactive.
# For the loop to be smooth, the last frame should be the same as the first.
class LoopAnim(KFAnim):
    def eval(self, t):
        return super(LoopAnim, self).eval(t % self.time[-1])

    def is_active(self, t) :
        return True


class Notehead(InstructionGroup):
    def __init__(self, pos, r, pitch):
        super(Notehead, self).__init__()
        self.circle = CEllipse(cpos = pos, size = (2*r, 2*r), segments = 40)
        self.add(self.circle)

    def on_update(self, dt):
        return True


class VisualNote(InstructionGroup):
    def __init__(self, staff, pos, pitch, duration, color, stem_direction):
        super(VisualNote, self).__init__()

        self.staff = staff

        self.add(PushMatrix())

        # Perform translation.
        line, accidental = pitch_to_staff(pitch, staff.accidental_type)
        self.translation = Translate(*pos)
        self.add(self.translation)

        # Add ledger lines, if necessary.
        self.add(Color(0, 0, 0))
        lines = []
        if line < 0:
            lines = range(line, 0)
        else:
            lines = range(10, line + 1)
        for l in lines:
            if l % 2 == 0:
                height = l * staff.spacing
                self.add(Line(points=(-25, height, 25, height)))

        self.color = Color(*color)
        self.add(self.color)
        # The value (brightness) of the note has its own sort of attack and decay.
        # After the note has finished, it remains on the staff, but is darkened.
        self.color_anim = KFAnim((0, 0.5), (0.25 * duration, 1.0), (0.5 * duration, 0.6), (1.0 * duration, 0.3))

        # Draw the note.
        height = line * staff.spacing
        self.notehead = Notehead((0, height), 10, pitch)
        self.add(self.notehead)

        if accidental > 0:
            # Draw a tiny up arrow to indicate a sharp.
            self.add(Line(points=(-20, height-10, -20, height+10), width=1.5))
            self.add(Line(points=(-25, height+5, -20, height+10), width=1.5))
            self.add(Line(points=(-15, height+5, -20, height+10), width=1.5))
        elif accidental < 0:
            # Draw a tiny down arrow to indicate a flat.
            self.add(Line(points=(-20, height-10, -20, height+10), width=1.5))
            self.add(Line(points=(-25, height-5, -20, height-10), width=1.5))
            self.add(Line(points=(-15, height-5, -20, height-10), width=1.5))

        self.add(PopMatrix())

        self.time = 0
        self.on_update(0)

    def on_update(self, dt):
        self.notehead.on_update(dt)
        self.time += dt
        self.color.v = self.color_anim.eval(self.time)

class Output(AnimGroup):

    # Associate voices with colors and stem directions.
    voice_info = [('s', (1, 0, 0), 'up'),
                  ('a', (1, 1, 0), 'down'),
                  ('t', (0, 1, 0), 'up'),
                  ('b', (0, 0, 1), 'down')]

    def __init__(self, data):
        super(Output, self).__init__()

        self.data = data

        self.audio = Audio(2)
        self.synth = Synth('data/FluidR3_GM.sf2')

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(120)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)

        self.add(Color(1, 1, 1))
        self.add(Rectangle(pos=(0, 0), size=Window.size))
        self.add(Color(0, 0, 0))
        self.staff = Staff((200, 300), (400, 100), -1)
        self.add(self.staff)

        # TODO: This is sample data, remove it.
        data = [{'s': 67, 'a': 64, 't': 60, 'b': 53},
                {'s': 67, 'a': 62, 't': 59, 'b': 53},
                {'s': 67, 'a': 64, 't': 60, 'b': 48}]
        for i, beat in enumerate(data):
            for (voice, color, stem_direction) in self.voice_info:
                if voice in beat:
                    self.staff.add_note(VisualNote(self.staff, (i * 90, 0), beat[voice], 5.0, color, stem_direction))

    def on_update(self, dt):
        super(Output, self).on_update(dt)
        self.audio.on_update()

