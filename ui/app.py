from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
import threading
import time

from databases.bank import BankDB
from interfaces.rfid import RFIDReader
from interfaces.coin_inserter import CoinInserter
from interfaces.hopper import CoinHopper
from interfaces.led_light import LED

from ui.waiting_screen import WaitingScreen
from ui.user_screen import UserScreen
from ui.pin_screen import PinScreen
from ui.admin_screen import AdminScreen

Window.fullscreen = "auto"
Window.show_cursor = False

bank_db = BankDB()

class BankApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bank_db = bank_db
        self.devices = {}  # store all devices here

    def build(self):
        self.sm = ScreenManager(transition=FadeTransition())
        
        self._init_hardware()

        self.waiting_screen = WaitingScreen(name="waiting")
        self.user_screen = UserScreen(name="user")
        self.pin_screen = PinScreen(name="pin")
        self.admin_screen = AdminScreen(name="admin")

        self.waiting_screen.app = self
        self.user_screen.app = self
        self.pin_screen.app = self
        self.admin_screen.app = self

        self.sm.add_widget(self.pin_screen)
        self.sm.add_widget(self.waiting_screen)
        self.sm.add_widget(self.user_screen)
        self.sm.add_widget(self.admin_screen)

        self.sm.current = "waiting"

        threading.Thread(target=self.handle_munch_led, daemon=True).start()
        threading.Thread(target=self.handle_dispenser_led, daemon=True).start()

        return self.sm

    def _init_hardware(self):
        # RFID Scanner
        self.devices["rfid_reader"] = RFIDReader(self.on_rfid_scanned)
        self.devices["rfid_reader"].start()
 
        # LEDs
        self.devices["dispenser_led"] = LED("DISPENSER_LED")
        self.devices["change_led"] = LED("CHANGE_LED")
        self.devices["munch_led"] = LED("MUNCH_LED")

        self.last_dispense_time = time.time() - 20

        # Coin Inserter
        self.devices["coin_inserter"] = CoinInserter(
            input_pin_name="COIN_INSERTER_POWER",
            output_pin_name="INSERTER_SENSOR",
            pulse_callback=self.handle_coin_insert,
            coin_value=0.10
        )

        # Coin Hoppers
        self.devices["coin_dispenser"] = CoinHopper(
            motor_pin="DISPENSER_MOTOR",
            coin_sensor_pin="DISPENSER_SENSOR",
            low_level_pin="DISPENSER_LOW",
            pulse_callback=self.coin_withdrawn,
            coin_value=0.02
        )

        self.devices["coin_muncher"] = CoinHopper(
            motor_pin="MUNCHER_MOTOR",
            coin_sensor_pin="MUNCHER_SENSOR",
            low_level_pin="MUNCHER_LOW",
            pulse_callback=self.coin_munched,
            coin_value=0.02
        )

        self.devices["coin_dispenser"].set_error_callback(
            lambda msg: Clock.schedule_once(
                lambda dt: self._handle_hopper_error(msg)
            )
        )
        self.devices["coin_muncher"].set_error_callback(
            lambda msg: Clock.schedule_once(
                lambda dt: self._handle_hopper_error(msg)
            )
        )

    def login_user(self, user):
        self.current_user = user
        self.user_screen.update_user(user)
        self.sm.current = "user"

    def show_waiting_screen(self, dt=None):
        self.current_user = None
        self.sm.current = "waiting"

    def show_admin_screen(self, dt=None):
        self.current_user = None
        self.sm.current = "admin"

    def _handle_hopper_error(self, message):
        screen = self.sm.current_screen
        if hasattr(screen, "show_popup"):
            screen.show_popup(message)
        else:
            print(message)

    def handle_coin_insert(self, amount):
        current_screen = self.sm.current_screen
        print(f"[Coin Inserter] Coin inserted on {current_screen.name} screen")
        
        if hasattr(current_screen, "handle_coin_insert"):
            current_screen.handle_coin_insert(amount)
        elif hasattr(current_screen, "show_popup"):
            current_screen.show_popup("Error Detected, please ask an admin for help")
        else:
            print(f"[Coin Inserter] ERROR: No handler found on {current_screen.name} screen")
    
    def coin_withdrawn(self, amount):
        self.bank_db.adjust_machine_cash('Hoppers', -amount)
        self.handle_change_led()
        current_screen = self.sm.current_screen
        self.last_dispense_time = time.time()
        print(f"[Coin Hopper] Coin withdrawn on {current_screen.name} screen")
        
        if hasattr(current_screen, "coin_withdrawn"):
            current_screen.coin_withdrawn(amount)
    
    def coin_munched(self, amount):
        self.bank_db.adjust_machine_cash('Hoppers', amount)
        self.handle_change_led()
        current_screen = self.sm.current_screen
        print(f"[Coin Hopper] Coin munched on {current_screen.name} screen")
        
        if hasattr(current_screen, "coin_munched"):
            current_screen.coin_munched(amount)
    
    def on_rfid_scanned(self, rfid):
        Clock.schedule_once(lambda dt: self._handle_rfid(rfid))

    def _handle_rfid(self, rfid):
        current_screen = self.sm.current_screen
        print(f"[RFID] Scanned on {current_screen.name}")

        card = self.bank_db.get_rfid_card_by_rfid(rfid)
        current_screen = self.sm.current_screen

        if not card:
            card = bank_db.add_rfid_card(rfid, 0)
            if hasattr(current_screen, "show_popup"):
                current_screen.show_popup("New RFID card registered, ID:", {card['id']})
                return

        # ─── ADMIN OVERRIDE ─────────────────────
        if card['is_admin']:
            self._handle_admin_rfid(current_screen)
            return

        # ─── SCREEN-SPECIFIC HANDLING ───────────
        if hasattr(current_screen, "handle_rfid"):
            current_screen.handle_rfid(card)
        else:
            print("[RFID] No handler on this screen")
            if hasattr(current_screen, "show_popup"):
                current_screen.show_popup("No RFID Handler found for this screen")

    def _handle_admin_rfid(self, current_screen):
        print("[RFID Scanner] Admin key detected")
        if current_screen.name == "user" and current_screen.user:
            self.bank_db.update_balance(current_screen.user, 1, 'Admin', 'RFID', f'Adjusted Balance by £1.00 by an Admin')
            if hasattr(current_screen, "update_user"):
                current_screen.update_user(current_screen.user)
            if hasattr(current_screen, "show_popup"):
                current_screen.show_popup("Increased balance by £1.00")
        else:
            self.show_admin_screen()

    def handle_change_led(self):
        change_led = self.devices['change_led']

        if self.bank_db.get_machine_cash('Hoppers') > 1:
            change_led.on()
        elif self.bank_db.get_machine_cash('Hoppers') > 0:
            change_led.flash(1)
        else:
            change_led.off()

    def handle_munch_led(self):
        munch_led = self.devices['munch_led']

        while True:
            if self.devices['coin_muncher'].motor_on:
                munch_led.flash(0.3)
            elif self.sm.current == 'user':
                munch_led.flash(2)
            else:
                munch_led.off()

            time.sleep(0.25)
    
    def handle_dispenser_led(self):
        dispenser_led = self.devices['dispenser_led']

        while True:
            if self.devices['coin_dispenser'].motor_on:
                dispenser_led.flash(0.3)
                self.last_dispense_time = time.time()
            elif time.time() - self.last_dispense_time < 20:
                dispenser_led.flash(1)
            else:
                dispenser_led.off()

            time.sleep(0.25)
