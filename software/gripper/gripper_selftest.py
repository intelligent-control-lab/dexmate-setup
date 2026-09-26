#!/usr/bin/env python3
"""Gripper CAN connection self-test — runs ON the robot.

Assumes nothing about motor IDs, side mapping, or direction: everything is
discovered. Written for use after re-wiring, where the old calibration and
the old assumptions are both suspect.

    python3 gripper_selftest.py check    # read-only wiring verification
    python3 gripper_selftest.py status   # telemetry for discovered motors
    python3 gripper_selftest.py open     # full open against the hard stop, then halt
    python3 gripper_selftest.py close    # full close against the hard stop, then halt
    python3 gripper_selftest.py stop     # halt motion on every discovered motor
    python3 gripper_selftest.py all      # check -> open -> close -> stop

Exit code 0 = pass, 1 = fail. Prints a PASS/FAIL block at the end of `check`.
"""
import subprocess
import sys
import time

IFACE = "can1"          # can0 is the Jetson's on-SoC mttcan, NOT the adapter
BITRATE = 1_000_000
ID_SCAN = range(1, 33)  # protocol allows motor IDs 1..32

# read-only opcodes (LK Tech set — this firmware answers these)
RD_ANGLE, RD_STATUS1, RD_STATUS2 = 0x92, 0x9A, 0x9C
# motion / state opcodes (MYACTUATOR set — NOTE 0xA2 is SPEED, never use it for position)
MOTOR_OFF, MOTOR_HALT, MOTOR_ON, CLEAR_ERR, POS_ABS = 0x80, 0x81, 0x88, 0x9B, 0xA4

CURRENT_ABORT = 1.3     # amps; trips late (spikes between samples), treat as a detector
ACCEL_BLIND = 1.0       # seconds to ignore current for — acceleration draws current


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def link_state():
    out = sh(f"ip -details link show {IFACE}").stdout
    if not out:
        return None
    up = "state UP" in out or ",UP," in out
    br = None
    for tok in out.split():
        if tok.isdigit() and len(tok) >= 5:
            pass
    if "bitrate" in out:
        parts = out.split("bitrate")[1].split()
        br = int(parts[0]) if parts and parts[0].isdigit() else None
    return {"up": up, "bitrate": br, "raw": out}


def counters():
    out = sh(f"ip -details -s link show {IFACE}").stdout
    res = {}
    lines = out.splitlines()
    for i, ln in enumerate(lines):
        if "re-started" in ln and i + 1 < len(lines):
            f = lines[i + 1].split()
            keys = ["restart", "buserr", "arblost", "errwarn", "errpass", "busoff"]
            for k, v in zip(keys, f):
                res[k] = int(v) if v.isdigit() else -1
        if ln.strip().startswith("RX:") and i + 1 < len(lines):
            res["rx_pkts"] = int(lines[i + 1].split()[1])
        if ln.strip().startswith("TX:") and i + 1 < len(lines):
            f = lines[i + 1].split()
            res["tx_pkts"], res["tx_drop"] = int(f[1]), int(f[3])
    return res


