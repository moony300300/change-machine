from interfaces.gpio_manager import GPIOManager
import threading
import time

class LED:
    def __init__(self, pin_name):
        self.pin = pin_name
        self._mode = "off"
        self._interval = 1.0
        self._running = True

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def on(self):
        if self._mode == "on":
            return
        self._mode = "on"
        print("[LED] on")

    def off(self):
        if self._mode == "off":
            return
        self._mode = "off"
        print("[LED] off")

    def flash(self, interval):
        if self._mode == "flash" and self._interval == interval:
            return
        self._mode = "flash"
        self._interval = interval
        print("[LED] flash", interval)

    def _loop(self):
        while self._running:
            if self._mode == "on":
                GPIOManager.on(self.pin)
                time.sleep(0.1)

            elif self._mode == "off":
                GPIOManager.off(self.pin)
                time.sleep(0.1)

            elif self._mode == "flash":
                GPIOManager.on(self.pin)
                time.sleep(self._interval)
                GPIOManager.off(self.pin)
                time.sleep(self._interval)

