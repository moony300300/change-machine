from interfaces.gpio_manager import GPIOManager 
import time 
import threading
import queue

class CoinInserter: 
    INACTIVITY_TIMEOUT = 0.5 # seconds

    def __init__(self, pin_name, pulse_callback, coin_value=0.10): 
        """ pulse_callback: function to call when a batch of coins is detected coin_value: value of each coin detected (in £) """ 
        self.pin = pin_name 
        self.pulse_callback = pulse_callback 
        self.coin_value = coin_value 

        self.running = True 

        self.last_state = GPIOManager.read(self.pin) 

        self.pulse_queue = queue.Queue()

        threading.Thread(target=self._run, daemon=True).start() 
        threading.Thread(target=self._pulse_worker, daemon=True).start()

    def stop(self): 
        self.running = False

    # ───────────────────────────── 
    # Pulse detection 
    # ───────────────────────────── 
    def _run(self):
        """Monitors coin pulses."""
        while self.running:
            current_state = GPIOManager.read(self.pin)

            if self.last_state and not current_state:
                self.pulse_queue.put(self.coin_value)
                self.last_pulse_time = time.time()

            self.last_state = current_state
            time.sleep(0.01)

    def _pulse_worker(self):
        while self.running:
            try:
                value = self.pulse_queue.get(timeout=0.1)
                self.pulse_callback(value)
            except queue.Empty:
                continue