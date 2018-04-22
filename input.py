from kivy.graphics.instructions import InstructionGroup

class Input(InstructionGroup):
    def __init__(self, data):
        super(Input, self).__init__()

        self.data = data
        # What information is the user currently filling in?
        self.selected_parts = {'s': False, 't': False, 'a': False, 'b': False,
                               'chord': False, 'key': False}

    def on_key_down(self, keycode, modifiers):
        pass

    def on_key_up(self, keycode):
        pass

    def on_touch_move(self, touch):
        pass

    def on_touch_down(self, touch):
        pass

    def on_touch_up(self, touch):
        pass

    def on_update(self, dt):
        pass

