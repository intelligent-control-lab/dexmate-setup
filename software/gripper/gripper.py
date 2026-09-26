"""
Vega gripper driver — 2x MG4005-i10 V3 servos on a Jhoinrch RH-02 USB-CAN adapter.

Bus: can1 @ 1 Mbit/s.  Motor 1 = LEFT, motor 2 = RIGHT.
Protocol is a hybrid: LK Tech *read* opcodes, MYACTUATOR *motion* opcodes.

IMPORTANT: sending 0x80 (motor off) DESTROYS the multi-turn position reference —
afterwards 0x92 reports only the single-turn angle wrapped to (-180, 180]. So this
driver homes against the closed stop once, then keeps the motors ENABLED. Call
release() only when you accept losing calibration and re-homing next time.

    from gripper import Grippers
    g = Grippers()          # uses stored calibration; g.home() to re-derive
    g.left.open(); g.left.close()
    g.both_open(); g.both_close()
    g.left.grip(current=0.6)   # close until it meets resistance
    print(g.status())
"""
import can, time, struct

CLOSED, OPEN = 0.0, 1.0

# calibration measured 2026-08-29 (valid only while motors stay enabled)
STROKE = {1: 4679.5, 2: 4681.1}


class Motor:
    def __init__(self, bus, mid, name):
        self.bus, self.id, self.name = bus, mid, name
        self.closed_deg = None
        self.open_deg = None

    # ---------- raw protocol ----------
    def _cmd(self, data, timeout=0.25, ignore_echo=False):
        """Send a command and wait for its reply.

        `ignore_echo` guards against another process on the same interface: SocketCAN
        delivers every frame to every socket, including other clients' *outgoing*
        queries — which share our arbitration ID and command byte. Without this, a
        query gets mistaken for a reply and decodes as all zeros.
        """
        payload = list(data)
        self.bus.send(can.Message(arbitration_id=0x140 + self.id,
                                  data=payload, is_extended_id=False))
        sent = bytes(payload)
        t0 = time.time()
        while time.time() - t0 < timeout:
            r = self.bus.recv(timeout=timeout)
            if r is None:
                break
            if r.arbitration_id in (0x140 + self.id, 0x240 + self.id) and r.data[0] == data[0]:
                if ignore_echo and bytes(r.data) == sent:
                    continue          # that was somebody's query, not a reply
                return bytes(r.data)
        return None

    def _read(self, opcode):
        """Telemetry read — echo-guarded."""
        return self._cmd([opcode, 0, 0, 0, 0, 0, 0, 0], ignore_echo=True)

    def angle(self):
        d = self._read(0x92)
        return None if not d else int.from_bytes(d[1:8], "little", signed=True) / 100.0

    def current(self):
        """torque current in amps"""
        d = self._read(0x9C)
        return None if not d else int.from_bytes(d[2:4], "little", signed=True) / 100.0

    def temperature(self):
        d = self._read(0x9A)
        return None if not d else d[1]

    def voltage(self):
        d = self._read(0x9A)
        return None if not d else int.from_bytes(d[2:4], "little") / 100.0

    def enabled(self):
        """0x0010 is a state bit meaning 'output stage off', not a fault."""
        d = self._read(0x9A)
        return None if not d else int.from_bytes(d[6:8], "little") == 0x0000

    def enable(self):  self._cmd([0x88, 0, 0, 0, 0, 0, 0, 0])
    def halt(self):    self._cmd([0x81, 0, 0, 0, 0, 0, 0, 0])
    def release(self): self._cmd([0x80, 0, 0, 0, 0, 0, 0, 0])   # loses calibration!
    def clear_error(self): self._cmd([0x9B, 0, 0, 0, 0, 0, 0, 0])

    # ---------- motion ----------
    def _send_goto(self, target, speed):
        """Fire an absolute move (0xA4) and return immediately, without waiting."""
        p = [0xA4, 0, speed & 0xFF, (speed >> 8) & 0xFF] + list(struct.pack("<i", int(round(target * 100))))
        self._cmd(p, timeout=0.4)
        return target

    def target_for(self, fraction, margin=0.02):
        """Absolute angle for a 0..1 position, clamped off the hard stops."""
        self._require_cal()
        f = max(margin, min(1.0 - margin, fraction))
        return self.closed_deg + STROKE[self.id] * f

    def _goto(self, target, speed, i_max, timeout, blind=1.0):
        """absolute move, 0xA4. Returns (angle, peak_current, reason)."""
        self._send_goto(target, speed)
        t0, last, flat, peak = time.time(), None, 0, 0.0
        while time.time() - t0 < timeout:
            time.sleep(0.08)
            a, c = self.angle(), self.current()
            if a is None:
                continue
            if time.time() - t0 > blind and c is not None:
                peak = max(peak, abs(c))
                if abs(c) > i_max:
                    self.halt(); return a, peak, "current"
                if last is not None and abs(a - last) < 0.3:
                    flat += 1
                    if flat >= 3:
                        self.halt(); return a, peak, "stall"
                else:
                    flat = 0
            last = a
            if abs(a - target) < 2.0:
                return a, peak, "reached"
        self.halt(); return self.angle(), peak, "timeout"

    def alive(self, tries=3):
        """True if the motor answers a telemetry read. Cheap - use before commanding."""
        return any(self._read(0x92) for _ in range(tries))

    def _require_alive(self):
        if not self.alive():
            raise RuntimeError(
                f"{self.name} (motor id {self.id}) is not responding on CAN. "
                f"Check the cable and the CAN_H/CAN_L polarity - reversed polarity "
                f"gives exactly this: no replies and no error frames.")

    def find_stop(self, direction, step=200.0, speed=90, i_max=1.2, budget=40):
        """Walk until the mechanism stops us. direction: -1 closed, +1 open."""
        self._require_alive()
        self.enable()
        for _ in range(budget):
            cur = self.angle()
            if cur is None:
                raise RuntimeError(f"{self.name} stopped answering mid-homing")
            a, pk, why = self._goto(cur + direction * step, speed, i_max,
                                    timeout=step / speed * 3 + 5)
            if why in ("current", "stall") or abs(a - cur) < step * 0.3:
                return a
            self.enable()
        return self.angle()

    def home(self, verbose=True):
        """Find the closed stop and derive the open end from the known stroke."""
        self._require_alive()
        self.clear_error(); self.enable()
        if verbose: print(f"  homing {self.name}...")
        self.closed_deg = self.find_stop(-1)
        self.open_deg = self.closed_deg + STROKE[self.id]
        if verbose: print(f"  {self.name}: closed={self.closed_deg:+.1f} open={self.open_deg:+.1f}")
        return self.closed_deg

    def calibrate_from(self, closed_deg):
        self.closed_deg = closed_deg
        self.open_deg = closed_deg + STROKE[self.id]

    # ---------- high level ----------
    def _require_cal(self):
        if self.closed_deg is None:
            raise RuntimeError(f"{self.name} not calibrated — call home() first")

    def position(self):
        """0.0 = closed, 1.0 = open"""
        self._require_cal()
        a = self.angle()
        if a is None:
            raise RuntimeError(f"{self.name} is not responding on CAN")
        return (a - self.closed_deg) / STROKE[self.id]

    def move_to(self, fraction, speed=150, i_max=1.2, margin=0.02):
        """fraction 0..1 (clamped inside `margin` so we never rest on a hard stop)"""
        self._require_cal()
        f = max(margin, min(1.0 - margin, fraction))
        target = self.closed_deg + STROKE[self.id] * f
        self.enable()
        a, pk, why = self._goto(target, speed, i_max,
                                timeout=abs(target - self.angle()) / speed * 3 + 8)
        return a, pk, why

    def open(self, **kw):  return self.move_to(OPEN, **kw)
    def close(self, **kw): return self.move_to(CLOSED, **kw)

    def grip(self, current=0.6, speed=60):
        """Close until resistance — use this on an object, not close()."""
        self._require_cal()
        self.enable()
        target = self.closed_deg + STROKE[self.id] * 0.02
        a, pk, why = self._goto(target, speed, current,
                                timeout=abs(target - self.angle()) / speed * 3 + 8)
        return {"angle": a, "peak_current": pk, "stopped_by": why,
                "position": (a - self.closed_deg) / STROKE[self.id],
                "gripped": why in ("current", "stall")}


