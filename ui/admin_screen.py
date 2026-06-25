from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.popup import Popup

import subprocess
from ui.utils import TimeoutMixin, show_popup, check_wifi

import types

# ───────── Admin colour scheme ─────────
ORANGE_BG = (0.6, 0.35, 0.0, 1)      # dark orange
ORANGE_TEXT = (1.0, 0.75, 0.2, 1)    # yellow-orange
GREY_BG = (0.25, 0.25, 0.25, 1)
GREY_TEXT = (0.6, 0.6, 0.6, 1)

class AdminScreen(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app = App.get_running_app()
        self.timeout = TimeoutMixin(30, self.app.show_waiting_screen)
        self.show_popup = types.MethodType(show_popup, self)

        self.coin_dispenser = self.app.devices["coin_dispenser"]
        self.coin_muncher = self.app.devices["coin_muncher"]

        self.muncher_running = False
        self.dispenser_running = False

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

        shutdown_btn = Button(
            text="SHUTDOWN",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=20,
            background_normal="",
            background_color=(0.6, 0, 0, 1),
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=60,
        )

        shutdown_btn.bind(on_press=lambda x: self.confirm_shutdown())

        top_bar.add_widget(shutdown_btn)

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

        # ─────────────────────────────
        # Header
        # ─────────────────────────────

        admin_header = Label(
            text="ADMIN PANEL",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=36,
            color=(1, 0.8, 0, 1),  # yellow-orange
            size_hint_y=None,
            height=60,
        )
        self.layout.add_widget(admin_header)

        self.layout.add_widget(BoxLayout(size_hint_y=None, height=15))

        # ─────────────────────────────
        # Munch Hopper
        # ─────────────────────────────

        muncher_controls = BoxLayout(
            orientation="horizontal",
            spacing=10,
            size_hint_x=None,
            width=260,
        )

        self.muncher_on_btn = self._make_admin_button("ON")
        self.muncher_off_btn = self._make_admin_button("OFF")

        self.muncher_on_btn.bind(on_press=lambda x: self.run_muncher())
        self.muncher_off_btn.bind(on_press=lambda x: self.stop_muncher())

        muncher_controls.add_widget(self.muncher_on_btn)
        muncher_controls.add_widget(self.muncher_off_btn)

        self.layout.add_widget(
            self._make_row("Munch Hopper:", muncher_controls)
        )

        # ─────────────────────────────
        # Dispenser Hopper
        # ─────────────────────────────

        dispenser_controls = BoxLayout(
            orientation="horizontal",
            spacing=10,
            size_hint_x=None,
            width=260,
        )

        self.dispenser_on_btn = self._make_admin_button("ON")
        self.dispenser_off_btn = self._make_admin_button("OFF")

        self.dispenser_on_btn.bind(on_press=lambda x: self.run_dispenser())
        self.dispenser_off_btn.bind(on_press=lambda x: self.stop_dispenser())

        dispenser_controls.add_widget(self.dispenser_on_btn)
        dispenser_controls.add_widget(self.dispenser_off_btn)

        self.layout.add_widget(
            self._make_row("Dispenser Hopper:", dispenser_controls)
        )


        # ─────────────────────────────
        # Machine Balance
        # ─────────────────────────────

        self.machine_balance_label = Label(
            text="£0.00",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=28,
            color=(1, 0.9, 0.4, 1),
            size_hint_x=None,
            width=260,
            halign="left",
        )
        self.machine_balance_label.bind(
            size=lambda *x: setattr(self.machine_balance_label, "text_size", self.machine_balance_label.size)
        )

        self.layout.add_widget(
            self._make_row("Machine Balance:", self.machine_balance_label, height=70)
        )

        bottom_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=45,
            padding=[0, 0, 10, 0],
        )

        self.wifi_label = Label(
            text="WiFi",
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=18,
            color=(0, 1, 0, 1),
            size_hint=(None, None),
            size=(120, 45),
            halign="left",
            valign="middle",
        )

        self.wifi_label.bind(
            size=lambda *x: setattr(self.wifi_label, "text_size", self.wifi_label.size)
        )

        bottom_bar.add_widget(self.wifi_label)
        
        self.layout.add_widget(bottom_bar)

        self.add_widget(self.layout)

        self._update_hopper_buttons()

    def _make_admin_button(self, text):
        return Button(
            text=text,
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=20,
            background_normal="",      # REQUIRED
            background_color=ORANGE_BG,
            color=ORANGE_TEXT,
        )
    
    def _make_row(self, title, right_widget, height=60):
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=height,
            spacing=20,
        )

        label = Label(
            text=title,
            font_name="ui/fonts/PressStart2P-Regular.ttf",
            font_size=24,
            color=(1, 0.8, 0, 1),
            size_hint_x=None,
            width=420,
            halign="left",
            valign="middle",
        )
        label.bind(size=lambda *x: setattr(label, "text_size", label.size))

        row.add_widget(label)
        row.add_widget(right_widget)
        return row

    def on_enter(self):
        self.coin_dispenser.set_error_callback(self.on_hopper_error)
        self.coin_muncher.set_error_callback(self.on_hopper_error)
        self.app.devices['coin_muncher'].set_low_level_callback(self._on_muncher_coin_detected)
        self.app.devices['coin_inserter'].stop()
        self.timeout.start_timeout()

        self._wifi_event = Clock.schedule_interval(self._wifi_check, 2)
        self.update_wifi_status()  # initial sync

        self.app.handle_change_led()
        self.update_balance()
        self._watchdog_event = Clock.schedule_interval(self._ui_watchdog, 0.5)

    def on_leave(self):
        self.coin_dispenser.set_error_callback(None)
        self.timeout.cancel_timeout()

        if hasattr(self, "_wifi_event"):
            self._wifi_event.cancel()
            del self._wifi_event

        if hasattr(self, "_watchdog_event"):
            self._watchdog_event.cancel()


    def _on_muncher_coin_detected(self, low_state):
        if not low_state:
            return  # only act when coins are passing
        
        self.run_muncher()
        self.timeout.restart()

    def on_hopper_error(self, message):
        Clock.schedule_once(
            lambda dt: self.show_popup(f"Hopper Error:\n{message}")
        )
        print(f"[Coin Hopper] ERROR: {message}")
        self.timeout.restart()
        self.update_balance()

    def _update_hopper_buttons(self):
        # Muncher
        self._set_button_state(self.muncher_on_btn, not self.muncher_running)
        self._set_button_state(self.muncher_off_btn, self.muncher_running)

        # Dispenser
        self._set_button_state(self.dispenser_on_btn, not self.dispenser_running)
        self._set_button_state(self.dispenser_off_btn, self.dispenser_running)


    def _set_button_state(self, btn, enabled):
        btn.disabled = not enabled

        if enabled:
            btn.background_color = ORANGE_BG
            btn.color = ORANGE_TEXT
        else:
            btn.background_color = GREY_BG
            btn.color = GREY_TEXT

    def coin_withdrawn(self, amount):
        self.update_balance()
        self.timeout.restart()

    def coin_munched(self, amount):
        self.update_balance()
        self.timeout.restart()

    def handle_rfid(self, card):
        self.app.bank_db.update_rfid_card(card['id'], card['value'], 1)
        msg = ""
        if card['active']:
            msg = "Voucher Active"
        else:
            msg = "Voucher Activated"

        self.show_popup("" \
        f"{msg}\n" \
        f"ID: {card['id']}\n" \
        f"Value: {card['value']}\n")

        self.timeout.restart()

    def update_wifi_status(self):
        if getattr(self.app, "wifi_connected", False):
            self.wifi_label.text = "WiFi"
            self.wifi_label.color = (0, 1, 0, 1)
        else:
            self.wifi_label.text = "No WiFi"
            self.wifi_label.color = (1, 0, 0, 1)

    def _wifi_check(self, dt):
        new_state = check_wifi()

        # store previous state on app (create if missing)
        if not hasattr(self.app, "wifi_connected"):
            self.app.wifi_connected = None

        # only update if changed
        if self.app.wifi_connected != new_state:
            self.app.wifi_connected = new_state
            self.update_wifi_status()

    # ─────────────────────────────
    # Button handlers
    # ─────────────────────────────

    def run_muncher(self):
        if self.muncher_running:
            return

        print("[ADMIN] Running muncher hopper")
        self.coin_muncher.on()
        self.muncher_running = True
        self._update_hopper_buttons()
        self.timeout.restart()
        self.update_balance()

    def stop_muncher(self):
        if not self.muncher_running:
            return

        self.coin_muncher.off()
        self.muncher_running = False
        self._update_hopper_buttons()
        self.timeout.restart()
        self.update_balance()

    def run_dispenser(self):
        if self.dispenser_running:
            return

        print("[ADMIN] Running dispenser hopper")
        self.coin_dispenser.on()
        self.dispenser_running = True
        self._update_hopper_buttons()
        self.timeout.restart()
        self.update_balance()

    def stop_dispenser(self):
        if not self.dispenser_running:
            return

        self.coin_dispenser.off()
        self.dispenser_running = False
        self._update_hopper_buttons()
        self.timeout.restart()
        self.update_balance()

    def update_balance(self):
        app = App.get_running_app()
        balance = app.bank_db.get_machine_cash("Hoppers")
        self.machine_balance_label.text = f"£{balance:.2f}"

    def _ui_watchdog(self, dt):
        # If hardware exposes a state flag, use it
        if hasattr(self.coin_muncher, "motor_on"):
            self.muncher_running = self.coin_muncher.motor_on

        if hasattr(self.coin_dispenser, "motor_on"):
            self.dispenser_running = self.coin_dispenser.motor_on

        self._update_hopper_buttons()

    def confirm_shutdown(self):
           layout = BoxLayout(
               orientation="vertical",
               padding=20,
               spacing=20
           )

           layout.add_widget(Label(
               text="Shutdown Raspberry Pi?",
               font_name="ui/fonts/PressStart2P-Regular.ttf",
           ))

           buttons = BoxLayout(spacing=10)

           cancel_btn = Button(text="Cancel")
           shutdown_btn = Button(text="Shutdown")

           buttons.add_widget(cancel_btn)
           buttons.add_widget(shutdown_btn)

           layout.add_widget(buttons)

           popup = Popup(
               title="Confirm Shutdown",
               content=layout,
               size_hint=(0.7, 0.4),
               auto_dismiss=False
           )

           cancel_btn.bind(on_press=popup.dismiss)

           shutdown_btn.bind(
               on_press=lambda x: self.safe_shutdown(popup)
           )

           popup.open()
