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

# TODO: Barlines, key signatures, other types of notes?

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
        self.tick = 0
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
        self.beat_highlighter.cpos = (470 + selected_beat * 90, self.beat_highlighter.cpos[1])

    def set_accidental_type(self, accidental_type):
        self.accidental_type = accidental_type

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
        # TODO: Fewer magic numbers.
        self.objects.add(Color(1, 1, 1))
        now_pos = 470 - 90 - 45
        print(self._selected_beat, self.display_history)
        self.objects.add(Line(points=(now_pos, -self.spacing * 4, now_pos, self.spacing * 16)))
        self.objects.add(Color(.7, .8, 1.0, 0.3))
        self.beat_highlighter = CRectangle(cpos=(470 + self._selected_beat * 90, self.spacing * 6),
                                    csize=(100, self.spacing * 24))
        self.objects.add(self.beat_highlighter)
        self.objects.add(PushMatrix())
        self.translation = Translate(700 - self.tick * 90.0 / 480.0, self.spacing * 8)
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
        for (voice, color, stem_direction, clef) in UI.voice_info:
            if voice in beat:
                reference = {'s': 77, 'a': 64, 't': 57, 'b': 43}[voice]
                notes = [note for note in beat[voice] if note not in [None, -1]]
                if notes:
                    reference = notes[0]
                if len(beat[voice]) > 2:
                    beat_start = beat_id - self.display_history - 1
                    beat_group.add(Tuplet(self, (beat_start * 90, 0), len(beat[voice]), reference, color))
                for idx, note in enumerate(beat[voice]):
                    # TODO: rests, rhythmic grouping
                    if note != -1:
                        beat_pos = beat_id + idx / float(len(beat[voice])) - self.display_history - 1
                        clef_bounds = (0, 10) if clef == 'treble' else (-10, -2)
                        manual = 'manual' in beat and voice in beat['manual']
                        value = 1 if len(beat[voice]) > 1 else 2
                        if note is None:
                            if idx > 0 and beat[voice][idx-1] not in [None, -1]:
                                reference = beat[voice][idx-1]
                            elif idx + 1 < len(beat[voice]) and beat[voice][idx+1] not in [None, -1]:
                                reference = beat[voice][idx+1]
                            beat_group.add(VisualRest(self, (beat_pos * 90, 0),
                                                      reference, beat_pos -
                                                      self.beat, color,
                                                      clef_bounds))
                        else:
                            beat_group.add(VisualNote(self, (beat_pos * 90, 0),
                                                      note, value, beat_pos -
                                                      self.beat, color,
                                                      stem_direction, clef_bounds,
                                                      manual))
        label = CoreLabel(text="{}{}{}{}{}".format(
            "{}\n".format(beat['harmony']) if 'harmony' in beat else '',
            "|{}|\n".format(' ' * min(8, int((beat['spacing'] + 1) * 8))) if 'spacing' in beat and 'manual' in beat and 'spacing' in beat['manual'] else '',
            "{}\n".format(
                '.-+#'[max(0, min(4, int((beat['dissonance'] + 1) * 2)))]
            ) if 'dissonance' in beat and 'manual' in beat and 'dissonance' in beat['manual'] else '',
            "{}\n".format(''.join(
                'o' if t == True else '=' if t == -1 else '-'
                for t in beat['mel_rhythm']
            )) if 'manual' in beat and 'mel_rhythm' in beat['manual'] and 'mel_rhythm' in beat else '',
            "{}\n".format('\n'.join(''.join(
                '+' if t == True else '=' if t == -1 else '-'
                for t in beat['acc_rhythm'][part]
            ) for part in 'atb')) if 'manual' in beat and 'acc_rhythm' in beat['manual'] and 'acc_rhythm' in beat else '',
        ), font_size=25, color=(1, 1, 1, 1))
        label.refresh()
        texture = label.texture
        texture_size = list(texture.size)
        # A slight hack.
        container = AnimGroup()
        container.color = Color(1, 1, 1)
        container.add(container.color)
        beat_pos = beat_id - self.display_history - 1
        container.add(Rectangle(pos=(beat_pos * 90 - texture_size[0] / 2, -self.spacing * 27), size=texture_size, texture=label.texture))
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

    def on_update(self, dt):
        self.tick += dt
        self.moving_objects.on_update()
        self.translation.x -= dt * 90.0 / 480.0
        if self.beat in self.beat_groups:
            for obj in self.beat_groups[self.beat].objects:
                obj.color.a -= dt * 0.6 / 480.0


class Notehead(InstructionGroup):
    def __init__(self, pos, r, color, pitch, value, stem_direction, outline=False):
        super(Notehead, self).__init__()
        if stem_direction == 'down':
            self.add(PushMatrix())
            self.add(Rotate(angle=180, origin=(pos[0], pos[1])))
        image_src = ['data/quarter.png', 'data/halfnote.png'][value - 1]
        self.outline_color = Color(1, 1, 1)
        if outline:
            self.add(self.outline_color)
            self.add(PushMatrix())
            self.add(Scale(1.2, origin=(pos[0], pos[1])))
            self.outline = CRectangle(cpos=(pos[0], pos[1] + 2.5*r), csize=(2.5*r, 7*r),
                               texture=Image(image_src).texture)
            self.add(self.outline)
            self.add(PopMatrix())
        self.add(color)
        self.rect = CRectangle(cpos=(pos[0], pos[1] + 2.5*r), csize=(2.5*r, 7*r),
                               texture=Image(image_src).texture)
        self.add(self.rect)
        if stem_direction == 'down':
            self.add(PopMatrix())

    def on_update(self, dt):
        self.outline_color.a = self.color.a
        return True


