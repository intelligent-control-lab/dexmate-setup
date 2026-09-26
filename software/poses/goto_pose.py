#!/usr/bin/env python3
"""Drive the Vega-1U arms (and optionally head) to a named pose, with limit clipping.

    python3 goto_pose.py pre_move [--head tucked | --head-rad J1,J2,J3] [--dry-run]

Named arm poses come from the robot's own pose_pool (get_predefined_pose), so the
right-arm sign flip is taken from the config rather than hardcoded. Extra poses
defined here:

    brickbench_home  BrickBench Joint_Home_Position, arm slots only
    pre_move         the pose recorded just before the first goto_home run

vega_1u has no torso/chassis, so nothing else is commandable.
"""
import sys
import time

import numpy as np
from dexcontrol.robot import Robot

EXTRA = {
    "brickbench_home": {
        "left_arm": [0, 1.2, 1.4, -1.57, -1.57, 1, -0.35],
        "right_arm": [0, -1.2, -1.4, -1.57, 1.57, -1, 0.35],
    },
    "pre_move": {
        "left_arm": [1.7289, 0.0101, 0.0041, -0.9924, -0.2311, 0.5011, -0.0066],
        "right_arm": [-1.5683, -0.0026, 0.0031, -0.9916, 0.0908, -0.4138, -0.0018],
    },
}

STEP = 0.12
TOL = 0.02
MARGIN = 0.02
WAIT = 0.6


# These tuck the forearm against the body and were designed around Dexmate's own end
# effectors. The third-party CAN grippers on this robot stick out past L_ee/R_ee and are
# absent from vega_1u.urdf, so the kinematic model cannot see the collision. One of these
# nearly damaged a gripper on 2026-09-07.
BANNED = {"folded", "folded_closed_hand"}


def resolve(robot, pose_name):
    """-> {component: goal array}, using pose_pool when the name is one of theirs."""
    if pose_name in BANNED:
        raise SystemExit(
            "refusing pose %r: it collides with the CAN grippers, which are not in the URDF"
            % pose_name)
    goals = {}
    if pose_name in EXTRA:
        for comp_name, vals in EXTRA[pose_name].items():
            goals[comp_name] = np.asarray(vals, dtype=float)
        return goals
    for comp_name in ("left_arm", "right_arm"):
        comp = getattr(robot, comp_name)
        goals[comp_name] = np.asarray(comp.get_predefined_pose(pose_name), dtype=float)
    return goals


def report(name, comp, goal):
    cur = np.asarray(comp.get_joint_pos(), dtype=float)
    lim = np.asarray(comp.joint_pos_limit, dtype=float)
    clipped = np.clip(goal, lim[:, 0] + MARGIN, lim[:, 1] - MARGIN)
    print("\n=== %s ===" % name)
    for i in range(len(goal)):
        note = ""
        if abs(clipped[i] - goal[i]) > 1e-9:
            note = "  <- clipped from %+.4f (limit %+.3f)" % (
                goal[i], lim[i, 0] if goal[i] < clipped[i] else lim[i, 1])
        print("  j%d: cur %+.4f -> %+.4f   (delta %+.4f)%s"
              % (i + 1, cur[i], clipped[i], clipped[i] - cur[i], note))
    print("  max |delta| = %.4f rad (%.1f deg)"
          % (np.max(np.abs(clipped - cur)), np.degrees(np.max(np.abs(clipped - cur)))))
    return clipped


def step_to(comps, goals, step):
    while True:
        done = True
        for name, comp in comps.items():
            cur = np.asarray(comp.get_joint_pos(), dtype=float)
            err = goals[name] - cur
            if np.max(np.abs(err)) > TOL:
                done = False
                comp.set_joint_pos(cur + np.clip(err, -step, step), wait_time=0.0)
        if done:
            return
        time.sleep(WAIT)


