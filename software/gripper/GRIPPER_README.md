> Historical source-robot notes. For the current install paths, reference head defaults, dry-run side effects, and per-robot checks, use the [bilingual manual](https://intelligent-control-lab.github.io/dexmate-setup/). Values and cable status here are historical.

# Vega Gripper Driver

Python control for the two grippers on the Dexmate Vega-1U, over CAN.

## Hardware

| | |
|---|---|
| Actuators | 2 × **MG4005-i10 V3** servo (LK Tech / MYACTUATOR lineage, 10:1 reduction) |
| Connector board | `iSuit_D_A2_Sub` |
| Adapter | **Jhoinrch RH-02** USB-to-CAN (Canable/candleLight clone, STM32F072C8T6, USB `1d50:606f`) |
| Bus | CAN 2.0, **1 Mbit/s**, standard frames |
| Motor IDs | **1 = LEFT**, **2 = RIGHT** |
| Termination | 60 Ω across CAN_H/CAN_L. Both motors have internal 120 Ω, so the adapter's `R120` switch must be **OFF** |

The adapter's `BOOT` switch must be **OFF** (work mode). ON puts the STM32 into its DFU
bootloader and no CAN interface appears at all.

## One-time setup

The `gs_usb` driver is **not** shipped with the L4T kernel and must be built out of tree.
It has to be rebuilt after any kernel change.

```bash
mkdir -p ~/gs_usb_build && cd ~/gs_usb_build
curl -fsSLO https://raw.githubusercontent.com/gregkh/linux/v$(uname -r | cut -d- -f1)/drivers/net/can/usb/gs_usb.c
echo 'obj-m += gs_usb.o' > Makefile
make -C /lib/modules/$(uname -r)/build M=$PWD modules
sudo mkdir -p /lib/modules/$(uname -r)/kernel/drivers/net/can/usb
sudo cp gs_usb.ko /lib/modules/$(uname -r)/kernel/drivers/net/can/usb/
sudo depmod -a && sudo modprobe gs_usb
```

```bash
pip install --user python-can
```

## Bring the bus up

`can0` is the Jetson's **on-SoC** controller and is *not* the adapter. The adapter is `can1`.

```bash
sudo ip link set can1 up type can bitrate 1000000 loopback off listen-only off restart-ms 100
```

Spell out `loopback off listen-only off` every time — **control-mode flags are sticky** and
survive a `down`/`up`. A leftover `listen-only` silently blocks all transmits while `cansend`
still returns success.

## Quick start

```python
from gripper import Grippers

g = Grippers()          # opens can1
g.home()                # find the closed stop on each gripper (~1 min)

g.both_open(speed=500)
g.both_close(speed=500)

g.left.move_to(0.4)              # 0.0 = closed, 1.0 = open
g.right.grip(current=0.6)        # close onto an object

print(g.status())
```

Homing takes about a minute and derives the reference from the mechanism itself.
**Prefer it.** You can skip it by passing closed-stop angles from a previous session, but only
if the motors have stayed enabled since — and even then it has been observed to drift by whole
revolutions across a gap, for reasons not fully understood:

```python
g = Grippers(calibration=[-553.5, -2765.3])   # shortcut — verify before trusting
```

To check a stored calibration without a full re-home, drive to the closed stop and compare:

```python
found = g.left.find_stop(-1)
print(found - g.left.closed_deg)     # a few degrees is fine; a multiple of 360 is not
```

## ⚠ The one rule: never call `release()` casually

`release()` sends `0x80` (motor off), and **that destroys the position reference**. Afterwards
`0x92` reports only the single-turn angle wrapped to (−180, 180], so all your coordinates
silently become wrong — off by whole revolutions.

The motors are self-holding when energised and draw only ~0.1 A doing it. So:

- **home once, then leave the motors enabled** for the whole working session
- call `release()` only when you accept re-homing next time
- `halt()` stops motion without dropping the reference — use it for an emergency stop

## Shutting down safely

`close_bus()` only releases the CAN socket — it does **not** disable the motors. Whether you
call `release()` is the real decision, and it costs you the calibration.

**Pausing, back soon** — leaves the motors holding, calibration intact, so you can skip homing:

```python
g.both_close(speed=500)   # park somewhere sensible
g.close_bus()
```

They hold at ~0.1 A each. Nothing is lost.

**Done for the day, or someone will handle the grippers** — de-energises them so the jaws are
limp and safely back-driveable:

```python
g.both_close(speed=500)
g.release()               # loses calibration — g.home() next session
g.close_bus()
```

**Powering the robot off** — just close the REPL. The reference dies with the power either way,
so there is nothing to protect.

Also worth knowing:

- **Never exit mid-move.** Ctrl-C leaves the motor still executing its last `0xA4` target.
  **`g.halt()` is the emergency stop** — it stops motion *without* losing calibration.
- **Leaving `can1` up is fine.** An idle CAN interface costs nothing; no need to bring it down.
- **Closing the REPL without `close_bus()`** only prints `SocketcanBus was not properly shut
  down`. It is harmless, and the motors stay energised and calibrated.

## API

### `Grippers`

| | |
|---|---|
| `Grippers(channel="can1", calibration=None)` | `calibration` is `[left_closed_deg, right_closed_deg]` |
| `home()` | find both closed stops, return their angles |
| `both_move_to(fraction, speed=500, …)` | drive **both concurrently** — wall clock is the slower motor, not the sum |
| `both_open(**kw)` / `both_close(**kw)` | full travel, both motors concurrently (~9 s at 500 dps) |
| `status()` | dict of angle, current, temp, volts, enabled, position |
| `halt()` | stop motion, keep calibration |
| `release()` | de-energise both — **loses calibration** |
| `close_bus()` | shut down the CAN socket |

### `Motor` — `g.left`, `g.right`

| | |
|---|---|
| `move_to(fraction, speed=150, i_max=1.2, margin=0.02)` | `fraction` 0.0 = closed, 1.0 = open |
| `open(**kw)` / `close(**kw)` | shorthand for `move_to(1.0)` / `move_to(0.0)` |
| `grip(current=0.6, speed=60)` | close until resistance; returns a dict with `gripped` |
| `position()` | current position as 0.0–1.0 |
| `angle()` `current()` `temperature()` `voltage()` `enabled()` | telemetry |
| `home()` `calibrate_from(closed_deg)` `find_stop(direction)` | calibration |
| `enable()` `halt()` `release()` `clear_error()` | state |

**`speed`** is in degrees/sec of motor travel and is honoured closely — 100/250/500 dps measured
at 100/249/499 effective. 500 dps is comfortable (peak 0.28 A, same as slow moves).

**`margin`** keeps the jaws off the hard stops, so `move_to(1.0)` actually lands at 0.98.
Pass `margin=0.0` for the true extreme.

**`close()` vs `grip()`** — `close()` drives to a position and will stall against anything in the
way. `grip()` closes under a current limit and reports whether it made contact. Use `grip()` on
objects.

## Calibration

Measured 2026-08-29, both ends found by contact:

| | Closed | Open | Stroke |
|---|---|---|---|
| Left (motor 1) | −553.5° | +4126.0° | **4679.5°** |
| Right (motor 2) | −2765.3° | +1915.7° | **4681.1°** |

Negative = closed, positive = open, on both. The two strokes agree to 1.6° (0.03%), which is the
cross-check that they're right. `STROKE` in `gripper.py` holds these; the absolute angles are
session-specific and come from homing.

Full open/close draws **under 0.3 A** across the whole travel. A hard stop shows **~2.5 A**.

## Protocol notes

Arbitration IDs are `0x140 + motor_id`; **replies come back on the same ID**, not `0x240 + id`
as the MYACTUATOR document states.

The firmware is a **hybrid** and this is the trap that matters most:

- **Read** opcodes follow LK Tech — `0x90` `0x92` `0x94` `0x9A` `0x9C` `0x9D` work,
  `0x30` `0x33` `0x70` `0xB1` `0xB2` `0xB5` return nothing
- **Motion** opcodes follow MYACTUATOR, which is offset by one from LK Tech:
  **`0xA2` is speed, not position.** Sending a position value to `0xA2` makes the motor rotate
  continuously at that number in deg/s. Use **`0xA4`** (absolute position, with a speed limit).

Other findings worth keeping:

- `errorState = 0x0010` means **"output stage disabled"**, not over-current. It tracks
  `0x80`/`0x88` exactly. Judge real over-current from the `iq` field of `0x9C` (0.01 A/LSB).
- Motion commands are silently ignored until the motor is enabled with `0x88`.
- `0x9B` clears the error flag and works, though it's absent from the MYACTUATOR doc.
- Use `0xA4` absolute targets recomputed from a fresh `0x92` reading — **not** `0xA8` increments,
  whose reference is the last *commanded* position and inherits windup after an abort.
- Encoder is 16-bit, 65536 counts/rev. `0x92` is a genuine multi-turn accumulator while enabled.
- The two motors are mechanically **independent** — driving one does not move the other.

## Troubleshooting

**No `can1` interface** — check `lsusb` for `1d50:606f`. If you see `0483:df11` instead, the
adapter's `BOOT` switch is ON (DFU mode); flip it and **replug** (BOOT0 is only sampled at reset).
If neither appears, `gs_usb` isn't loaded.

**`TX packets` stuck at exactly 3** — that's the STM32's three transmit mailboxes full of
unacknowledged frames, i.e. **nothing on the bus is ACKing**. Only `tx > 3` proves a live node.
Wedged mailboxes live in adapter firmware and survive `ip link down/up`; reset the USB port:

```bash
echo 0 | sudo tee /sys/bus/usb/devices/1-2.3/authorized; echo 1 | sudo tee /sys/bus/usb/devices/1-2.3/authorized
```

**Bus completely silent** — the motors never broadcast, they only answer. An empty `candump`
proves nothing. Send a read and look for a reply.

**Positions are wrong by whole revolutions** — something sent `0x80`. Re-home.

**A reading comes back as exactly `0.0`, or a move reports `stall` with `0.00 A`** — two clients
are on the bus. SocketCAN delivers every frame to every socket, including other processes'
*outgoing queries*, which carry the same arbitration ID and command byte as a reply. A query
decodes as all zeros. The driver guards against this (`ignore_echo` in `_cmd`), but if you write
your own code against the bus, filter it out — and prefer one client at a time regardless.

**`SocketcanBus was not properly shut down`** — harmless; call `g.close_bus()` when done.

**Code changes don't take effect in a REPL** — Python caches imports:

```python
import importlib, gripper; importlib.reload(gripper)
from gripper import Grippers
```

**`candump` shows nothing while RX climbs** — those are error frames; `candump` hides them by
default. Use `candump -e can1`.

**Sanity check without the driver.** Note `candump` must already be running — the reply lands
within a millisecond, so starting it after `cansend` catches nothing:

```bash
timeout 3 candump -e -n 2 can1 & sleep 0.3; cansend can1 141#9A00000000000000; wait
```

```
can1  141   [8]  9A 00 00 00 00 00 00 00      <- our query
can1  141   [8]  9A 1F 54 09 00 00 00 00      <- reply: 0x1F = 31 C, 0x0954 = 23.88 V
```

Or in Python, which avoids the race entirely:

```bash
python3 -c "
import can
b=can.Bus(channel='can1', interface='socketcan')
b.send(can.Message(arbitration_id=0x141, data=[0x9A,0,0,0,0,0,0,0], is_extended_id=False))
r=b.recv(timeout=1.0)
print('reply:', bytes(r.data).hex(' ') if r else 'NONE')
b.shutdown()"
```

A reply starting `9a` means the left motor is alive. Use `0x142` for the right.