class Bus:
    def __init__(self):
        import can
        self.can = can
        self.bus = can.Bus(channel=IFACE, interface="socketcan")

    def cmd(self, mid, opcode, payload=None, timeout=0.25, guard_echo=True):
        """Send and await the reply.

        guard_echo: SocketCAN delivers every frame to every socket, including other
        processes' *outgoing* queries — which share our arbitration ID and command
        byte. Without this a query is mistaken for a reply and decodes as all zeros.
        """
        data = [opcode] + list(payload or [0] * 7)
        data = (data + [0] * 8)[:8]
        sent = bytes(data)
        self.bus.send(self.can.Message(arbitration_id=0x140 + mid,
                                       data=data, is_extended_id=False))
        t0 = time.time()
        while time.time() - t0 < timeout:
            r = self.bus.recv(timeout=timeout)
            if r is None:
                break
            if r.arbitration_id in (0x140 + mid, 0x240 + mid) and r.data[0] == opcode:
                if guard_echo and bytes(r.data) == sent:
                    continue
                return bytes(r.data)
        return None

    def angle(self, mid):
        d = self.cmd(mid, RD_ANGLE)
        return None if not d else int.from_bytes(d[1:8], "little", signed=True) / 100.0

    def status1(self, mid):
        d = self.cmd(mid, RD_STATUS1)
        if not d:
            return None
        return {"temp_c": d[1],
                "volts": int.from_bytes(d[2:4], "little") / 100.0,
                # 0x0010 is a STATE bit meaning "output stage off", not over-current
                "err": int.from_bytes(d[6:8], "little")}

    def status2(self, mid):
        d = self.cmd(mid, RD_STATUS2)
        if not d:
            return None
        return {"temp_c": d[1],
                "amps": int.from_bytes(d[2:4], "little", signed=True) / 100.0,
                "speed": int.from_bytes(d[4:6], "little", signed=True),
                "enc": int.from_bytes(d[6:8], "little")}

    def shutdown(self):
        self.bus.shutdown()


def ensure_link():
    st = link_state()
    if st is None:
        print(f"  FAIL: interface {IFACE} does not exist")
        print("        adapter not enumerated, or gs_usb not loaded")
        return False
    if not st["up"]:
        print(f"  {IFACE} is down, bringing it up at {BITRATE}...")
        r = sh(f"sudo -n ip link set {IFACE} up type can bitrate {BITRATE} "
               f"loopback off listen-only off restart-ms 100")
        if r.returncode != 0:
            print(f"  FAIL: could not bring up {IFACE}: {r.stderr.strip()}")
            return False
        st = link_state()
    if st["bitrate"] != BITRATE:
        print(f"  FAIL: bitrate is {st['bitrate']}, expected {BITRATE}")
        return False
    print(f"  {IFACE} UP @ {st['bitrate']} bps")
    return True


def usb_present():
    out = sh("lsusb").stdout
    if "1d50:606f" in out:
        return True, "1d50:606f candleLight adapter present"
    if "0483:df11" in out:
        return False, "adapter is in DFU MODE — flip the BOOT switch OFF and REPLUG"
    return False, "adapter not enumerated on USB at all"


def discover(bus):
    """Scan IDs 1..32 by read. Returns {id: status1}."""
    found = {}
    for mid in ID_SCAN:
        s = bus.status1(mid)
        if s:
            found[mid] = s
    return found


