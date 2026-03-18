import lgpio
import time
import os

TRIG = 23
ECHO = 24
THRESHOLD_CM = 20
COOLDOWN = 3
TIMEOUT = 0.05  # 50 ms timeout for pulse

h = lgpio.gpiochip_open(0)
# lgpio.gpio_free(h, TRIG)   # free first
# lgpio.gpio_free(h, ECHO)
lgpio.gpio_claim_output(h, TRIG)
lgpio.gpio_claim_input(h, ECHO)

def get_distance():
    # Send 10 µs trigger pulse
    lgpio.gpio_write(h, TRIG, 1)
    time.sleep(0.00001)
    lgpio.gpio_write(h, TRIG, 0)

    # Initialize start and end to avoid UnboundLocalError
    start = time.time()
    end = time.time()

    timeout_time = time.time() + TIMEOUT
    while lgpio.gpio_read(h, ECHO) == 0 and time.time() < timeout_time:
        start = time.time()
    if time.time() >= timeout_time:
        return None

    timeout_time = time.time() + TIMEOUT
    while lgpio.gpio_read(h, ECHO) == 1 and time.time() < timeout_time:
        end = time.time()
    if time.time() >= timeout_time:
        return None

    duration = end - start
    distance = duration * 17150
    return distance

last_trigger_time = 0
try:
    while True:
        dist = get_distance()
        if dist is not None:
            print(f"Distance: {dist:.1f} cm")
            if dist < THRESHOLD_CM and (time.time() - last_trigger_time > COOLDOWN):
                print("Playing welcome.wav...")
                os.system("aplay Namaste.wav")
                last_trigger_time = time.time()
        else:
            print("No echo detected")
        time.sleep(0.3)
except KeyboardInterrupt:
    pass
finally:
    lgpio.gpiochip_close(h)