class VisualNote(InstructionGroup):
    sharp_symbol = CoreLabel(text=u'\u266f', font_size=75, font_name="Code2001")
    flat_symbol = CoreLabel(text=u'\u266d', font_size=75, font_name="Code2001")

    def __init__(self, staff, pos, pitch, value, duration, color, stem_direction, clef_bounds, outline):
        super(VisualNote, self).__init__()

        self.staff = staff

        self.add(PushMatrix())
        self.add(Translate(*pos))

        line, accidental = pitch_to_staff(pitch, staff.accidental_type)

        # Add ledger lines, if necessary.
        self.ledger_color = Color(1, 1, 1)
        self.add(self.ledger_color)
        lines = []
        if line < clef_bounds[0]:
            lines = range(line, clef_bounds[0])
        else:
            lines = range(clef_bounds[1], line + 1)
        for l in lines:
            if l % 2 == 0:
                height = l * staff.spacing
                self.add(Line(points=(-25, height, 25, height)))

        self.color = Color(*color)

        # Draw the note.
        height = line * staff.spacing
        self.notehead = Notehead((0, height), 10, self.color, pitch, value, stem_direction, outline)
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


class VisualRest(InstructionGroup):
    def __init__(self, staff, pos, pitch, duration, color, clef_bounds):
        super(VisualRest, self).__init__()

        self.staff = staff

        self.add(PushMatrix())
        self.add(Translate(*pos))
        line, _ = pitch_to_staff(pitch, staff.accidental_type)

        # Add ledger lines, if necessary.
        self.ledger_color = Color(1, 1, 1)
        self.add(self.ledger_color)
        lines = []
        if line < clef_bounds[0]:
            lines = range(line, clef_bounds[0])
        else:
            lines = range(clef_bounds[1], line + 1)
        for l in lines:
            if l % 2 == 0:
                height = l * staff.spacing
                self.add(Line(points=(-25, height, 25, height)))

        self.color = Color(*color)

        # Draw the rest.
        height = line * staff.spacing
        self.add(self.color)
        self.rect = CRectangle(cpos=(0, height), csize=(2.5*8, 7*8),
                               texture=Image('data/quarter_rest.png').texture)
        self.add(self.rect)
        self.add(PopMatrix())


class Tuplet(InstructionGroup):
    def __init__(self, staff, pos, number, pitch, color):
        super(Tuplet, self).__init__()

        self.staff = staff

        self.add(PushMatrix())
        self.add(Translate(*pos))
        line, _ = pitch_to_staff(pitch, staff.accidental_type)

        self.color = Color(*color)

        # Draw the tuplet.
        height = line * staff.spacing
        self.add(self.color)
        self.rect = CRectangle(cpos=(35, height + 80), csize=(90, 20),
                               texture=Image('data/tuplet.png').texture)
        self.add(self.rect)
        self.add(PopMatrix())


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

            label = LabelButton(text=name, font_size=25, halign='right',
                                valign='middle', on_press=lambda _: checkbox._do_press())
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
        part = lookup(keycode[1], 'satbhdwmc', ('s', 'a', 't', 'b', 'harmony',
                                                'dissonance', 'spacing', 'mel_rhythm', 'acc_rhythm'))
        if part:
            self.checkboxes[part]._do_press()

class UI(BoxLayout):

    # Associate voices with colors, stem directions, and clefs.
    voice_info = [('s', (1, 0, 0), 'up', 'treble'),
                  ('a', (1, 1, 0), 'down', 'treble'),
                  ('t', (0, 1, 0), 'up', 'bass'),
                  ('b', (0, 0.5, 1), 'down', 'bass')]

    def __init__(self, input, *args, **kwargs):
        super(UI, self).__init__(*args, orientation='horizontal', **kwargs)

        self.input = input

        self.part_selector = PartSelector(self.set_part_active,
                                          pos_hint={'center_y': 0.5}, size_hint=(.2, .5))
        self.add_widget(self.part_selector)

        self.staff = Staff(accidental_direction=-1, pos_hint={'center_x': 0.5}, size_hint=(.8, 1.))
        layout = RelativeLayout(pos_hint={'center_y': 0.5}, size_hint=(.8, .2))
        layout.add_widget(self.staff)
        self.add_widget(layout)

    @property
    def selected_beat(self):
        return self.staff.selected_beat

    @selected_beat.setter
    def selected_beat(self, selected_beat):
        self.staff.selected_beat = selected_beat

    def set_accidental_type(self, accidental_type):
        self.staff.set_accidental_type(accidental_type)

    def set_part_active(self, part, active):
        self.input.set_part_enabled(part, active)

    def on_key_down(self, keycode, modifiers):
        self.part_selector.on_key_down(keycode, modifiers)

    def on_beat(self, beat):
        self.staff.on_beat(beat)

    def on_update(self, dt):
        self.staff.on_update(dt)