def cmd_check():
    ok = True
    print("=" * 64)
    print("PHASE 1 — READ-ONLY CONNECTION CHECK")
    print("=" * 64)

    print("\n[1] USB adapter")
    present, msg = usb_present()
    print(f"  {'OK  ' if present else 'FAIL'}: {msg}")
    ok &= present
    if not present:
        return False, {}

    print("\n[2] CAN interface")
    if not ensure_link():
        return False, {}

    before = counters()
    bus = Bus()

    print("\n[3] Motor discovery (scanning IDs 1..32)")
    found = discover(bus)
    if not found:
        print("  FAIL: no motor replied on any ID")
        print("        Most likely causes, in order:")
        print("          - CAN_H / CAN_L swapped  (silent bus, no errors)")
        print("          - motors unpowered       (check 24V)")
        print("          - GND not shared between adapter and motor supply")
        print("          - wrong bitrate")
        bus.shutdown()
        return False, {}
    for mid, s in sorted(found.items()):
        print(f"  OK  : motor ID {mid} (cmd 0x{0x140+mid:03X}) "
              f"{s['temp_c']}C {s['volts']:.2f}V err=0x{s['err']:04X}")

    print("\n[4] Transmit acknowledgement")
    after = counters()
    tx = after.get("tx_pkts", 0)
    # bxCAN has exactly 3 TX mailboxes; unACKed frames occupy them forever.
    # tx > 3 is the ONLY proof that something on the bus is acknowledging.
    if tx > 3:
        print(f"  OK  : TX packets = {tx} (>3 — frames are being acknowledged)")
    else:
        print(f"  FAIL: TX packets stuck at {tx}")
        print("        3 = the STM32's three mailboxes full of unACKed frames.")
        print("        Nothing on the bus is acknowledging — suspect CAN_H/CAN_L swap.")
        ok = False

    print("\n[5] Bus error counters")
    bad = {k: after.get(k, 0) for k in ("buserr", "arblost", "errwarn", "errpass", "busoff")
           if after.get(k, 0) > before.get(k, 0)}
    drop = after.get("tx_drop", 0) - before.get("tx_drop", 0)
    if not bad and drop == 0:
        print(f"  OK  : no bus errors, no dropped frames "
              f"(rx={after.get('rx_pkts')} tx={after.get('tx_pkts')})")
    else:
        print(f"  FAIL: errors during scan: {bad} tx_dropped={drop}")
        print("        Suspect termination (want 60 ohm across CAN_H/CAN_L) or noise.")
        ok = False

    print("\n[6] Link reliability (100 round-trips per motor)")
    for mid in sorted(found):
        good, lat = 0, []
        for _ in range(100):
            t0 = time.time()
            if bus.status2(mid):
                good += 1
                lat.append((time.time() - t0) * 1000)
        lat.sort()
        rate = 100 * good / 100
        verdict = "OK  " if rate >= 99 else "FAIL"
        if rate < 99:
            ok = False
        med = lat[len(lat) // 2] if lat else float("nan")
        print(f"  {verdict}: motor {mid}: {good}/100 replies ({rate:.0f}%), median {med:.2f} ms")

    print("\n[7] Motor health")
    for mid in sorted(found):
        s1, s2 = bus.status1(mid), bus.status2(mid)
        if not s1 or not s2:
            print(f"  FAIL: motor {mid} stopped replying")
            ok = False
            continue
        volt_ok = 20.0 <= s1["volts"] <= 30.0
        # 0x0010 == output stage disabled (a state bit). Anything else is a real fault.
        fault = s1["err"] not in (0x0000, 0x0010)
        en = "enabled" if s1["err"] == 0x0000 else "disabled"
        print(f"  {'OK  ' if volt_ok and not fault else 'FAIL'}: motor {mid}: "
              f"{s1['volts']:.2f}V {s1['temp_c']}C {en} "
              f"pos={bus.angle(mid):+.2f}deg enc={s2['enc']}")
        if not volt_ok:
            print(f"        supply out of range — expected ~24V")
            ok = False
        if fault:
            print(f"        fault flag 0x{s1['err']:04X}")
            ok = False

    bus.shutdown()
    return ok, found


def _goto(bus, mid, target, speed, i_max, timeout):
    import struct
    p = [0, speed & 0xFF, (speed >> 8) & 0xFF] + list(struct.pack("<i", int(round(target * 100))))
    bus.cmd(mid, POS_ABS, p, timeout=0.4)
    t0, last, flat, peak = time.time(), None, 0, 0.0
    while time.time() - t0 < timeout:
        time.sleep(0.1)
        a = bus.angle(mid)
        s = bus.status2(mid)
        if a is None or s is None:
            continue
        if time.time() - t0 > ACCEL_BLIND:
            peak = max(peak, abs(s["amps"]))
            if abs(s["amps"]) > i_max:
                bus.cmd(mid, MOTOR_HALT, guard_echo=False)
                return a, peak, "current"
            if last is not None and abs(a - last) < 0.3:
                flat += 1
                if flat >= 3:
                    bus.cmd(mid, MOTOR_HALT, guard_echo=False)
                    return a, peak, "stall"
            else:
                flat = 0
        last = a
        if abs(a - target) < 2.0:
            return a, peak, "reached"
    bus.cmd(mid, MOTOR_HALT, guard_echo=False)
    return bus.angle(mid), peak, "timeout"


def cmd_drive(direction, found=None, step=200.0, speed=90, budget=40):
    """Drive every discovered motor to a hard stop, then halt.

    direction: -1 = close, +1 = open.
    """
    label = "CLOSE" if direction < 0 else "OPEN"
    ing = "closing" if direction < 0 else "opening"
    print("=" * 64)
    print(f"PHASE — FULL {label}, THEN STOP")
    print("=" * 64)
    bus = Bus()
    if found is None:
        found = discover(bus)
    if not found:
        print("  FAIL: no motors found")
        bus.shutdown()
        return False
    results = {}
    for mid in sorted(found):
        print(f"\n  motor {mid}: {ing} (steps of {step:.0f}deg @ {speed}dps, "
              f"abort {CURRENT_ABORT}A)")
        bus.cmd(mid, CLEAR_ERR, guard_echo=False)
        bus.cmd(mid, MOTOR_ON, guard_echo=False)
        time.sleep(0.3)
        start = bus.angle(mid)
        stop_at, why, pk = start, "budget", 0.0
        for i in range(budget):
            cur = bus.angle(mid)
            a, peak, reason = _goto(bus, mid, cur + direction * step, speed, CURRENT_ABORT,
                                    timeout=step / speed * 3 + 5)
            pk = max(pk, peak)
            if reason in ("current", "stall") or abs(a - cur) < step * 0.3:
                stop_at, why = a, reason
                print(f"    {label.lower()} stop at {a:+.1f}deg after {i+1} steps "
                      f"(peak {peak:.2f}A, {reason})")
                break
            bus.cmd(mid, MOTOR_ON, guard_echo=False)
        else:
            stop_at = bus.angle(mid)
            print(f"    WARNING: no stop found within {budget} steps "
                  f"({budget*step:.0f}deg), at {stop_at:+.1f}deg")
        bus.cmd(mid, MOTOR_HALT, guard_echo=False)
        results[mid] = {"start": start, "closed": stop_at, "why": why,
                        "travel": stop_at - start, "peak_amps": pk}
        print(f"    halted. travelled {stop_at - start:+.1f}deg")

    print("\n  --- summary ---")
    allok = True
    for mid, r in sorted(results.items()):
        good = r["why"] in ("current", "stall")
        allok &= good
        print(f"    motor {mid}: {'OK  ' if good else 'WARN'} "
              f"{label.lower()} stop at {r['closed']:+.1f}deg, travelled {r['travel']:+.1f}deg, "
              f"peak {r['peak_amps']:.2f}A ({r['why']})")
    bus.shutdown()
    return allok


def cmd_stop():
    bus = Bus()
    found = discover(bus)
    for mid in sorted(found) or ID_SCAN:
        bus.cmd(mid, MOTOR_HALT, guard_echo=False)
    print(f"  halted motors: {sorted(found) or 'none found'}")
    for mid in sorted(found):
        s = bus.status2(mid)
        if s:
            print(f"    motor {mid}: speed={s['speed']} amps={s['amps']:+.2f} enc={s['enc']}")
    bus.shutdown()
    return True


def cmd_status():
    bus = Bus()
    found = discover(bus)
    if not found:
        print("  no motors found")
        bus.shutdown()
        return False
    for mid in sorted(found):
        s1, s2 = bus.status1(mid), bus.status2(mid)
        print(f"  motor {mid}: {s1['volts']:.2f}V {s1['temp_c']}C "
              f"err=0x{s1['err']:04X} pos={bus.angle(mid):+.2f}deg "
              f"speed={s2['speed']} amps={s2['amps']:+.2f}")
    bus.shutdown()
    return True


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        ok, _ = cmd_check()
    elif cmd == "status":
        ok = cmd_status()
    elif cmd == "open":
        ok = cmd_drive(+1)
    elif cmd == "close":
        ok = cmd_drive(-1)
    elif cmd == "stop":
        ok = cmd_stop()
    elif cmd == "all":
        # check -> full open -> full close -> stop. Refuses to move on a failed check.
        ok, found = cmd_check()
        if not ok:
            print("\nRefusing to move: connection check failed.")
        else:
            print()
            ok_open = cmd_drive(+1, found)
            print()
            ok_close = cmd_drive(-1, found)
            cmd_stop()
            ok = ok_open and ok_close
    else:
        print(__doc__)
        return 2
    print("\n" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
