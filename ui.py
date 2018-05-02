from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Mesh, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.core.image import Image
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label

from common.core import *
from common.gfxutil import KFAnim, AnimGroup, CEllipse, CRectangle
from common.gfxutil import topleft_label

# TODO: Barlines, stems, standard accidentals.

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

class Staff(Widget):
    def __init__(self, accidental_type=-1, *args, **kwargs):
        super(Staff, self).__init__(*args, **kwargs)
        self.accidental_type = accidental_type
        self.notes = []
        self.objects = InstructionGroup()
        self.canvas.add(self.objects)
        self.draw()
        self.bind(pos=self.draw, size=self.draw)
        self.beat = 0
        self.display_history = 1

    def draw(self, a=None, b=None):
        self.objects.clear()
        self.spacing = self.size[1] / 10.0
        for i in range(11):
            if i == 5:
                # Middle C is relegated to ledger lines.
                continue
            height = i * self.spacing * 2 - self.spacing * 4
            self.objects.add(Line(points=(0, height, self.size[0], height)))
        self.objects.add(CRectangle(cpos=(self.spacing, self.spacing * 11.5),
                                    size=(self.spacing * 5, self.spacing * 12),
                                    texture=Image('data/treble.png').texture))
        self.objects.add(CRectangle(cpos=(self.spacing, self.spacing * 0.5),
                                    size=(self.spacing * 5, self.spacing * 7),
                                    texture=Image('data/bass.png').texture))
        self.objects.add(PushMatrix())
        # TODO: Make the x-component based on the current time.
        self.translation = Translate(self.size[0] * 0.25, self.spacing * 8)
        self.objects.add(self.translation)
        self.moving_objects = AnimGroup()
        for (beat, pitch, color, stem_direction) in self.notes:
            relative_beat = beat - self.beat + self.display_history - 1
            if relative_beat >= 0:
                self.moving_objects.add(VisualNote(self, (relative_beat * 90, 0), pitch, 5.0, color, stem_direction))
        self.objects.add(self.moving_objects)
        self.objects.add(PopMatrix())

    def add_note(self, beat, pitch, color, stem_direction):
        relative_beat = beat - self.beat + self.display_history - 1
        self.notes.append((beat, pitch, color, stem_direction))
        self.moving_objects.add(VisualNote(self, (relative_beat * 90, 0), pitch, 5.0, color, stem_direction))

    def on_update(self, dt):
        self.moving_objects.on_update()
        self.translation.x -= dt * 90.0
        #self.draw()


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
        self.ledger_color = Color(1, 1, 1)
        self.add(self.ledger_color)
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
        self.start = 0
        self.pos = pos
        self.on_update(0)

    def on_update(self, dt):
        self.notehead.on_update(dt)
        self.time += dt
        if self.pos[0] == 0:
            if not self.start:
                self.start = self.time
            self.color.a = 1.0 - (self.time - self.start) * 0.8
            self.ledger_color.a = self.color.a
        #self.color.v = self.color_anim.eval(self.time)


class PartSelector(BoxLayout):
    def __init__(self, set_part_active_callback, *args, **kwargs):
        super(PartSelector, self).__init__(*args, orientation='vertical', **kwargs)

        self.set_part_active = set_part_active_callback
        self.checkboxes = {}
        for p in ['s', 'a', 't', 'b', 'harmony']:
            checkbox = CheckBox()
            checkbox.bind(active=self.on_checkbox_toggled)
            self.checkboxes[p] = checkbox
            self.add_widget(self.checkboxes[p])

    def on_checkbox_toggled(self, checkbox, value):
        checkbox_active = value
        for part in ['s', 'a', 't', 'b', 'harmony']:
            if self.checkboxes[part] == checkbox:
                self.set_part_active(part, checkbox_active)

class UI(BoxLayout):

    # Associate voices with colors and stem directions.
    voice_info = [('s', (1, 0, 0), 'up'),
                  ('a', (1, 1, 0), 'down'),
                  ('t', (0, 1, 0), 'up'),
                  ('b', (0, 0, 1), 'down')]

    def __init__(self, data, input, *args, **kwargs):
        super(UI, self).__init__(*args, orientation='horizontal', **kwargs)

        self.data = data
        self.input = input

        self.part_selector = PartSelector(self.set_part_active, pos_hint={'center_y': 0.5}, size_hint=(.2, .5))
        self.add_widget(self.part_selector)

        self.staff = Staff(accidental_direction=-1, pos_hint={'center_x': 0.5}, size_hint=(.8, 1.))
        layout = RelativeLayout(pos_hint={'center_y': 0.5}, size_hint=(.8, .2))
        layout.add_widget(self.staff)
        self.add_widget(layout)
        self.bind(pos=self.draw, size=self.draw)
        self.draw()

        self.info = Label(text = "text", valign='top', halign='left', font_size='20sp',
                          size_hint=(1.0, 1.0), pos_hint={'center_x': -0.12, 'y': 1.0})
        layout.add_widget(self.info)

        self.selected_beat = 0

    def set_part_active(self, part, active):
        self.input.set_part_enabled(part, active)

    def draw(self, a=None, b=None):
        # TODO: This is sample data, remove it.
        data = [{'s': 67, 'a': 64, 't': 60, 'b': 53},
                {'s': 67, 'a': 62, 't': 59, 'b': 53},
                {'s': 67, 'a': 64, 't': 60, 'b': 48}]
        for i, beat in enumerate(data):
            for (voice, color, stem_direction) in self.voice_info:
                if voice in beat:
                    pass#self.staff.add_note(i, beat[voice], color, stem_direction)

    def on_beat(self, tick):
        pass#print(tick)

    def on_update(self):
        self.staff.on_update(kivy.clock.Clock.frametime)

        key_mapping = [
            'C',
            'C#',
            'D',
            'Eb',
            'E',
            'F',
            'F#',
            'G',
            'Ab',
            'A',
            'Bb',
            'B',
            'C',
        ]

        self.info.text = "Selected Beat: {}\nHarmonies:\n{}".format(self.selected_beat + 1,
            '\n'.join([
                "{}: {} {}".format(
                    i,
                    beat['harmony'].split('|')[1] if 'harmony' in beat else '',
                    beat['harmony'].split('|')[0] if 'harmony' in beat else '',
                )
                for i, beat in enumerate(self.data[self.staff.beat + 1:])
            ])
        )

