from pirc522 import RFID
from time import sleep
import RPi.GPIO as GPIO
import threading

class RFIDReader:
    def __init__(self, callback, bus=1, device=2, pin_rst=13):
        """
        callback: function to call when an RFID tag is scanned (passes rfid string)
        """
        self.callback = callback
        self.running = False
        self.rdr = RFID(bus=bus, device=device, pin_rst=pin_rst, pin_irq=None, pin_mode=GPIO.BCM)

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self._scan_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _scan_loop(self):
        while self.running:
            error, _ = self.rdr.request()
            if not error:
                error, uid = self.rdr.anticoll()
                if not error:
                    rfid = "-".join(map(str, uid))
                    print("[RFID] Detected RFID with UID:", rfid)
                    self.callback(rfid)
                    sleep(0.5)  # short delay to avoid double-reads
            sleep(0.1)
