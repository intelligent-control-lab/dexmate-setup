#!/usr/bin/env python3
"""Sensor-only connection: subscribe to head_camera WITHOUT constructing Robot().

Robot() unconditionally runs _set_default_state(), which drives the head to its 'home'
pose. dexcontrol.sensors.manager.Sensors is the object Robot builds internally for
sensors (robot.py:_initialize_sensors does `self.sensors = Sensors(self._configs.sensors)`),
so building it directly gives the same camera API with no control topics touched at all.
"""
import sys
import time

import numpy as np
import cv2

from dexcontrol.core.config import get_robot_config
from dexcontrol.sensors.manager import Sensors

OUT_PNG = sys.argv[1] if len(sys.argv) > 1 else "/home/dexmate/sensor_only_left.png"

configs = get_robot_config()
configs.sensors["head_camera"].enabled = True

sensors = Sensors(configs.sensors)
try:
    sensors.wait_for_all_active()
    cam = sensors.head_camera

    info = cam.get_camera_info()
    act = info.get("actual", {}) if isinstance(info, dict) else {}
    left = info.get("intrinsics", {}).get("left", {}) if isinstance(info, dict) else {}
    print("actual     :", act)
    print("serial     :", info.get("serial_number") if isinstance(info, dict) else "?")
    print("left fx,fy :", left.get("fx"), left.get("fy"))
    print("left cx,cy :", left.get("cx"), left.get("cy"))
    print("distortion :", left.get("distortion"))

    img = None
    for _ in range(30):
        img = cam.get_obs(obs_keys=["left_rgb"]).get("left_rgb")
        if img is not None:
            break
        time.sleep(1)
    if img is None:
        print("no frame")
    else:
        a = np.asarray(img)
        print("frame shape:", a.shape, a.dtype)
        cv2.imwrite(OUT_PNG, cv2.cvtColor(a[:, :, :3].astype(np.uint8), cv2.COLOR_RGB2BGR))
        print("wrote", OUT_PNG)
finally:
    sensors.shutdown()
    print("sensors shut down; no control topic was ever published")
