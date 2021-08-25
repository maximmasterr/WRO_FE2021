import cv2
import numpy as np
import math
import time
import hardware
import atexit

ENABLE_MOTORS = True

direction_mode = False  # True - clockwise, False - counter clock wise

KP = 1.5
KD = 1
ROUNDER = 1
CW_POINT = 140
CCW_POINT = 140

LEFT90_MANEUVER = (-40, 5500)
RIGHT90_MANEUVER = (45, 5500)

RIGHT_WALL = (452, 4000)
LEFT_WALL = (0, 4000)

######################################################################################
######################################################################################
######################################################################################

errold = 0

atexit.register(hardware.close_all)


def maneuver(angle, encoder_ticks):
    hardware.steer(angle)
    start_tick = hardware.read_encoder()
    cnt = 0
    while True:
        if ENABLE_MOTORS:
            hardware.forward()
        time.sleep(0.07)
        current_tick = hardware.read_encoder()
        print(abs(current_tick - start_tick))
        if cnt == 0:
            hardware.get_frame()
        cnt = (cnt + 1) % 10

        if abs(current_tick - start_tick) > encoder_ticks:
            hardware.get_frame()
            break
    # hardware.stop_center()


def binarize(img, bin_min, bin_max):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bin_image = cv2.inRange(hsv, bin_min, bin_max)
    bin_image = cv2.erode(bin_image, None, iterations=4)
    bin_image = cv2.dilate(bin_image, None, iterations=4)

    return bin_image


def get_contour_params(cnt):
    M = cv2.moments(cnt)
    area = M['m00']
    cx = int(M['m10'] / area)
    cy = int(M['m01'] / area)

    return area, cx, cy


def detect_object(name, img, bin_min, bin_max, area_min, show=True):
    contour = None
    area, cx, cy = (None, None, None)

    binarized = binarize(img, bin_min, bin_max)
    debug = cv2.cvtColor(binarized, cv2.COLOR_GRAY2BGR)

    contours = cv2.findContours(binarized, cv2.RETR_TREE,
                                cv2.CHAIN_APPROX_NONE)[0]

    if len(contours) > 0:
        cv2.drawContours(debug, contours, -1, (0, 255, 0), 1)
        contours = list(
            filter(lambda c: cv2.contourArea(c) > area_min, contours))

        if len(contours) > 0:
            cv2.drawContours(debug, contours, -1, (0, 255, 0), 3)

            contour = max(contours, key=cv2.contourArea)
            area, cx, cy = get_contour_params(contour)

            cv2.drawContours(debug, [contour], -1, (0, 0, 255), 3)
            cv2.circle(debug, (cx, cy), 5, (0, 0, 255), -1)
    if show:
        cv2.imshow(name, debug)
    return contour, (area, cx, cy)


WALL_MODE_LEFT = False
WALL_MODE_RIGHT = True
wall_mode = WALL_MODE_RIGHT
distance = 740

current_point = 0


def find_wall(img, mode):
    if mode:
        img = img[120:280, :80]
    else:
        img = img[120:280, -80:]

    binarized = binarize(img=img, bin_min=(0, 0, 0), bin_max=(255, 160, 100))

    debug = cv2.cvtColor(binarized, cv2.COLOR_GRAY2BGR)

    lowest_points = np.argmax(binarized[::-1], axis=0)
    lowest_point = binarized.shape[0] - np.average(lowest_points)

    cv2.line(debug, (0, int(lowest_point)), (80, int(lowest_point)),
             (0, 255, 0), 2)
    cv2.imshow("Wall", debug)

    return lowest_point


def wall(img):
    lowest_point = find_wall(img, direction_mode)

    global errold
    print(lowest_point)
    err = lowest_point - current_point
    u = KP * err + KD * (err - errold)
    errold = err

    hardware.steer(u if direction_mode else -u)


def normalize(img):
    img = img.copy()
    for i in range(3):
        normalization = img[:, :, i]
        mi = np.min(normalization)
        ma = np.max(normalization)

        im = img[:, :, i].astype(np.float32) - mi
        im /= ma - mi
        im = np.clip(im, 0, 1)
        img[:, :, i] = (im * 255).astype(np.uint8)
    cv2.imshow("NORMALIZED", img)
    return img


has_rotated = False
"""
object_name = detect_object(name="object_name",
                            img=img[74:187, 2:72],
                            bin_min=(0, 0, 0),
                            bin_max=(255, 255, 32),
                            area_min=0)
"""
cw_conf, ccw_conf = 0, 0
for i in range(5):

    flag, img = hardware.get_frame()
    cw_conf += find_wall(img, True)
    ccw_conf += find_wall(img, False)
    cv2.waitKey(10)
print(cw_conf, ccw_conf)
# direction_mode = cw_conf > ccw_conf
time.sleep(1)

while True:
    start_time = time.time()
    flag, img = hardware.get_frame()
    # img = cv2.flip(img, 1)
    # if not flag: break

    red_marker = detect_object(name="red_marker",
                               img=img[210:384, 0:171],
                               bin_min=(0, 80, 100),
                               bin_max=(255, 255, 255),
                               area_min=100)

    green_marker = detect_object(name="green_marker",
                                 img=img[239:384, 272:512],
                                 bin_min=(47, 168, 50),
                                 bin_max=(96, 255, 252),
                                 area_min=100)

    # if green[0] is not None:
    #     print(green[1])

    # blue_line_stop = blue_line[0] is not None
    # print(wall_forward)
    if red_marker[0] is not None:
        point_shift = -10
    elif green_marker[0] is not None:
        point_shift = +10
    else:
        point_shift = 0

    if direction_mode:
        current_point = CW_POINT + point_shift

    else:
        current_point = CCW_POINT - point_shift

    # if 0 == 0:
    wall(img)
    if ENABLE_MOTORS:
        hardware.forward()
    print("STATUS: RIDING_WALL")

    flag, img = hardware.get_frame()
    main_line = detect_object(name="main_line",
                              img=normalize(img[320:, ])[:, 200:240],
                              bin_min=(0, 50, 50),
                              bin_max=(255, 255, 255),
                              area_min=20)

    if main_line[0] is not None:
        print('Wowo!')
        if direction_mode:
            maneuver(*RIGHT90_MANEUVER)
        else:
            maneuver(*LEFT90_MANEUVER)
        # hardware.stop_center()
        for i in range(10):
            flag, img = hardware.get_frame()
            # cv2.waitKey(1)
        main_line = [None, None]
        # exit()

    ch = cv2.waitKey(5)
    if ch == 27:
        break

    print("Frame took:", time.time() - start_time)
