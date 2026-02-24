from interfaces.gpio_manager import GPIOManager
from kivy.app import App
import time
import threading
import queue

class CoinHopper:
    TIMEOUT_SECONDS = 5
    BATCH_TIMEOUT = 0.5  # seconds without pulses = batch complete

    def __init__(self, motor_pin, coin_sensor_pin, low_level_pin,
                 pulse_callback, coin_value=0.02):
        self.motor_pin = motor_pin
        self.coin_sensor_pin = coin_sensor_pin
        self.low_level_pin = low_level_pin
        self.pulse_callback = pulse_callback
        self.coin_value = coin_value

        self.running = True
        self.motor_on = False

        self.coins_withdrawing = False
        self.target_amount = 0
        self.total_withdrawn = 0
        self.last_coin_time = None

        self.last_coin_state = GPIOManager.read(self.coin_sensor_pin)
        self.last_low_state = GPIOManager.read(self.low_level_pin)

        self.low_level_callback = None
        self.error_callback = None

        self.withdraw_queue = queue.Queue()
        self.pulse_queue = queue.Queue()

        threading.Thread(target=self._run, daemon=True).start()
        threading.Thread(target=self._pulse_worker, daemon=True).start()
        threading.Thread(target=self._low_level_watch, daemon=True).start()
        threading.Thread(target=self._withdraw_worker, daemon=True).start()
        threading.Thread(target=self._munch_watchdog, daemon=True).start()


    # ─────────────────────────────
    # Public API
    # ─────────────────────────────

    def withdraw_coins(self, amount):
        """Queue a withdrawal request."""
        self.withdraw_queue.put(amount)

    def get_low_level_state(self):
        if self.motor_on:
            return True
        else:
            return GPIOManager.read(self.low_level_pin)

    def set_low_level_callback(self, callback):
        self.low_level_callback = callback

    def set_error_callback(self, callback):
        self.error_callback = callback

    # ─────────────────────────────
    # Motor control
    # ─────────────────────────────

    def on(self):
        GPIOManager.on(self.motor_pin)
        self.motor_on = True
        self.last_coin_time = time.time()

    def off(self):
        GPIOManager.off(self.motor_pin)
        self.motor_on = False
        self.last_coin_time = None

    # ─────────────────────────────
    # Workers
    # ─────────────────────────────

    def _withdraw_worker(self):
        """Processes queued withdrawals one at a time."""
        while self.running:
            try:
                amount = self.withdraw_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # --- Safety checks ---
            if not self.get_low_level_state():
                self._error("Hopper empty")
                continue

            app = App.get_running_app()
            if app.bank_db.get_machine_cash("Hoppers") < 1.0:
                self._error("Machine hopper balance low")
                continue

            # --- Begin withdrawal ---
            self.target_amount = amount
            print(f"[Coin Hopper] Starting worker withdrawing £{amount}")
            self.total_withdrawn = 0
            self.coins_withdrawing = True
            self.on()

            # Wait until finished or aborted
            while self.coins_withdrawing and self.running:
                # Timeout check
                if self.last_coin_time and time.time() - self.last_coin_time > self.TIMEOUT_SECONDS:
                    self._error("Coin dispense timeout")
                    self.coins_withdrawing = False
                    break

                time.sleep(0.05)
            
            self.off()
            print("[Coin Hopper] Worker finished")


    def _run(self):
        """Monitors coin pulses."""
        while self.running:
            current_state = GPIOManager.read(self.coin_sensor_pin)

            if self.last_coin_state and not current_state:
                self.pulse_queue.put(self.coin_value)
                self.last_coin_time = time.time()

                if self.coins_withdrawing:
                    self.total_withdrawn += self.coin_value
                    if self.total_withdrawn >= self.target_amount:
                        self.coins_withdrawing = False

            self.last_coin_state = current_state
            time.sleep(0.001)

    def _pulse_worker(self):
        while self.running:
            try:
                value = self.pulse_queue.get(timeout=0.1)
                self.pulse_callback(value)
            except queue.Empty:
                continue

    def _low_level_watch(self):
        while self.running:
            current_state = GPIOManager.read(self.low_level_pin)
            if current_state != self.last_low_state:
                self.last_low_state = current_state
                if self.low_level_callback and not self.motor_on:
                    self.low_level_callback(current_state)
            time.sleep(0.001)

    def _munch_watchdog(self):
        """Automatically stop motor if no coins detected for TIMEOUT_SECONDS."""
        while self.running:
            if self.motor_on and not self.coins_withdrawing:  # Only for munching mode
                if self.last_coin_time:
                    elapsed = time.time() - self.last_coin_time
                    if elapsed > self.TIMEOUT_SECONDS:
                        self.off()  # Stop motor, no error for munching
            time.sleep(0.1)

    # ─────────────────────────────
    # Error handling
    # ─────────────────────────────

    def _error(self, message):
        if self.error_callback:
            self.error_callback(message)

    def stop(self):
        self.running = False
        self.off()
