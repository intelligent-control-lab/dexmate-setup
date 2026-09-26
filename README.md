# dexmate-setup

[Chinese manual](https://intelligent-control-lab.github.io/dexmate-setup/) · [English manual](https://intelligent-control-lab.github.io/dexmate-setup/en.html)

Vega-1U setup kit: robot-exported gripper library, dual-wrist camera initialization/API,
pose scripts, pinned camera/CAN drivers, and an illustrated bilingual GitHub Pages manual.

## Quick start

Target: **Orin Nano 8GB (p3767-0005 / p3768), L4T 36.5.0, Linux 5.15.185-tegra,
aarch64, system Python 3.10, firmware 0.5.x**.
Prepare the robot's own certificate and matching vendor baseline first:
ZED SDK 5.2.3, ZED Link Duo 1.4.3-LI-MAX96712-L4T36.5.0 and dexsensor 0.7.6.
Exact vendor filenames/hashes: [vendor-installers.json](provenance/vendor-installers.json).

```bash
git clone https://github.com/intelligent-control-lab/dexmate-setup.git
cd dexmate-setup
/usr/bin/python3 scripts/install.py  # read-only plan

# Use THIS robot's serial, not the source robot's identity.
sudo /usr/bin/python3 scripts/install.py --apply \
  --robot-name dm/YOUR_SERIAL-1u --user dexmate \
  --install-deps --camera-boot --activate-camera-boot --configure-head
```

Review the generated boot entry, then reboot manually with a display/keyboard available.
Log in again for group membership, then:

```bash
source /opt/dexmate-setup/env.sh
cd ~/dexmate-setup  # or your actual clone path
python3 scripts/doctor.py
```

The installer preserves the target robot's root disk arguments and original boot entries,
backs up replaced files, and does not start services, reboot, or command motors.
Omit `--activate-camera-boot` to stage the camera boot entry without selecting it.
The dependency installation needs Internet access; this is not an offline factory image.

## What is included

| Path | Purpose |
|---|---|
| `software/gripper/` | Grippers/Motor library and connection/self-test tool |
| `software/wrist_cameras/` | On-demand dual RGB API, initialization and trigger worker |
| `software/poses/` | Latest robot-exported ready/rest, head and pose scripts |
| `drivers/` | Exact-kernel modules, overlay, checksums and rebuild inputs |
| `config/` | CAN/wrist services, tmpfiles and captured dexsensor template |
| `scripts/` | Installer, initrd builder, read-only doctor, site generator |
| `docs/` | Original manual with two added hardware chapters, Chinese translation, photos and videos |
| `provenance/` | Original source hashes, package versions and validation limits |

## Maintain the site

The supplied original is preserved in `manual/vega1umanual.html`. The website keeps its
layout, sections, commands and examples. Only B10 (gripper hardware) and B11 (PCB/camera
hardware) are added. Chinese prose is in `manual/zh.json`.

Edit `manual/hardware.en.html` and `manual/hardware.zh.html` for the two added chapters, then:

```bash
python3 scripts/build_docs.py
python3 -m unittest discover -s tests -v
python3 scripts/check_site.py
python3 -m http.server 8000 --directory docs
```

GitHub Pages publishes **main /docs**. No frontend build system or API keys are required.
