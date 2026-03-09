# import RPi.GPIO as GPIO
# import time

# TRIG = 23
# ECHO = 24
# THRESHOLD_CM = 20
# COOLDOWN = 3
# TIMEOUT = 0.05  # 50 ms timeout for pulse

# GPIO.setmode(GPIO.BCM)
# GPIO.setup(TRIG, GPIO.OUT)
# GPIO.setup(ECHO, GPIO.IN)

# def get_distance():
#     # Send 10 µs trigger pulse
#     GPIO.output(TRIG, True)
#     time.sleep(0.00001)
#     GPIO.output(TRIG, False)

#     start_time = time.time()
#     timeout_time = start_time + TIMEOUT

    
#     while GPIO.input(ECHO) == 0 and time.time() < timeout_time:
#         start = time.time()
#     if time.time() >= timeout_time:
#         return None  # timeout happened

#     timeout_time = time.time() + TIMEOUT

#     # Wait for ECHO to go LOW
#     while GPIO.input(ECHO) == 1 and time.time() < timeout_time:
#         end = time.time()
#     if time.time() >= timeout_time:
#         return None  # timeout happened

#     duration = end - start
#     distance = duration * 17150
#     return distance

# last_trigger_time = 0

# try:
#     while True:
#         dist = get_distance()

#         if dist is not None:
#             print(f"Distance: {dist:.1f} cm")

#             if dist < THRESHOLD_CM and (time.time() - last_trigger_time > COOLDOWN):
#                 print("Hello. Welcome to Utpal Shanghvi Global School")
#                 last_trigger_time = time.time()

#         else:
#             print("No echo detected")

#         time.sleep(0.3)

# except KeyboardInterrupt:
#     pass

# finally:
#     GPIO.cleanup()
import RPi.GPIO as GPIO
import time
import os

TRIG = 23
ECHO = 24
THRESHOLD_CM = 20
COOLDOWN = 3
TIMEOUT = 10  # 50 ms timeout for pulse

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    # Send 10 µs trigger pulse
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start_time = time.time()
    timeout_time = start_time + TIMEOUT

    while GPIO.input(ECHO) == 0 and time.time() < timeout_time:
        start = time.time()
    if time.time() >= timeout_time:
        return None

    timeout_time = time.time() + TIMEOUT

    while GPIO.input(ECHO) == 1 and time.time() < timeout_time:
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

                # Play your welcome.wav file
                os.system("aplay Namaste_hindi.wav")

                last_trigger_time = time.time()

        else:
            print("No echo detected")

        time.sleep(0.3)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