class Grippers:
    def __init__(self, channel="can1", calibration=None):
        self.bus = can.Bus(channel=channel, interface="socketcan")
        self.left = Motor(self.bus, 1, "left")
        self.right = Motor(self.bus, 2, "right")
        if calibration:
            for m, c in zip((self.left, self.right), calibration):
                m.calibrate_from(c)

    def home(self, require_all=False):
        """Home every motor that answers. A motor that is off the bus is reported and
        skipped rather than aborting the whole call, so one dead motor does not stop
        the other from homing. Pass require_all=True to insist on both."""
        missing = [m.name for m in (self.left, self.right) if not m.alive()]
        if missing and require_all:
            raise RuntimeError("not responding on CAN: " + ", ".join(missing))
        for m in (self.left, self.right):
            if m.name in missing:
                print(f"  skipping {m.name}: not responding on CAN")
                continue
            m.home()
        return {m.name: m.closed_deg for m in (self.left, self.right)}

    def both_move_to(self, fraction, speed=500, i_max=1.2, margin=0.02, timeout=None):
        """Drive BOTH grippers concurrently.

        Both 0xA4 commands are issued back-to-back, then the two motors are polled
        together until each finishes. Wall-clock time is the slower motor, not the sum.
        Returns {"left": (angle, peak_current, reason), "right": (...)}.
        """
        ms = [self.left, self.right]
        tgt = {}
        for m in ms:
            m.enable()
            tgt[m] = m.target_for(fraction, margin)
        if timeout is None:
            span = max(abs(tgt[m] - m.angle()) for m in ms)
            timeout = span / max(speed, 1) * 3 + 8
        for m in ms:                      # fire both, then wait on both
            m._send_goto(tgt[m], speed)
        done, peak = {}, {m: 0.0 for m in ms}
        last, flat = {m: None for m in ms}, {m: 0 for m in ms}
        t0 = time.time()
        while len(done) < len(ms) and time.time() - t0 < timeout:
            time.sleep(0.05)
            for m in ms:
                if m in done:
                    continue
                a, c = m.angle(), m.current()
                if a is None:
                    continue
                if time.time() - t0 > 1.0 and c is not None:
                    peak[m] = max(peak[m], abs(c))
                    if abs(c) > i_max:
                        m.halt(); done[m] = (a, peak[m], "current"); continue
                    if last[m] is not None and abs(a - last[m]) < 0.3:
                        flat[m] += 1
                        if flat[m] >= 3:
                            m.halt(); done[m] = (a, peak[m], "stall"); continue
                    else:
                        flat[m] = 0
                last[m] = a
                if abs(a - tgt[m]) < 2.0:
                    done[m] = (a, peak[m], "reached")
        for m in ms:
            if m not in done:
                m.halt(); done[m] = (m.angle(), peak[m], "timeout")
        return {m.name: done[m] for m in ms}

    def both_open(self, **kw):  return self.both_move_to(OPEN, **kw)
    def both_close(self, **kw): return self.both_move_to(CLOSED, **kw)

    def status(self):
        out = {}
        for m in (self.left, self.right):
            out[m.name] = {
                "angle": m.angle(), "current": m.current(),
                "temp_c": m.temperature(), "volts": m.voltage(),
                "enabled": m.enabled(),
                "position": (None if m.closed_deg is None else round(m.position(), 3)),
            }
        return out

    def halt(self):
        """Emergency stop — halts motion on both, keeps calibration. Safe to call anytime."""
        self.left.halt(); self.right.halt()

    def release(self):
        """De-energise BOTH — jaws go limp and back-driveable.

        Destroys the position reference: you must home() again next session.
        Use this when finishing for the day or when someone will handle the grippers.
        To stop motion WITHOUT losing calibration, use halt() instead.
        """
        self.left.release(); self.right.release()

    def close_bus(self):
        """Release the CAN socket only.

        This does NOT disable the motors — they stay energised, holding position, with
        their calibration intact. That is usually what you want between sessions.
        Call release() first if you want them limp (and accept re-homing next time).
        """
        self.bus.shutdown()
