#!/usr/bin/env python3
"""Read-only: dump every controllable component's DOF, joint names, limits, current pos."""
import numpy as np
from dexcontrol.robot import Robot

robot = Robot()
try:
    for name in ["torso", "left_arm", "right_arm", "head", "chassis"]:
        if not robot.has_component(name):
            print("\n=== %s: NOT PRESENT ===" % name)
            continue
        c = getattr(robot, name)
        print("\n=== %s ===" % name)
        for attr in ("joint_name", "_joint_name", "joint_names"):
            if hasattr(c, attr):
                print("  joint_name:", getattr(c, attr))
                break
        try:
            pos = np.asarray(c.get_joint_pos(), dtype=float)
            print("  dof:", pos.size)
            print("  cur:", np.round(pos, 4).tolist())
        except Exception as e:
            print("  get_joint_pos failed:", e)
        try:
            lim = np.asarray(c.joint_pos_limit, dtype=float)
            print("  limits:")
            for i, (lo, hi) in enumerate(lim):
                print("    j%d: [%+.4f, %+.4f]" % (i + 1, lo, hi))
        except Exception as e:
            print("  joint_pos_limit failed:", e)
        for pn in ("pose_pool", "_pose_pool"):
            if hasattr(c, pn):
                try:
                    print("  poses:", list(getattr(c, pn).keys()))
                except Exception:
                    pass
                break
finally:
    robot.shutdown()
