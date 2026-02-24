from interfaces.hopper import CoinHopper
from interfaces.led_light import LED
import time
import threading

balance = 5
lock = threading.Lock()

def coin_input(amount):
    global balance
    balance += amount
    print(f"[TOP] Coin detected: £{amount:.2f} | Balance: £{balance:.2f}")

def coin_output(amount):
    global balance
    balance -= amount
    print(f"[BOTTOM] Coin detected: £{amount:.2f} | Balance: £{balance:.2f}")


def on_low_level_top(is_low):
    if is_low:
        print("⚠️ LOW LEVEL DETECTED")
    else:
        print("✅ HOPPER REFILLED")
        top_hopper.on()

def hopper_watchdog():
    while True:
        time.sleep(0.5)

        with lock:
            if top_hopper.motor_on:
                time_since = top_hopper.get_time_since_last_coin()
                print(time_since)
                if time_since == None:
                    print("[TOP] Hopper not on")
                elif time_since > 5:
                    top_hopper.off()
                    print("[TOP] 5 Second since last coin, switching off")


# GPIO pins: motor, coin sensor, low-level sensor
top_hopper = CoinHopper(
    motor_pin=17,
    coin_sensor_pin=27,
    low_level_pin=22,
    pulse_callback=coin_input,
    coin_value=0.02
)

top_hopper.set_low_level_callback(on_low_level_top)

threading.Thread(target=hopper_watchdog, daemon=True).start()

bottom_hopper = CoinHopper(
    motor_pin=14,
    coin_sensor_pin=12,
    low_level_pin=4,
    pulse_callback=coin_output,
    coin_value=0.02
)

#print("Bottom hopper hardware test running")
#bottom_hopper.on()
#time.sleep(3)
#bottom_hopper.off()
#print("Bottom hopper hardware test complete")

print("Top hopper hardware test running")
#top_hopper.on()
#time.sleep(10)
#top_hopper.off()
#print("Top hopper hardware test complete")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping...")
    top_hopper.stop()
    bottom_hopper.stop()
