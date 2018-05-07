from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Mesh, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.core.image import Image
from kivy.core.text import Label as CoreLabel
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.label import CoreLabel
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
        self._selected_beat = 0
        self.canvas.add(self.objects)
        self.moving_objects = AnimGroup()
        self.bind(pos=self.draw, size=self.draw)
        self.beat = 0
        self.display_history = 2
        self.beat_groups = {}
        self.draw()

    @property
    def selected_beat(self):
        return self._selected_beat

    @selected_beat.setter
    def selected_beat(self, selected_beat):
        self._selected_beat = selected_beat
        self.beat_highlighter.cpos = (450 + selected_beat * 90, self.beat_highlighter.cpos[1])

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
        self.objects.add(Color(.7, .8, 1.0, 0.3))
        # TODO: Fewer magic numbers.
        self.beat_highlighter = CRectangle(cpos=(450 + self._selected_beat * 90, self.spacing * 6),
                                    csize=(100, self.spacing * 24))
        self.objects.add(self.beat_highlighter)
        self.objects.add(PushMatrix())
        self.translation = Translate(700 - self.time * 90.0, self.spacing * 8)
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
        if 'harmony' in beat:
            label = CoreLabel(text=beat['harmony'], font_size=25, color=(1, 1, 1, 1))
            label.refresh()
            texture = label.texture
            texture_size = list(texture.size)
            # A slight hack.
            container = AnimGroup()
            container.color = Color(1, 1, 1)
            container.add(container.color)
            beat_pos = beat_id - self.display_history - 1
            container.add(Rectangle(pos=(beat_pos * 90 - texture_size[0] / 2, -self.spacing * 16), size=texture_size, texture=label.texture))
            beat_group.add(container)

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
        self.rect = CRectangle(cpos=(pos[0], pos[1] + 2.5*r), csize=(2.5*r, 7*r),
                               texture=Image('data/quarter.png').texture)
        self.add(self.rect)

    def on_update(self, dt):
        return True


class VisualNote(InstructionGroup):
    sharp_symbol = CoreLabel(text=u'\u266f', font_size=75, font_name="Code2001")
    flat_symbol = CoreLabel(text=u'\u266d', font_size=75, font_name="Code2001")

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
            # Draw a sharp.
            self.sharp_symbol.refresh()
            texture = self.sharp_symbol.texture
            w, h = self.sharp_symbol.texture.size
            self.add(Rectangle(size=self.sharp_symbol.texture.size, pos=(-2*w, height - h/4), texture=texture))
        elif accidental < 0:
            # Draw a flat.
            self.flat_symbol.refresh()
            texture = self.flat_symbol.texture
            w, h = self.flat_symbol.texture.size
            self.add(Rectangle(size=self.flat_symbol.texture.size, pos=(-2*w, height - h/4), texture=texture))

        self.add(PopMatrix())

        self.time = 0
        self.start = 0


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

    @property
    def selected_beat(self):
        return self.staff.selected_beat

    @selected_beat.setter
    def selected_beat(self, selected_beat):
        self.staff.selected_beat = selected_beat

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
