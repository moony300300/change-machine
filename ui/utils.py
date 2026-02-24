from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.clock import Clock


class TimeoutMixin:
    def __init__(self, duration, callback):
        self.TIMEOUT_DURATION = duration
        self.callback = callback

    def start_timeout(self):
        self.cancel_timeout()
        self._timeout_event = Clock.schedule_once(self.callback, self.TIMEOUT_DURATION)

    def restart(self):
        self.cancel_timeout()
        self.start_timeout()

    def cancel_timeout(self):
        if hasattr(self, "_timeout_event") and self._timeout_event:
            self._timeout_event.cancel()

def show_popup(self, message, duration=2.5):
    """
    Show a temporary popup message on the screen.
    
    :param message: str, text to display
    :param duration: float, seconds before auto-dismiss
    """
    popup = ModalView(size_hint=(0.8, 0.3), auto_dismiss=True, background_color=[0,0,0,0.8])
    popup_label = Label(
        text=message,
        font_name="ui/fonts/PressStart2P-Regular.ttf",
        font_size=24,
        color=[0, 1, 0, 1],
        halign="center",
        valign="middle",
    )
    popup_label.bind(size=popup_label.setter('text_size'))
    popup.add_widget(popup_label)
    popup.open()

    # Auto-dismiss after duration seconds
    Clock.schedule_once(lambda dt: popup.dismiss(), duration)
