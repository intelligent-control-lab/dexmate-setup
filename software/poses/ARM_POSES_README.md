> Historical source-robot notes. For the current install paths, reference head defaults, dry-run side effects, and per-robot checks, use the [bilingual manual](https://intelligent-control-lab.github.io/dexmate-setup/). Values and cable status here are historical.

# Arm poses on the Vega-1U

Two scripts move the arms between the only two poses this setup uses. Both are slow,
limit-checked, and refuse paths that would bring the grippers together.

```bash
cd ~/py_scripts
export ROBOT_NAME="dm/YOUR_SERIAL-1u"      # Robot() raises ValueError without this

python3 goto_ready.py     # rest  -> manipulation ready
python3 goto_rest.py      # ready -> rest
```

Add `--dry-run` to print the plan, the per-joint limit check and the clearance number
without commanding anything. Any flag you pass overrides the script's default, e.g.
`python3 goto_rest.py --step 0.02 --wait 1.0` to go slower.

## The two poses

**rest** (`pre_move` in `goto_pose.py`) — where the robot sits when nothing is running.
This is the only pose empirically known to be safe to park in.

```
left  [ 1.7289, 0.0101, 0.0041, -0.9924, -0.2311,  0.5011, -0.0066]
right [-1.5683,-0.0026, 0.0031, -0.9916,  0.0908, -0.4138, -0.0018]
```

**manipulation ready** (`brickbench_home`) — BrickBench's `Joint_Home_Position`, arms
forward over the table. Wrists sit 0.656 m apart, roughly level with the shoulders.

```
left  [0,  1.2,  1.4, -1.57, -1.57,  1, -0.35]
right [0, -1.2, -1.4, -1.57,  1.57, -1,  0.35]
```

## Why the arms move one at a time

Minimum wrist separation along the path, by schedule:

| direction | concurrent | left first | right first |
|---|---|---|---|
| rest -> ready | 0.354 m | 0.431 m | **0.459 m** |
| ready -> rest | 0.267 m | **0.459 m** | 0.434 m |

**The collision risk is in the schedule, not in the target pose.** Both endpoints are
safe in both directions; concurrent motion is what swings the wrists past each other
mid-path. `goto_rest.py` concurrent would dip to 0.267 m — closer than the 0.31 m that
actually broke a gripper cable. Sequential costs twice the wall clock and nothing else.

## The clearance guard

`goto_pose.py` simulates the exact waypoints the move will visit (same per-joint
clipping the real loop uses, and the same left/right schedule), computes wrist
separation at each one by URDF forward kinematics, and raises `SystemExit` if any
waypoint falls below `MIN_WRIST_SEP` (0.35 m, override with `--min-sep`).

It exists because **the CAN grippers extend past `L_ee` / `R_ee` and are not in
`vega_1u.urdf` at all**, so pinocchio and every URDF-based collision check are blind to
them. Calibration points, all from real outcomes:

| pose / path | separation | outcome |
|---|---|---|
| `folded` | 0.31 m | grippers crossed, **broke a cable** |
| ready -> rest, concurrent | 0.267 m | traversed once with no contact |
| rest <-> ready, concurrent | 0.364 m | traversed twice, no contact |
| `pre_move` endpoint | 0.44 m | fine |
| `brickbench_home` endpoint | 0.66 m | fine |

Note the 0.267 m row: it is *below* the value that caused damage, yet nothing touched.
**Wrist-centre distance ignores orientation** — `folded` tucks both forearms inward so
the jaws face each other, which is far worse than the number alone says. Treat the
guard as a coarse screen, not a proof of clearance. Prefer re-measuring over lowering
the threshold.

## `folded` is banned

`folded` and `folded_closed_hand` from the arm `pose_pool` are in `goto_pose.py`'s
`BANNED` set and refuse to run. They were designed around Dexmate's own end effectors;
with these grippers fitted, `folded` crossed the jaws and broke the left gripper's CAN
cable. Do not use them as a "safe stow" — **rest is the stow pose here.**

## Things that bite

- **`Robot()` always drives the head to `home`.** `Robot.__init__` takes only
  `(configs, auto_shutdown)`; `_safe_initialize_components` runs a hardcoded step list
  ending in `("default state", self._set_default_state)` (robot.py:353), and
  `_set_default_state` (robot.py:424) calls `head.set_joint_pos(home_pos)`
  unconditionally unless the software E-Stop is active. There is no flag to skip it.
  Re-apply any head pose after construction — see `head_pose.py`.
- **A head pose does not survive process exit.** It holds exactly while the session is
  alive (measured: no drift over 25 s), then relaxes from -0.5056 to about -0.13 rad.
  Anything that depends on head angle must hold its own live `Robot()` session.
- **To read sensors without moving anything**, skip `Robot()` entirely and build the
  sensor manager directly — `Sensors(get_robot_config().sensors)`; see
  `sensor_only.py`. It publishes no control topic. It also cannot hold the head.
- **`ROBOT_NAME` must be in the environment.** A non-interactive `ssh` does not source
  the interactive shell config, so prefix it on the command line.
- The arms have no torso or chassis to move: `vega_1u` exposes `left_arm` (7),
  `right_arm` (7) and `head` (3) only.

Grippers are documented separately in `GRIPPER_README.md`.
