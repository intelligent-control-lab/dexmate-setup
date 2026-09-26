#!/usr/bin/env python3
"""Read-only setup status. Does not construct Robot(), poll CAN, or initialize cameras."""
import json
from pathlib import Path
import platform
import re
import subprocess
import sys


def main():
    failed = []
    print("Kernel:", platform.release())
    if platform.release() != "5.15.185-tegra":
        failed.append("kernel mismatch")
    for service in ("dexsensor", "wrist-camera-init", "can1"):
        result = subprocess.run(["systemctl", "is-active", service], text=True, capture_output=True)
        print(service + ":", result.stdout.strip())
        if result.returncode:
            failed.append(service + " is not active")
    try:
        ready = json.loads(Path("/run/wrist-cameras/ready.json").read_text())
        if ready["boot_id"] != Path("/proc/sys/kernel/random/boot_id").read_text().strip():
            failed.append("stale camera initialization marker")
        print("Wrist devices:", ready["devices"])
    except (OSError, KeyError, ValueError) as error:
        failed.append("no valid wrist readiness marker: " + str(error))
    result = subprocess.run(["ip", "-details", "link", "show", "can1"], capture_output=True, text=True)
    print(result.stdout or result.stderr)
    if result.returncode or "bitrate 1000000" not in result.stdout or not re.search(r"<[^>]*\bUP\b[^>]*>", result.stdout):
        failed.append("can1 missing, down, or not at 1 Mbit/s")
    for node in sorted(Path("/sys/class/video4linux").glob("video*")):
        print("/dev/" + node.name, (node / "name").read_text().strip())
    print("This status check does not prove video frames, CAN replies, or safe motion.")
    if failed:
        print("\n".join("FAIL: " + item for item in failed))
        return 1
    print("PASS: static/service prerequisites. Continue with supervised acceptance in the manual.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
