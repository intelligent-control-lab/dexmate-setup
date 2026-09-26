#!/usr/bin/env python3
"""Drive the Vega-1U to BrickBench's Joint_Home_Position.

The config vector is 23 long; vega_1u exposes only left_arm(7) + right_arm(7) + head(3).
Mapping used (indices into the flat 23-vector):

    [0:2]   torso / lift        -> NOT PRESENT on vega_1u, skipped
    [2:9]   left_arm  j1..j7
    [9:11]  left gripper        -> not a dexcontrol component here, skipped
    [11:18] right_arm j1..j7
    [18:20] right gripper       -> skipped
    [20:23] head j1..j3

Run with --dry-run to only print the plan and the limit check.
"""
import sys
import time

import numpy as np
from dexcontrol.robot import Robot

JOINT_HOME = [
    0.2, 0.5,
    0, 1.2, 1.4, -1.57, -1.57, 1, -0.35, 0.2, 0,
    0, -1.2, -1.4, -1.57, 1.57, -1, 0.35, 0.2, 0,
    0, 0, 0,
]

TARGETS = {
    "left_arm": JOINT_HOME[2:9],
    "right_arm": JOINT_HOME[11:18],
    "head": JOINT_HOME[20:23],
}

ARM_STEP = 0.12      # rad per joint per iteration
HEAD_STEP = 0.10
TOL = 0.02
MARGIN = 0.02        # keep this far off a hard limit
WAIT = 0.6


def plan(comp, goal):
    cur = np.asarray(comp.get_joint_pos(), dtype=float)
    goal = np.asarray(goal, dtype=float)
    lim = np.asarray(comp.joint_pos_limit, dtype=float)
    lo, hi = lim[:, 0] + MARGIN, lim[:, 1] - MARGIN
    clipped = np.clip(goal, lo, hi)
    return cur, goal, clipped, lim


def report(name, cur, goal, clipped, lim):
    print("\n=== %s ===" % name)
    bad = False
    for i in range(len(goal)):
        note = "OK"
        if abs(clipped[i] - goal[i]) > 1e-9:
            note = "*** OUT OF RANGE -> clipped to %+.3f ***" % clipped[i]
            bad = True
        print("  j%d: cur %+.4f -> goal %+.4f   (delta %+.4f)  "
              "limits [%+.3f, %+.3f]  %s"
              % (i + 1, cur[i], goal[i], goal[i] - cur[i], lim[i, 0], lim[i, 1], note))
    print("  max |delta| = %.4f rad (%.1f deg)"
          % (np.max(np.abs(goal - cur)), np.degrees(np.max(np.abs(goal - cur)))))
    return bad


def step_to(comps, goals, step):
    """Interpolate all given components toward their goals together."""
    while True:
        done = True
        for name, comp in comps.items():
            cur = np.asarray(comp.get_joint_pos(), dtype=float)
            goal = goals[name]
            err = goal - cur
            if np.max(np.abs(err)) > TOL:
                done = False
                target = cur + np.clip(err, -step, step)
                comp.set_joint_pos(target, wait_time=0.0)
        if done:
            return
        time.sleep(WAIT)


def main():
    dry = "--dry-run" in sys.argv
    robot = Robot()
    try:
        comps, goals, any_bad = {}, {}, False
        for name, goal in TARGETS.items():
            if not robot.has_component(name):
                print("\n=== %s: NOT PRESENT, skipping ===" % name)
                continue
            comp = getattr(robot, name)
            cur, goal_a, clipped, lim = plan(comp, goal)
            any_bad |= report(name, cur, goal_a, clipped, lim)
            comps[name] = comp
            goals[name] = clipped

        print("\nSkipped (no such component on vega_1u): "
              "vector[0:2]=%s, left gripper vector[9:11]=%s, "
              "right gripper vector[18:20]=%s"
              % (JOINT_HOME[0:2], JOINT_HOME[9:11], JOINT_HOME[18:20]))

        if dry:
            print("\nDRY RUN - nothing was commanded.")
            return

        print("\nMoving arms (both together, %.2f rad/step)..." % ARM_STEP)
        arms = {k: v for k, v in comps.items() if k.endswith("_arm")}
        step_to(arms, {k: goals[k] for k in arms}, ARM_STEP)

        if "head" in comps:
            print("Moving head (%.2f rad/step)..." % HEAD_STEP)
            step_to({"head": comps["head"]}, {"head": goals["head"]}, HEAD_STEP)

        print("\n=== final ===")
        for name, comp in comps.items():
            fin = np.asarray(comp.get_joint_pos(), dtype=float)
            err = np.max(np.abs(fin - goals[name]))
            print("  %-10s %s   max err %.4f"
                  % (name, np.round(fin, 4).tolist(), err))
    finally:
        robot.shutdown()


if __name__ == "__main__":
    main()
