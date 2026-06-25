from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.app import App

from ui.utils import TimeoutMixin
from ui.utils import show_popup

import types


class PinScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.timeout = TimeoutMixin(15, self.app.show_waiting_screen)
        self.show_popup = types.MethodType(show_popup, self)
        self.pin = ""
        self.new_user_mode = False
        self.current_user = None  # Store the user who needs a new PIN

        root = BoxLayout(orientation="vertical", padding=20, spacing=20)

        self.display = Label(
            text="Enter PIN",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=36,
            color=[0, 1, 0, 1],
            size_hint_y=0.3,
        )

        root.add_widget(self.display)

        keypad = GridLayout(cols=3, spacing=10, size_hint_y=0.7)

        for n in range(1, 10):
            keypad.add_widget(self._make_button(str(n)))

        keypad.add_widget(self._make_button("Clear"))
        keypad.add_widget(self._make_button("0"))
        keypad.add_widget(self._make_button("←"))

        root.add_widget(keypad)
        self.add_widget(root)

    def _make_button(self, text):
        btn = Button(
            text=text,
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=24,
            background_normal="",
            background_color=(0, 0.4, 0, 1),
            color=(0, 1, 0, 1),
        )
        btn.bind(on_press=self.on_key)
        return btn

    def on_key(self, instance):
        self.timeout.restart()

        key = instance.text

        if key == "Clear":
            self.clear()
        elif key == "←":
            self.pin = self.pin[:-1]
        else:
            if len(self.pin) < 4:
                self.pin += key

        self.update_display()

        if len(self.pin) == 4:
            self.check_pin()

    def update_display(self):
        self.display.text = "*" * len(self.pin)

    def check_pin(self):
        if self.new_user_mode:
            self.set_new_pin()
            return

        user = self.app.bank_db.get_user_by_pin(self.pin)
        if user:
            self.clear()
            # If user is flagged as new, switch to new pin mode
            if user['newUser']:
                self.new_user_mode = True
                self.current_user = user
                self.display.text = "Set NEW PIN"
                self.show_popup("Enter a new 4-digit PIN")
            else:
                self.app.login_user(user)
        else:
            self.flash_error_message("INVALID PIN")

    def set_new_pin(self):
        """Called when new_user_mode is active and a 4-digit PIN has been entered."""
        # Check uniqueness
        if self.app.bank_db.get_user_by_pin(self.pin):
            self.flash_error_message("PIN already taken")
            return

        # Save new PIN
        self.app.bank_db.update_user_pin(self.current_user, self.pin)
        self.app.bank_db.set_user_not_new(self.current_user)  # mark newUser = 0

        self.show_popup("PIN updated successfully")
        self.new_user_mode = False
        self.current_user = None
        self.clear()

        # Login with the new PIN
        user = self.app.bank_db.get_user_by_pin(self.pin)
        if user:
            self.app.login_user(user)

    def flash_error_message(self, message):
        """Flash a custom error message."""
        self.display.text = message
        self.display.color = [1, 0, 0, 1]
        Clock.schedule_once(self.reset_after_error, 1)

    def reset_after_error(self, dt):
        self.display.color = [0, 1, 0, 1]
        self.clear()

    def clear(self):
        self.pin = ""
        self.display.text = "Enter PIN"

    def withdraw_coins(self, amount):
        """
        Withdraw coins from the shared coin dispenser.
        """
        dispenser = self.app.devices.get("coin_dispenser")
        self.timeout.restart()
        if dispenser:
            dispenser.withdraw_coins(amount)
        else:
            print(f"[{self.name}] ERROR: No coin dispenser found")

    def on_hopper_error(self, message):
        Clock.schedule_once(
            lambda dt: self.show_popup(f"Hopper Error:\n{message}")
        )
        print(f"[Coin Hopper] ERROR: {message}")

    def _on_muncher_coin_detected(self, low_state):
        if not low_state:
            return  # only act when coins are passing

        # Check if a user is logged in
        current_user = getattr(self.app, 'current_user', None)
        if not current_user:
            # No user, show popup
            Clock.schedule_once(lambda dt: self.show_popup("Please log in to deposit coins"))

    def handle_coin_insert(self, amount):
        self.withdraw_coins(amount)
        self.timeout.restart()

    def handle_rfid(self, card):
        self.timeout.restart()
        if not card['active']:
            self.show_popup("Prize already redeemed!")
            return
        
        self.app.bank_db.update_rfid_card(card['id'], card['value'], 0)
        dispenser = self.app.devices.get("coin_dispenser")
        if dispenser:
            dispenser.withdraw_coins(card['value'])
        else:
            print(f"[{self.name}] ERROR: No coin dispenser found")
            self.show_popup('Error detected please contact an admin')
            return

        return self.show_popup(f'Congratulations!\nRedeemed £{card["value"]:.2f}')

    def on_enter(self):
        self.app.devices["coin_dispenser"].set_error_callback(self.on_hopper_error)
        self.app.devices['coin_muncher'].set_error_callback(self.on_hopper_error)
        self.app.devices['coin_muncher'].set_low_level_callback(self._on_muncher_coin_detected)
        self.app.devices['coin_inserter'].stop()
        self.clear()
        self.pin = ""
        self.new_user_mode = False
        self.current_user = None
        self.timeout.start_timeout()
        self.app.handle_change_led()

    def on_leave(self):
        self.timeout.cancel_timeout()
