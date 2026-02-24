import RPi.GPIO as GPIO
import atexit
import signal
import sys

from config.gpio_pins import (
    GPIO_PINS,
    GPIO_OUTPUTS,
    GPIO_INPUTS,
    GPIO_INVERTED,
)

class GPIOManager:
    _initialized = False

    @classmethod
    def init(cls):
        if cls._initialized:
            return

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Configure OUTPUTS
        for name in GPIO_OUTPUTS:
            pin = GPIO_PINS[name]

            # OFF means logical off → handle inversion
            initial = GPIO.HIGH if name in GPIO_INVERTED else GPIO.LOW

            GPIO.setup(pin, GPIO.OUT, initial=initial)
            print(f"[GPIO] {name} ({pin}) OUTPUT OFF")

        # Configure INPUTS
        for name in GPIO_INPUTS:
            pin = GPIO_PINS[name]
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            print(f"[GPIO] {name} ({pin}) INPUT")

        cls._initialized = True

        atexit.register(cls.shutdown)
        signal.signal(signal.SIGINT, cls.shutdown)
        signal.signal(signal.SIGTERM, cls.shutdown)

    # ---------- LOGICAL API ----------

    @classmethod
    def on(cls, name):
        pin = GPIO_PINS[name]
        GPIO.output(pin, GPIO.LOW if name in GPIO_INVERTED else GPIO.HIGH)

    @classmethod
    def off(cls, name):
        pin = GPIO_PINS[name]
        GPIO.output(pin, GPIO.HIGH if name in GPIO_INVERTED else GPIO.LOW)

    @classmethod
    def read(cls, name):
        """
        Returns logical sensor state:
        True  = ACTIVE
        False = INACTIVE
        """
        value = GPIO.input(GPIO_PINS[name])
        return not value if name in GPIO_INVERTED else bool(value)

    # ---------- SAFE SHUTDOWN ----------

    @classmethod
    def shutdown(cls, *args):
        print("\n[GPIO] Safe shutdown")

        for name in GPIO_OUTPUTS:
            try:
                cls.off(name)
                print(f"[GPIO] {name} -> OFF")
            except Exception:
                pass

        GPIO.cleanup()
        sys.exit(0)