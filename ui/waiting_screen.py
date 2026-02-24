from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.app import App

from ui.utils import show_popup

import types

class WaitingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.show_popup = types.MethodType(show_popup, self)

        root = BoxLayout(orientation="vertical", padding=20, spacing=20)

        title = Label(
            text="🏆 Leaderboard 🏆",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=32,
            color=[0, 1, 0, 1],
            size_hint_y=0.2,
        )
        root.add_widget(title)

        self.leaderboard_box = BoxLayout(
            orientation="vertical",
            spacing=10,
            size_hint_y=0.6,
        )
        root.add_widget(self.leaderboard_box)

        self.login_button = Button(
            text="LOGIN",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=28,
            background_normal="",
            background_color=(0, 0.4, 0, 1),
            color=(0, 1, 0, 1),
            size_hint_y=0.2,
        )
        self.login_button.bind(on_press=self.go_to_pin)

        root.add_widget(self.login_button)
        self.add_widget(root)

    def refresh_leaderboard(self):
        self.leaderboard_box.clear_widgets()
        users = self.app.bank_db.get_top_users(5)

        if not users:
            self.leaderboard_box.add_widget(
                Label(text="No users yet", color=[0, 1, 0, 1])
            )
            return

        for idx, user in enumerate(users, start=1):
            self.leaderboard_box.add_widget(
                Label(
                    text=f"{idx}. {user['name']} — {int(user['score'] * 100)}",
                    font_name="ui/fonts/PressStart2P-Regular.ttf",
                    font_size=20,
                    color=[0, 1, 0, 1],
                )
            )

    def go_to_pin(self, instance):
        self.app.sm.current = "pin"

    def withdraw_coins(self, amount):
        """
        Withdraw coins from the shared coin dispenser.
        """
        dispenser = self.app.devices.get("coin_dispenser")
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

    def handle_rfid(self, card):
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
        self.refresh_leaderboard()
        self.app.handle_change_led()
