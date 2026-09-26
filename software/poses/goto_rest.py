#!/usr/bin/env python3
"""Manipulation-ready pose -> rest pose.

    python3 goto_rest.py [--dry-run] [--step 0.04] [--wait 0.8] [--min-sep 0.35]

Moves the LEFT arm first, then the right. For this direction the minimum wrist
separation along the path is

    concurrent   0.267 m   <- REFUSED by the clearance guard, and closer than the
                              0.31 m that broke a gripper cable on 2026-09-07
    right-first  0.434 m
    left-first   0.459 m   <- used here

so the order matters far more here than the target pose does: both endpoints are
safe, the danger only exists mid-path when the two arms move at once.

Flags you pass win over the defaults, because goto_pose reads the first occurrence.
"""
import sys

import goto_pose

POSE = "pre_move"
DEFAULTS = ["--seq", "left", "--step", "0.04", "--wait", "0.8"]

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + sys.argv[1:] + [POSE] + DEFAULTS
    goto_pose.main()
