from interfaces.gpio_manager import GPIOManager 
import time 
import threading
import queue
from kivy.clock import Clock

class CoinInserter: 
    INACTIVITY_TIMEOUT = 0.5 # seconds

    def __init__(self, input_pin_name, output_pin_name, pulse_callback, coin_value=0.10): 
        """ pulse_callback: function to call when a batch of coins is detected coin_value: value of each coin detected (in £) """ 
        self.input_pin = input_pin_name
        self.output_pin = output_pin_name 
        self.pulse_callback = pulse_callback
        self.coin_value = coin_value

        self.stop()

        self.last_state = GPIOManager.read(self.input_pin) 

        self.pulse_queue = queue.Queue()

    def stop(self): 
        GPIOManager.off(self.output_pin)
        self.running = False

    def start(self):
        GPIOManager.on(self.output_pin)
        self.running = True

        if not hasattr(self, 'run_thread') or not self.run_thread.is_alive():
            self.run_thread = threading.Thread(target=self._run, daemon=True)
            self.run_thread.start()

        if not hasattr(self, 'pulse_thread') or not self.pulse_thread.is_alive():
            self.pulse_thread = threading.Thread(target=self._pulse_worker, daemon=True)
            self.pulse_thread.start()

    # ───────────────────────────── 
    # Pulse detection 
    # ───────────────────────────── 
    def _run(self):
        """Monitors coin pulses."""
        while self.running:
            current_state = GPIOManager.read(self.input_pin)

            if self.last_state and not current_state:
                self.pulse_queue.put(self.coin_value)
                self.last_pulse_time = time.time()

            self.last_state = current_state
            time.sleep(0.01)

    def _pulse_worker(self):
        while self.running:
            try:
                value = self.pulse_queue.get(timeout=0.1)
                Clock.schedule_once(lambda dt: self.pulse_callback(value))
            except queue.Empty:
                continue