def calibrated_head_to(head, goal, *, step=0.025, wait=0.3, tolerance=0.001, timeout=60.):
    """Bounded head positioning with 0.001 rad arrival tolerance.

    This is a positioning check, not certification of camera calibration accuracy.
    Keep the exact calibrated target and require three consecutive in-tolerance reads.
    """
    goal = np.asarray(goal, dtype=float)
    limits = np.asarray(head.joint_pos_limit, dtype=float)
    if (goal.shape != (3,) or not np.isfinite(goal).all()
            or limits.shape != (3, 2) or not np.isfinite(limits).all()
            or np.any(goal < limits[:, 0] + MARGIN)
            or np.any(goal > limits[:, 1] - MARGIN)):
        raise ValueError("Calibrated head target must be finite and within limits with margin")
    deadline = time.monotonic() + timeout
    stable = 0
    current = None
    print(f'Head target rad={np.round(goal, 6).tolist()}, '
          f'arrival tolerance={tolerance:.3f} rad ({np.degrees(tolerance):.2f} deg)', flush=True)
    while time.monotonic() < deadline:
        current = np.asarray(head.get_joint_pos(), dtype=float)
        if (current.shape != (3,) or not np.isfinite(current).all()
                or np.any(current < limits[:, 0]) or np.any(current > limits[:, 1])):
            raise ValueError("Head feedback invalid or outside joint limits")
        error = goal - current
        reached = np.max(np.abs(error)) <= tolerance
        target = goal if reached else current + np.clip(error, -step, step)
        if np.any(target < limits[:, 0] + MARGIN) or np.any(target > limits[:, 1] - MARGIN):
            raise ValueError("Head intermediate target outside joint-limit margin")
        # This head controller does not advance toward a position target with
        # zero commanded velocity. Use bounded directional velocity while moving;
        # zero each settled axis and all axes once the target is reached.
        velocity = np.clip((target - current) / wait, -0.05, 0.05)
        velocity[np.abs(error) <= tolerance] = 0.0
        head.set_joint_pos_vel(target, velocity, relative=False, wait_time=0.0)
        stable = stable + 1 if reached else 0
        if stable >= 3:
            print(f'Head reached: measured rad={np.round(current, 6).tolist()}, '
                  f'error deg={np.round(np.degrees(error), 3).tolist()}', flush=True)
            return
        time.sleep(wait)
    details = ('no feedback sampled' if current is None else
               f'measured rad={np.round(current, 6).tolist()}, '
               f'error deg={np.round(np.degrees(goal - current), 3).tolist()}')
    raise TimeoutError(
        f'Head did not settle within {timeout:.1f} s: target rad={np.round(goal, 6).tolist()}, '
        f'{details}, tolerance={tolerance:.3f} rad, consecutive in-tolerance reads={stable}/3')


# ---------------------------------------------------------------- clearance guard
#
# The CAN grippers extend past L_ee / R_ee and are absent from vega_1u.urdf, so no
# URDF-based collision check can see them. Proxy: treat each gripper as a ball around
# its wrist and require the two wrist centres to stay apart. Calibration from real
# outcomes on this robot:
#     folded                        0.31 m  -> grippers crossed, broke a cable (2026-09-07)
#     pre_move <-> brickbench_home  0.364 m -> traversed twice, no contact (2026-09-07)
#     pre_move (endpoint)           0.44 m  -> fine
#     brickbench_home (endpoint)    0.66 m  -> fine
# So the real limit is between 0.31 (collides) and 0.364 (measured safe). 0.35 sits between
# them. This was 0.45 at first, set from endpoints alone, which wrongly refused the
# pre_move <-> brickbench_home transit; the 0.364 figure is the better evidence.
#
# CAVEAT: wrist-centre distance ignores orientation. Two poses at equal separation differ in
# whether the grippers actually point at each other - folded tucks both forearms inward so
# the jaws face off, which is worse than the number alone suggests. Treat this as a coarse
# screen, not a proof of clearance, and re-measure rather than loosening it further.
MIN_WRIST_SEP = 0.35

_ARM_J = {"left_arm": ["L_arm_j%d" % i for i in range(1, 8)],
          "right_arm": ["R_arm_j%d" % i for i in range(1, 8)]}


