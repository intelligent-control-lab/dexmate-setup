# dexmate-setup

[Official Dexmate manual](https://platform.dexmate.ai/) — For this setup, you generally only need the **Network** and **Software Setup** sections.

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

### Camera startup

The installer enables `wrist-camera-init.service` for boot-time initialization. Wrist capture
starts on demand through `WristCameras()`. The head uses the vendor's `dexsensor.service`;
`--configure-head` configures it but does not enable it. After installation, enable both:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dexsensor.service wrist-camera-init.service
```

See the manual's [camera startup](https://intelligent-control-lab.github.io/dexmate-setup/en.html#camera-autostart)
and [troubleshooting](https://intelligent-control-lab.github.io/dexmate-setup/en.html#camera-troubleshooting) instructions.

## What is included

| Path | Purpose |
|---|---|
| `software/gripper/` | Grippers/Motor library and connection/self-test tool |
| `software/wrist_cameras/` | On-demand dual RGB API, initialization and trigger worker |
| `software/poses/` | Latest robot-exported ready/rest, head and pose scripts |
| `drivers/` | Exact-kernel modules, overlay, checksums and rebuild inputs |
| `config/` | CAN/wrist services, tmpfiles and captured dexsensor template |
| `scripts/` | Installer, initrd builder, read-only doctor, site generator |
| `docs/` | Original manual, hardware setup, calibration/URDF reference, Chinese translation, photos and videos |
| `provenance/` | Original source hashes, package versions and validation limits |

## Calibration and URDF reference

[Hardware and control measurements](https://intelligent-control-lab.github.io/dexmate-setup/en.html#hardware-control-reference) · [TCP and camera extrinsics](https://intelligent-control-lab.github.io/dexmate-setup/en.html#tcp-extrinsics)

- Supplied package models: [vega_1u.urdf](docs/files/urdf/vega_1u.urdf) and [vega_1u_gripper.urdf](docs/files/urdf/vega_1u_gripper.urdf).
- [Clean calibration pair](docs/files/calibration/clean-20260924.json), [pivot-fit result](docs/files/calibration/tcp-pivot-fit.json), and [earlier Y-adjusted pair](docs/files/calibration/adjusted-20260924.json).
- [Reference matrices and file hashes](docs/files/reference-data.json), including the separate custom URDF nominal TCP.

## Maintain the site

The supplied original is preserved in `manual/vega1umanual.html`. The website keeps its
layout, commands and examples. Part B contains mandatory chapters B1–B8: gripper hardware,
PCB/camera hardware, network, certificates, workstation communication, libraries, verification,
and cameras. Part C contains advanced references, hardware/control information and TCP/extrinsics.
Chinese prose for the original chapters is in `manual/zh.json`.

Edit `manual/hardware.en.html` / `manual/hardware.zh.html` for hardware setup and
`manual/reference.en.html` / `manual/reference.zh.html` for calibration references.
Camera startup and troubleshooting additions are in `manual/camera-help.en.html` /
`manual/camera-help.zh.html`. Chapter order and numbering are set in `scripts/build_docs.py`. Then:

```bash
python3 scripts/build_docs.py
python3 -m unittest discover -s tests -v
python3 scripts/check_site.py
python3 scripts/check_reference.py
python3 -m http.server 8000 --directory docs
```

GitHub Pages publishes **main /docs**. No frontend build system or API keys are required.
