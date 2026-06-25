from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.app import App
from kivy.clock import Clock

from ui.utils import TimeoutMixin, show_popup

import types


class UserScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app = App.get_running_app()

        self.timeout = TimeoutMixin(30, self.app.show_waiting_screen)
        self.show_popup = types.MethodType(show_popup, self)

        self.user = None

        # ─────────────────────────────
        # Layout
        # ─────────────────────────────

        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        top_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=80,
            padding=[0, 0, 10, 0],
        )

        # Add manual munch button
        self.manual_munch_btn = Button(
            text="Start Munch",
            font_size=24,
            background_color=(0, 0.4, 0, 1),
            color=(0, 1, 0, 1),
            size_hint=(None, None),
            size=(200, 60)
        )
        self.manual_munch_btn.bind(on_press=lambda x: self.start_munching())
        top_bar.add_widget(self.manual_munch_btn)

        top_bar.add_widget(Label())

        logout_btn = Button(
            size_hint=(None, None),
            size=(80, 80),
            background_normal="ui/assets/logout.png",
            background_down="ui/assets/logout.png",
            border=(0, 0, 0, 0),
        )
        logout_btn.bind(on_press=lambda x: self.app.show_waiting_screen())
        top_bar.add_widget(logout_btn)

        self.layout.add_widget(top_bar)

        self.name_label = Label(
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=32,
            color=[0, 1, 0, 1],
        )
        self.balance_label = Label(
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=28,
            color=[0, 1, 0, 1],
        )
        self.score_label = Label(
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=28,
            color=[0, 1, 0, 1],
        )

        self.layout.add_widget(self.name_label)
        self.layout.add_widget(self.balance_label)
        self.layout.add_widget(self.score_label)

        self.layout.add_widget(BoxLayout(size_hint_y=None, height=40))

        self.withdraw_header = Label(
            text="Withdraw Coins",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=24,
            color=(0, 1, 0, 1),
            size_hint_y=None,
            height=40,
            halign="left",
            valign="bottom",
        )
        self.withdraw_header.bind(
            size=lambda instance, value: setattr(instance, "text_size", (value[0], None))
        )

        self.layout.add_widget(self.withdraw_header)

        self.withdraw_layout = GridLayout(cols=3, spacing=10, size_hint_y=None, height=100)
        self.withdraw_layout.add_widget(self._make_withdraw_button("2p", 0.02))
        self.withdraw_layout.add_widget(self._make_withdraw_button("10p", 0.10))
        self.withdraw_layout.add_widget(self._make_withdraw_button("50p", 0.50))
        self.layout.add_widget(self.withdraw_layout)

        self.add_widget(self.layout)

        # Hardware references (no ownership)
        self.coin_inserter = self.app.devices["coin_inserter"]
        self.coin_dispenser = self.app.devices["coin_dispenser"]
        self.coin_muncher = self.app.devices["coin_muncher"]

    # ─────────────────────────────
    # UI helpers
    # ─────────────────────────────

    def _make_withdraw_button(self, label, amount):
        btn = Button(
            text=label,
            font_size=24,
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            background_normal="",
            background_color=(0, 0.4, 0, 1),
            color=(0, 1, 0, 1),
        )
        btn.bind(on_press=lambda x: self.withdraw_coins(amount))
        return btn

    # ─────────────────────────────
    # User logic
    # ─────────────────────────────

    def update_user(self, user):
        self.user = self.app.bank_db.get_user_by_pin(user["pin"])
        if self.user:
            self.name_label.text = f"Name: {self.user['name']}"
            self.balance_label.text = f"Balance: £{self.user['balance']:.2f}"
            self.score_label.text = f"Score: {int((self.user['balance'] - self.user['float']) * 100)}"
        else:
            self.name_label.text = "Name: Unknown"
            self.balance_label.text = "Balance: £0.00"
            self.score_label.text = "Score: 0"

    def handle_coin_insert(self, amount):
        self.app.bank_db.update_balance(
            self.user,
            amount,
            "Deposit",
            "Coin Inserter",
            f"Inserted £{amount:.2f}",
        )
        Clock.schedule_once(lambda dt: self.update_user(self.user))

        self.timeout.restart()

    def handle_rfid(self, card):
        if not card['active']:
            self.show_popup("Prize already redeemed!")
            return
        
        self.app.bank_db.update_rfid_card(card['id'], card['value'], 0)
        self.app.bank_db.update_balance(self.user, card["value"], 'Redemption', 'RFID', f'Redeemed £{card["value"]:.2f}')

        self.timeout.restart()
        self.update_user(self.user)
        return Clock.schedule_once(lambda dt: self.show_popup(f'Congratulations!\nRedeemed £{card["value"]:.2f}'))

    def withdraw_coins(self, amount):
        if not self.user:
            Clock.schedule_once(
            lambda dt: self.show_popup("No user logged in")
            )
            return

        if self.user["balance"] < amount:
            Clock.schedule_once(
            lambda dt: self.show_popup("Insufficient funds")
            )
            return

        self.app.withdraw_coins(amount)

        self.timeout.restart()

    def coin_withdrawn(self, amount):
        self.app.bank_db.update_balance(
            self.user,
            -amount,
            "Withdrawal",
            "Hopper",
            f"Withdrew £{amount:.2f}",
        )
        self.update_user(self.user)
        self.timeout.restart()

    def start_munching(self):
        """Start munching coins from the coin hopper for the logged-in user."""
        if not self.user:
            Clock.schedule_once(lambda dt: self.show_popup("Please log in to deposit coins"))
            return
        
        # Start motor, reset last_coin_time for timeout
        self.coin_muncher.on()
        self.timeout.restart()

    def coin_munched(self, amount):
        """Called whenever a coin passes through the muncher."""
        if not self.user:
            # No user logged in, ignore
            return

        self.app.bank_db.update_balance(
            self.user,
            amount,
            "Deposit",
            "Hopper",
            f"Deposited £{amount:.2f}"
        )
        self.update_user(self.user)
        self.timeout.restart()

    def _on_muncher_coin_detected(self, low_state):
        if not low_state:
            return  # only act when coins are passing

        self.start_munching()
        self.timeout.restart()

    # ─────────────────────────────
    # Hopper error handling
    # ─────────────────────────────

    def on_hopper_error(self, message):
        Clock.schedule_once(
            lambda dt: self.show_popup(f"Hopper Error:\n{message}")
        )
        print(f"[Coin Hopper] ERROR: {message}")
        self.timeout.restart()

    # ─────────────────────────────
    # Screen lifecycle
    # ─────────────────────────────

    def on_enter(self):
        self.coin_dispenser.set_error_callback(self.on_hopper_error)
        self.coin_muncher.set_error_callback(self.on_hopper_error)
        self.app.devices['coin_muncher'].set_low_level_callback(self._on_muncher_coin_detected)
        self.app.devices['coin_inserter'].start()
        self.timeout.start_timeout()

        if self.coin_muncher.last_low_state:
            self.start_munching()

        self.app.handle_change_led()

    def on_leave(self):
        self.user = None
        self.coin_dispenser.set_error_callback(None)
        self.timeout.cancel_timeout()