def _fk_setup():
    import pinocchio as pin
    from dexmate_urdf import robots
    model = pin.buildModelFromUrdf(str(robots.humanoid.vega_1u.vega_1u.urdf))
    data = model.createData()
    qidx = {n: model.joints[model.getJointId(n)].idx_q
            for n in _ARM_J["left_arm"] + _ARM_J["right_arm"]}
    return pin, model, data, qidx, model.getFrameId("L_ee"), model.getFrameId("R_ee")


def wrist_sep(pin, model, data, qidx, LF, RF, left, right):
    q = pin.neutral(model)
    for n, v in list(zip(_ARM_J["left_arm"], left)) + list(zip(_ARM_J["right_arm"], right)):
        q[qidx[n]] = v
    pin.forwardKinematics(model, data, q)
    pin.updateFramePlacements(model, data)
    return float(np.linalg.norm(data.oMf[LF].translation - data.oMf[RF].translation))


def simulate(cur, goal, step):
    """Replay step_to's exact per-joint clipping to get the real waypoint sequence."""
    pts, p = [cur.copy()], cur.copy()
    for _ in range(2000):
        err = goal - p
        if np.max(np.abs(err)) <= TOL:
            break
        p = p + np.clip(err, -step, step)
        pts.append(p.copy())
    return pts


def _schedule(lcur, rcur, goals, step, order):
    """Waypoint sequences the real move will visit, for concurrent or sequential motion.

    order=None moves both arms together; order=["left_arm", "right_arm"] ramps the left
    arm to its goal while the right holds, then the right while the left holds. Moving
    one arm at a time keeps the wrists much further apart on some paths - going from
    brickbench_home to pre_move, concurrent motion dips to 0.267 m while left-then-right
    never drops below 0.459 m.
    """
    lp = simulate(lcur, goals["left_arm"], step)
    rp = simulate(rcur, goals["right_arm"], step)
    if order is None:
        n = max(len(lp), len(rp))
        return lp + [lp[-1]] * (n - len(lp)), rp + [rp[-1]] * (n - len(rp))
    if order[0] == "left_arm":
        return lp + [lp[-1]] * len(rp), [rp[0]] * len(lp) + rp
    return [lp[0]] * len(rp) + lp, rp + [rp[-1]] * len(lp)


def check_path(comps, goals, step, order=None):
    """Refuse the move if the wrists ever come closer than MIN_WRIST_SEP along the way."""
    try:
        fk = _fk_setup()
    except Exception as e:
        raise SystemExit("Refusing motion: clearance check unavailable (%s)" % e)
    lcur = np.asarray(comps["left_arm"].get_joint_pos(), float)
    rcur = np.asarray(comps["right_arm"].get_joint_pos(), float)
    lp, rp = _schedule(lcur, rcur, goals, step, order)
    n = len(lp)

    seps = [wrist_sep(*fk, l, r) for l, r in zip(lp, rp)]
    worst = int(np.argmin(seps))
    print("\nwrist separation along path: start %.3f m, min %.3f m (waypoint %d/%d), "
          "end %.3f m  [limit %.2f]"
          % (seps[0], seps[worst], worst, n - 1, seps[-1], MIN_WRIST_SEP))
    if seps[worst] < MIN_WRIST_SEP:
        raise SystemExit(
            "REFUSING: wrists reach %.3f m at waypoint %d, below the %.2f m gripper "
            "clearance limit. The grippers are not in the URDF - this is the guard that "
            "catches what the model cannot see." % (seps[worst], worst, MIN_WRIST_SEP))


