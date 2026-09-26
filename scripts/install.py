#!/usr/bin/env python3
"""Install local Vega-1U software. Default is a read-only plan; --apply writes files.

Does not command joints, start CAN/camera services, install certificates, or reboot.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from boot_config import camera_entry
from build_initrd import build, KERNEL

ROOT = Path(__file__).resolve().parents[1]
APT = ["python3-venv", "python3-pip", "python3-numpy", "python3-gi", "python3-gst-1.0",
       "gir1.2-gstreamer-1.0", "gir1.2-gst-plugins-base-1.0", "gstreamer1.0-tools",
       "gstreamer1.0-plugins-base", "gstreamer1.0-plugins-good", "gstreamer1.0-plugins-bad",
       "i2c-tools", "v4l-utils", "can-utils", "psmisc", "kmod", "initramfs-tools-core", "cpio"]


def run(*args):
    print("+", shlex.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def verify_bundle():
    for line in (ROOT / "drivers/SHA256SUMS").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        path = ROOT / "drivers" / name.strip()
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Driver checksum mismatch: " + str(path))


def preflight():
    errors = []
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        errors.append("Requires Linux aarch64 on Jetson Orin Nano 8GB")
    if platform.release() != KERNEL:
        errors.append("Requires exact kernel " + KERNEL + "; will not downgrade it")
    if sys.version_info[:2] != (3, 10):
        errors.append("Run /usr/bin/python3 (Python 3.10), outside conda")
    compatible = Path("/proc/device-tree/compatible")
    if not compatible.exists() or b"nvidia,p3768-0000+p3767-0005" not in compatible.read_bytes():
        errors.append("Requires p3768 carrier with p3767-0005 module")
    release = Path("/etc/nv_tegra_release")
    if not release.exists() or not re.search(r"# R36 .*REVISION: 5\.0,", release.read_text()):
        errors.append("Requires L4T 36.5.0")
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--user", default="dexmate")
    p.add_argument("--robot-name", help="THIS robot's dm/<serial>-1u name, required for --apply")
    p.add_argument("--install-deps", action="store_true", help="Install apt packages and pinned Python dependencies")
    p.add_argument("--camera-boot", action="store_true", help="Build a separate initrd and add an extlinux entry")
    p.add_argument("--activate-camera-boot", action="store_true", help="Select the new camera entry for the next boot")
    p.add_argument("--configure-head", action="store_true", help="Back up and replace dexsensor config with the captured template")
    a = p.parse_args()
    if a.activate_camera_boot and not a.camera_boot:
        p.error("--activate-camera-boot requires --camera-boot")
    verify_bundle()
    errors = preflight()
    print("Plan: install gripper/pose libraries, wrist API, CAN module and service files; enable at NEXT boot.")
    print("Python environment: /opt/dexmate-setup/venv; backups: /var/backups/dexmate-setup/<timestamp>")
    print("Camera boot:", a.camera_boot, "change DEFAULT:", a.activate_camera_boot, "configure head:", a.configure_head)
    if errors:
        print("\n".join("BLOCKED: " + e for e in errors))
    if not a.apply:
        print("PLAN ONLY: no changes made. Add --apply on a compatible robot.")
        return 1 if errors else 0
    if errors:
        raise SystemExit("Platform mismatch; nothing installed")
    if os.geteuid() != 0:
        p.error("--apply requires sudo")
    if not a.robot_name or not re.fullmatch(r"dm/[A-Za-z0-9_-]+-1u", a.robot_name):
        p.error("--robot-name must be THIS robot's dm/<serial>-1u identifier")
    account = pwd.getpwnam(a.user)
    if account.pw_uid == 0:
        p.error("--user must be a regular operator account")
    modules = ROOT / "drivers" / KERNEL
    boot = Path("/boot/extlinux/extlinux.conf")
    boot_text = fields = None
    if a.camera_boot:
        boot_text, fields = camera_entry(boot.read_text(), a.activate_camera_boot)
        for key in ("LINUX", "FDT", "INITRD"):
            path = Path(fields[key])
            if not path.is_absolute() or not path.is_file():
                raise SystemExit("Boot prerequisite missing: " + str(path))
        if not Path("/usr/local/zed/lib").is_dir():
            raise SystemExit("Install the matching ZED SDK first")
        version = subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", "stereolabs-zedlink-duo"], text=True)
        if version != "1.4.3-LI-MAX96712-L4T36.5.0":
            raise SystemExit("ZED Link package version mismatch: " + version)
        framework = Path("/usr/lib/modules") / KERNEL / "updates/drivers/media/platform/tegra/camera/tegra-camera.ko"
        if not framework.is_file():
            raise SystemExit("Original NVIDIA camera framework is missing")
    if a.configure_head:
        version = subprocess.check_output(["dpkg-query", "-W", "-f=${Version}", "dexsensor"], text=True)
        if version != "0.7.6":
            raise SystemExit("Expected dexsensor 0.7.6; refusing to replace another version's config")
    if a.install_deps:
        run("apt-get", "update")
        run("apt-get", "install", "-y", *APT)
    for name in ("modinfo", "depmod", "systemctl"):
        if shutil.which(name) is None:
            raise SystemExit("Missing " + name + "; use --install-deps")
    for module in modules.glob("*.ko"):
        magic = subprocess.check_output(["modinfo", "-F", "vermagic", str(module)], text=True)
        if not magic.startswith(KERNEL + " ") or "aarch64" not in magic:
            raise SystemExit("Module ABI mismatch: " + str(module))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = Path("/var/backups/dexmate-setup") / stamp
    backup.mkdir(parents=True)
    manifest = {"created": stamp, "files": [], "note": "Services are enabled but not started; no reboot or robot motion"}

    def put_bytes(data, destination, mode=0o644):
        destination = Path(destination)
        existed = destination.exists()
        if destination.is_symlink():
            raise ValueError("Refusing to overwrite symlink " + str(destination))
        if existed:
            old = backup / destination.relative_to("/")
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, old)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".dexmate-new")
        temp.write_bytes(data); temp.chmod(mode); temp.replace(destination)
        manifest["files"].append({"path": str(destination), "existed": existed})
        (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    with tempfile.TemporaryDirectory(prefix="dexmate-install-") as tmp:
        if a.camera_boot:
            prepared_initrd = Path(tmp) / "initrd"
            build(fields["INITRD"], modules, prepared_initrd)
        # A fresh versioned runtime keeps previous environments available for recovery.
        runtime = Path("/opt/dexmate-setup")
        for source in (ROOT / "software").rglob("*.py"):
            put_bytes(source.read_bytes(), runtime / source.relative_to(ROOT / "software"))
        for source in (ROOT / "software/wrist_cameras").glob("*.py"):
            put_bytes(source.read_bytes(), Path("/opt/wrist-cameras") / source.name)
        venv = runtime / "venv"
        if not (venv / "bin/python").is_file():
            run("/usr/bin/python3", "-m", "venv", "--system-site-packages", str(venv))
        if a.install_deps:
            run(venv / "bin/python", "-m", "pip", "install", "-r", ROOT / "requirements.txt")
        put_bytes(b"/opt/wrist-cameras\n", "/usr/local/lib/python3.10/dist-packages/wrist_cameras_local.pth")
        put_bytes(b"/opt/dexmate-setup/gripper\n/opt/dexmate-setup/poses\n/opt/wrist-cameras\n",
                  venv / "lib/python3.10/site-packages/dexmate_setup.pth")
        run(venv / "bin/python", "-c", "import can,numpy,pinocchio,dexmate_urdf,dexcontrol,gi; gi.require_version('Gst','1.0'); from gi.repository import Gst")
        for name, destination in [("wrist-camera-init.service", "/etc/systemd/system/wrist-camera-init.service"),
                                  ("can1.service", "/etc/systemd/system/can1.service"),
                                  ("wrist-cameras.conf", "/etc/tmpfiles.d/wrist-cameras.conf")]:
            put_bytes((ROOT / "config" / name).read_bytes(), destination)
        for group in ("i2c", "video"):
            run("groupadd", "-f", group)
            run("usermod", "-aG", group, a.user)
        put_bytes(b"gs_usb\n", "/etc/modules-load.d/dexmate-gripper.conf")
        put_bytes((modules / "gs_usb.ko").read_bytes(), Path("/usr/lib/modules") / KERNEL / "kernel/drivers/net/can/usb/gs_usb.ko")
        if a.camera_boot:
            wrist_target = Path("/usr/lib/modules") / KERNEL / "updates/drivers/media/i2c/isx031-gmsl-camera-b.ko"
            # Provide a mount target and module index on a robot without the wrist package.
            if not wrist_target.exists():
                put_bytes((modules / "isx031-gmsl-camera-b.ko").read_bytes(), wrist_target)
            put_bytes((modules / "tegra234-head-wrists.dtbo").read_bytes(), "/boot/tegra234-dexmate-setup.dtbo")
            put_bytes(prepared_initrd.read_bytes(), "/boot/initrd-dexmate-setup")
        if a.configure_head:
            head_config = (ROOT / "config/dexsensor.reference.toml").read_text()
            head_config = head_config.replace('name = "default"', 'name = "' + a.robot_name + '"', 1)
            put_bytes(head_config.encode(), "/etc/dexmate/dexsensor/default.toml")
            put_bytes(("[Service]\nEnvironment=ROBOT_NAME=" + a.robot_name + "\n").encode(),
                      "/etc/systemd/system/dexsensor.service.d/20-dexmate-setup.conf")
        env = ("export ROBOT_NAME=" + shlex.quote(a.robot_name) + "\n"
               "source /opt/dexmate-setup/venv/bin/activate\n")
        put_bytes(env.encode(), "/opt/dexmate-setup/env.sh")
        run("depmod", "-a", KERNEL)
        run("systemctl", "daemon-reload")
        run("systemd-tmpfiles", "--create", "/etc/tmpfiles.d/wrist-cameras.conf")
        run("systemctl", "enable", "can1.service", "wrist-camera-init.service")
        # Commit boot selection last, after all payload and service operations succeed.
        if a.camera_boot:
            put_bytes(boot_text.encode(), boot)
    print("Installed. Backup:", backup)
    print("Log in again for group membership. Review the boot entry; reboot manually with console access.")
    print("After boot: source /opt/dexmate-setup/env.sh; python3 scripts/doctor.py")
    print("Certificates, vendor firmware, and network configuration remain robot-specific.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
