#!/usr/bin/env python3
"""Rest pose -> manipulation-ready pose.

    python3 goto_ready.py [--dry-run] [--step 0.04] [--wait 0.8] [--min-sep 0.35]

Moves the RIGHT arm first, then the left. That order is not cosmetic. For this pair of
poses the minimum wrist separation along the path is

    concurrent   0.354 m
    left-first   0.431 m
    right-first  0.459 m   <- used here

The grippers stick out past the wrists and are absent from vega_1u.urdf, so no
URDF collision check can see them; keeping the wrists far apart is the only guard.
Use goto_rest.py for the return trip - it prefers the opposite order.

The head defaults to the calibrated tabletop-camera view (radians).
Explicit --head or --head-rad options override that default.
Flags you pass win over the defaults, because goto_pose reads the first occurrence.
"""
import sys

import goto_pose

POSE = "brickbench_home"
HEAD_RAD = "-0.00017453292093705386,-0.00017453292093705386,-0.5056219100952148"
DEFAULTS = ["--seq", "right", "--step", "0.04", "--wait", "0.8",
            "--head-rad", HEAD_RAD]

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + sys.argv[1:] + [POSE] + DEFAULTS
    goto_pose.main()
