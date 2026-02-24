import spidev
import time
import RPi.GPIO as GPIO

RST_PIN = 13  # GPIO13 (physical pin 33)

GPIO.setmode(GPIO.BCM)
GPIO.setup(RST_PIN, GPIO.OUT)

spi = spidev.SpiDev()
spi.open(1, 2)
spi.max_speed_hz = 1000000

def reset_rc522():
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.1)

def read_register(addr):
    return spi.xfer2([addr << 1 | 0x80, 0])[1]

try:
    while True:
        reset_rc522()
        time.sleep(0.2)
        version = read_register(0x37)
        if version == 0x91 or version == 0x92:
            print(f"✅ RC522 detected: Version 0x{version:02X}")
        else:
            print(f"❌ No RC522 detected: Version 0x{version:02X}")
        time.sleep(1)

except KeyboardInterrupt:
    spi.close()
    GPIO.cleanup()
