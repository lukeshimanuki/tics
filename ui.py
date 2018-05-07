from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Mesh, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.core.image import Image
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.button import ButtonBehavior

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
        self.objects = InstructionGroup()
        self.time = 0
        self.canvas.add(self.objects)
        self.moving_objects = AnimGroup()
        self.bind(pos=self.draw, size=self.draw)
        self.beat = 0
        self.display_history = 2
        self.beat_groups = {}
        self.draw()

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
        self.translation = Translate(self.size[0] * 1.5 - self.time * 90.0, self.spacing * 8)
        self.objects.add(self.translation)
        self.objects.add(self.moving_objects)
        self.objects.add(PopMatrix())

    def add_beat(self, beat_id, beat):
        if beat_id in self.beat_groups:
            # We've seen this beat before.
            if beat == self.beat_groups[beat_id]:
                # No need to redraw.
                return
            self.moving_objects.remove(self.beat_groups[beat_id])
        beat_group = AnimGroup()
        for (voice, color, stem_direction) in UI.voice_info:
            if voice in beat:
                for idx, note in enumerate(beat[voice]):
                    if note not in [None, -1]:
                        beat_pos = beat_id + idx / float(len(beat[voice])) - self.display_history - 1
                        # TODO: Make notes fade correctly, get rid of dead beat_group entries.
                        beat_group.add(VisualNote(self, (beat_pos * 90, 0),
                                                  note, beat_pos - self.beat, color, stem_direction))
        self.moving_objects.add(beat_group)
        self.beat_groups[beat_id] = beat_group

    def on_beat(self, beat):
        if self.beat != beat:
            self.beat = beat
            for beat_id, beat_group in self.beat_groups.items():
                if beat_id + self.display_history < self.beat:
                    self.moving_objects.remove(beat_group)
                    del self.beat_groups[beat_id]
                elif beat_id < self.beat:
                    for obj in beat_group.objects:
                        obj.color.a = 0.4
                elif beat_id == self.beat:
                    for obj in beat_group.objects:
                        obj.color.a = 1.0
                else:
                    for obj in beat_group.objects:
                        obj.color.a = 0.7
            self.draw()
        self.last_beat = self.time

    def on_update(self, dt):
        self.time += dt
        self.moving_objects.on_update()
        self.translation.x -= dt * 90.0
        if self.beat in self.beat_groups:
            for obj in self.beat_groups[self.beat].objects:
                # TODO: Actually incorporate tempo.
                obj.color.a = 1.0 - (self.time - self.last_beat) * 0.6


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


class LabelButton(ButtonBehavior, Label):
    pass

class PartSelector(BoxLayout):
    def __init__(self, set_part_active_callback, *args, **kwargs):
        super(PartSelector, self).__init__(*args, orientation='vertical', **kwargs)

        def add_checkbox(name, key):
            # This needs to be a separate function in order for the closure (in on_press) to work.
            box = BoxLayout(orientation='horizontal')

            checkbox = CheckBox(size_hint=(0.4, 1.0))
            checkbox.bind(active=self.on_checkbox_toggled)
            self.checkboxes[key] = checkbox

            label = LabelButton(text=name, font_size=25, halign='right', valign='middle', on_press=lambda _: checkbox._do_press())
            label.bind(size=label.setter('text_size'))

            box.add_widget(label)
            box.add_widget(self.checkboxes[key])
            self.add_widget(box)

        self.set_part_active = set_part_active_callback
        self.checkboxes = {}
        for name, key in [('Soprano', 's'), ('Alto', 'a'), ('Tenor', 't'),
                           ('Bass', 'b'), ('Harmony', 'harmony'),
                           ('Spacing', 'spacing'),
                           ('Dissonance', 'dissonance'),
                           ('Melodic Rhythm', 'mel_rhythm'),
                           ('Accompaniment Rhythm', 'acc_rhythm'),]:
            add_checkbox(name, key)

    def on_checkbox_toggled(self, checkbox, value):
        checkbox_active = value
        for part in ['s', 'a', 't', 'b', 'harmony', 'spacing', 'dissonance', 'mel_rhythm', 'acc_rhythm']:
            if self.checkboxes[part] == checkbox:
                self.set_part_active(part, checkbox_active)

    def on_key_down(self, keycode, modifiers):
        part = lookup(keycode[1], 'satbh', ('s', 'a', 't', 'b', 'harmony'))
        if part:
            self.checkboxes[part]._do_press()

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

    def on_key_down(self, keycode, modifiers):
        self.part_selector.on_key_down(keycode, modifiers)

    def on_beat(self, beat):
        self.staff.on_beat(beat)

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

