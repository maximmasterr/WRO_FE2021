from config import ENABLE_MOTORS
import hardware
import time
from marker import find_main_marker

def maneuver(angle, encoder_ticks):
    if not ENABLE_MOTORS:
        return

    hardware.steer(angle)
    start_tick = hardware.read_encoder()
    cnt = 0
    while hardware.wait_button():
        if ENABLE_MOTORS:
            hardware.forward()
        time.sleep(0.07)
        current_tick = hardware.read_encoder()
        
        #### BETA BETA BETA Unteseted
        img, flag = hardware.get_frame()
        find_main_marker(img)
        
        if abs(current_tick - start_tick) > encoder_ticks:
            hardware.get_frame()
            break

def complex_maneuver(forward, angle, encoder_ticks):
    if forward > 0:
        maneuver(0, forward)
    maneuver(angle, encoder_ticks)