#!/usr/bin/env python3
"""Compare motion strategies for brickbench_home -> pre_move by minimum wrist separation.

Pure FK, touches no hardware. Replays goto_pose.py's per-joint clipping so the simulated
waypoints are the ones the real move would visit.
"""
import numpy as np
import pinocchio as pin
from dexmate_urdf import robots

L = ["L_arm_j%d" % i for i in range(1, 8)]
R = ["R_arm_j%d" % i for i in range(1, 8)]

START = {"L": [0.0117, 1.2001, 1.4, -1.57, -1.5701, 1.0001, -0.35],
         "R": [-0.0127, -1.2001, -1.4, -1.5701, 1.5701, -0.9999, 0.3499]}
GOAL = {"L": [1.7289, 0.0101, 0.0041, -0.9924, -0.2311, 0.5011, -0.0066],
        "R": [-1.5683, -0.0026, 0.0031, -0.9916, 0.0908, -0.4138, -0.0018]}

STEP, TOL = 0.04, 0.02

model = pin.buildModelFromUrdf(str(robots.humanoid.vega_1u.vega_1u.urdf))
data = model.createData()
qidx = {n: model.joints[model.getJointId(n)].idx_q for n in L + R}
LF, RF = model.getFrameId("L_ee"), model.getFrameId("R_ee")


def sep(left, right):
    q = pin.neutral(model)
    for n, v in list(zip(L, left)) + list(zip(R, right)):
        q[qidx[n]] = v
    pin.forwardKinematics(model, data, q)
    pin.updateFramePlacements(model, data)
    return float(np.linalg.norm(data.oMf[LF].translation - data.oMf[RF].translation))


def ramp(cur, goal):
    pts, p = [np.array(cur, float)], np.array(cur, float)
    for _ in range(2000):
        err = np.array(goal, float) - p
        if np.max(np.abs(err)) <= TOL:
            break
        p = p + np.clip(err, -STEP, STEP)
        pts.append(p.copy())
    return pts


def pad(a, n):
    return a + [a[-1]] * (n - len(a))


def report(name, lpts, rpts):
    n = max(len(lpts), len(rpts))
    lp, rp = pad(lpts, n), pad(rpts, n)
    seps = [sep(l, r) for l, r in zip(lp, rp)]
    i = int(np.argmin(seps))
    print("%-34s waypoints %3d   min %.3f m at %3d   start %.3f  end %.3f"
          % (name, n, seps[i], i, seps[0], seps[-1]))
    return seps[i]


lp = ramp(START["L"], GOAL["L"])
rp = ramp(START["R"], GOAL["R"])
lhold = [np.array(START["L"], float)]
rhold = [np.array(START["R"], float)]

print("strategy                            ")
report("A both arms concurrently", lp, rp)
report("B left first, then right",
       lp + [lp[-1]] * len(rp), pad(rhold, len(lp)) + rp)
report("C right first, then left",
       pad(lhold, len(rp)) + lp, rp + [rp[-1]] * len(lp))
