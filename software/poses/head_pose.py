#!/usr/bin/env python3
"""Head joint-state read and smooth move for the Vega-1U.

Why this exists: dexcontrol's Robot() has no option to skip its startup homing.
Robot.__init__(self, configs=None, auto_shutdown=True) takes no such flag, and
_safe_initialize_components() runs a hardcoded step list whose last entry is
("default state", self._set_default_state); _set_default_state() then does

    head.set_mode("enable")
    home_pos = head.get_predefined_pose("home")      # [0.0, 0.0, 0.0]
    home_pos = self.compensate_torso_pitch(home_pos, "head")
    head.set_joint_pos(home_pos)

unconditionally, unless the software E-Stop is active. So every Robot() drives the
head to home, and any pose you want must be re-applied afterwards, in that session.

Measured behaviour:
  * within a live session the head holds a commanded pitch exactly (j3 = -0.5056
    unchanged over 25 s with no further commands)
  * after the owning process exits it relaxes from -0.5056 to about -0.13 rad,
    so the pose does NOT survive process exit and must be re-applied.
"""
import time

import numpy as np

HEAD_HOME = [0.0, 0.0, 0.0]
TARGET = [0.0, 0.0, -0.5056]      # j1 pitch, j2 yaw, j3 pitch (negative = look down)


def read_head_joint_pos(robot):
    """Current head joint positions as a float64 array [j1, j2, j3], radians.

    Returns a copy, so callers can mutate it safely.
    """
    return np.asarray(robot.head.get_joint_pos(), dtype=float).copy()


def read_head_limits(robot):
    """Head joint position limits as a (3, 2) array of [lower, upper], radians."""
    return np.asarray(robot.head.joint_pos_limit, dtype=float)


def move_head_smooth(robot, target, step=0.05, wait=0.4, tol=0.005,
                     margin=0.02, timeout=60.0, verbose=True):
    """Drive the head to `target` in small increments instead of one jump.

    Each iteration re-reads the measured position and commands at most `step`
    radians further, so the head tracks a ramp rather than being given a large
    step change. Targets are clipped inside the reported joint limits by `margin`.

    Args:
        robot:   a live dexcontrol Robot instance.
        target:  iterable of 3 joint angles [j1, j2, j3] in radians.
        step:    max radians commanded per joint per iteration.
        wait:    seconds between iterations.
        tol:     stop when every joint is within this of the goal.
        margin:  keep the goal this far inside each hard limit.
        timeout: give up after this many seconds.

    Returns:
        The final measured joint positions as a (3,) array.

    Raises:
        TimeoutError: if the head does not converge within `timeout`.
    """
    head = robot.head
    lim = read_head_limits(robot)
    goal = np.clip(np.asarray(target, dtype=float),
                   lim[:, 0] + margin, lim[:, 1] - margin)

    if verbose:
        cur = read_head_joint_pos(robot)
        print("head start : %s" % np.round(cur, 4).tolist())
        print("head goal  : %s" % np.round(goal, 4).tolist())
        for i in range(3):
            print("  j%d limits [%+.4f, %+.4f]" % (i + 1, lim[i, 0], lim[i, 1]))

    t0 = time.time()
    while True:
        cur = read_head_joint_pos(robot)
        err = goal - cur
        if np.max(np.abs(err)) <= tol:
            break
        if time.time() - t0 > timeout:
            raise TimeoutError(
                "head did not reach %s within %.0f s; stalled at %s"
                % (np.round(goal, 4).tolist(), timeout, np.round(cur, 4).tolist()))
        head.set_joint_pos(cur + np.clip(err, -step, step), wait_time=0.0)
        time.sleep(wait)

    fin = read_head_joint_pos(robot)
    if verbose:
        print("head final : %s   (max err %.4f, %.1f s)"
              % (np.round(fin, 4).tolist(), float(np.max(np.abs(fin - goal))),
                 time.time() - t0))
    return fin


if __name__ == "__main__":
    from dexcontrol.core.config import get_robot_config
    from dexcontrol.robot import Robot

    configs = get_robot_config()
    configs.sensors["head_camera"].enabled = True

    robot = Robot(configs=configs)          # this drives the head to home
    try:
        print("after Robot() init:", np.round(read_head_joint_pos(robot), 4).tolist())
        move_head_smooth(robot, TARGET)     # so re-apply the pose here

        # hold check: the pose stays put for as long as this session lives
        for t in (5, 10):
            time.sleep(5)
            print("hold t+%2ds j3=%+.4f" % (t, read_head_joint_pos(robot)[2]))

        # camera frames come from the same session, so the pose is guaranteed current
        img = robot.sensors.head_camera.get_obs(obs_keys=["left_rgb"]).get("left_rgb")
        print("frame:", None if img is None else np.asarray(img).shape)
    finally:
        robot.shutdown()