def main():
    global STEP, WAIT, MIN_WRIST_SEP
    dry = "--dry-run" in sys.argv
    # --seq left  : move the left arm to its goal first, then the right (and vice versa).
    # One arm at a time keeps the wrists far apart on paths where concurrent motion
    # brings them together; see _schedule().
    seq = None
    if "--seq" in sys.argv:
        seq = sys.argv[sys.argv.index("--seq") + 1]
        if seq not in ("left", "right"):
            raise SystemExit("--seq takes 'left' or 'right' (which arm moves first)")
    if "--min-sep" in sys.argv:
        MIN_WRIST_SEP = float(sys.argv[sys.argv.index("--min-sep") + 1])
    head_pose = None
    head_angles = None
    # First head option wins, including across the two spellings. Wrapper defaults
    # are appended, so explicit user options keep their established precedence.
    for index, flag in enumerate(sys.argv[1:], 1):
        if flag not in ("--head", "--head-rad"):
            continue
        if index + 1 >= len(sys.argv):
            raise SystemExit(flag + " requires a value")
        if flag == "--head":
            head_pose = sys.argv[index + 1]
        else:
            try:
                head_angles = np.asarray([float(v) for v in sys.argv[index + 1].split(",")])
            except ValueError:
                raise SystemExit("--head-rad requires three comma-separated radians")
            if head_angles.shape != (3,) or not np.isfinite(head_angles).all():
                raise SystemExit("--head-rad requires three finite comma-separated radians")
        break
    if "--step" in sys.argv:
        STEP = float(sys.argv[sys.argv.index("--step") + 1])
    if "--wait" in sys.argv:
        WAIT = float(sys.argv[sys.argv.index("--wait") + 1])

    flagvals = set()
    for f in ("--head", "--head-rad", "--step", "--wait", "--min-sep", "--seq"):
        if f in sys.argv:
            flagvals.add(sys.argv[sys.argv.index(f) + 1])
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a not in flagvals]
    pose_name = args[0] if args else "pre_move"
    if not all(np.isfinite(v) and v > 0 for v in (STEP, WAIT, MIN_WRIST_SEP)):
        raise SystemExit("--step, --wait and --min-sep must be finite and positive")
    print("step %.3f rad, %.2f s between steps -> ~%.2f rad/s"
          % (STEP, WAIT, STEP / WAIT))

    if pose_name in BANNED:
        raise SystemExit("Refusing a folded pose before constructing Robot()")
    if dry:
        print("WARNING: --dry-run still constructs Robot(), which may home the head.")
    robot = Robot()
    try:
        goals = resolve(robot, pose_name)
        comps = {n: getattr(robot, n) for n in goals}
        print("pose: %s" % pose_name)
        for n, comp in comps.items():
            goals[n] = report(n, comp, goals[n])

        head_goal = None
        if head_pose:
            head = robot.head
            head_goal = report("head (%s)" % head_pose, head,
                               np.asarray(head.get_predefined_pose(head_pose), float))
        elif head_angles is not None:
            limits = np.asarray(robot.head.joint_pos_limit, dtype=float)
            if (limits.shape != (3, 2) or not np.isfinite(limits).all()
                    or np.any(head_angles < limits[:, 0] + MARGIN)
                    or np.any(head_angles > limits[:, 1] - MARGIN)):
                raise SystemExit("Refusing calibrated head target outside joint limits with margin")
            head_goal = report("head (calibrated radians)", robot.head, head_angles)

        order = None
        if seq and len(comps) == 2:
            order = (["left_arm", "right_arm"] if seq == "left"
                     else ["right_arm", "left_arm"])

        check_path(comps, goals, STEP, order)

        if dry:
            print("\nDRY RUN - no arm targets sent; Robot() may already have homed the head.")
            return

        if order is None:
            print("\nMoving both arms together (%.2f rad/step)..." % STEP)
            step_to(comps, goals, STEP)
        else:
            for name in order:
                print("\nMoving %s alone (%.2f rad/step)..." % (name, STEP))
                step_to({name: comps[name]}, {name: goals[name]}, STEP)
        if head_goal is not None:
            print("Moving head...")
            if head_angles is not None:
                calibrated_head_to(robot.head, head_goal)
            else:
                step_to({"head": robot.head}, {"head": head_goal}, 0.10)

        print("\n=== final ===")
        for n, comp in comps.items():
            fin = np.asarray(comp.get_joint_pos(), dtype=float)
            print("  %-10s %s   max err %.4f"
                  % (n, np.round(fin, 4).tolist(), np.max(np.abs(fin - goals[n]))))
        if head_goal is not None:
            fin = np.asarray(robot.head.get_joint_pos(), dtype=float)
            print("  %-10s %s" % ("head", np.round(fin, 4).tolist()))
    finally:
        robot.shutdown()


if __name__ == "__main__":
    main()
