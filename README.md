# dexmate-setup

[中文手册](https://intelligent-control-lab.github.io/dexmate-setup/) · [English manual](https://intelligent-control-lab.github.io/dexmate-setup/en.html)

Vega-1U setup kit: robot-exported gripper library, dual-wrist camera initialization/API,
pose scripts, pinned camera/CAN drivers, and an illustrated bilingual GitHub Pages manual.

面向新 Vega-1U 的安装仓库：夹爪控制、双腕相机初始化与读取、位姿脚本、精确版本驱动，
以及包含实拍照片和两段 walkthrough 的中英文手册。

**Hardware correction / 接线更正:** Jetson header pins **2 and 4 are 5V**, pin **6 is GND**.
The grippers' 24V supply is a separate circuit. Never connect 24V to these 5V header pins.

## Quick start / 快速安装

Target: **Orin Nano 8GB (p3767-0005 / p3768), L4T 36.5.0, Linux 5.15.185-tegra,
aarch64, system Python 3.10, firmware 0.5.x**.
Prepare the robot's own certificate and matching vendor baseline first:
ZED SDK 5.2.3, ZED Link Duo 1.4.3-LI-MAX96712-L4T36.5.0 and dexsensor 0.7.6.
Exact vendor filenames/hashes: [vendor-installers.json](provenance/vendor-installers.json).

```bash
git clone https://github.com/intelligent-control-lab/dexmate-setup.git
cd dexmate-setup
/usr/bin/python3 scripts/install.py  # read-only plan / 只显示计划

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

安装器检查型号和版本、备份被替换文件、保留原启动项，并使用新机自己的磁盘参数。
它不自动重启或执行动作。厂商基础软件和本机证书需要单独准备；Python 依赖联网安装。

## What is included / 仓库内容

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

## Validation scope / 验证范围

- Exported from the source robot on **2026-09-26** without motion or service changes.
- No second-robot installation, cold boot or live motion acceptance is claimed.
- `Robot()` can home the head even in a pose `--dry-run`; the manual calls this out.
- `goto_pose.py` now refuses a missing FK guard and invalid step/wait values before proceeding.
- Robot certificates, private keys, per-robot calibration files and vendor installers are excluded.

See [export status](provenance/STATUS.md), [third-party sources](THIRD_PARTY.md).

## Maintain the site / 更新网站

The supplied original is preserved in `manual/vega1umanual.html`. The website keeps its
layout, sections, commands and examples. Only B10 (gripper hardware) and B11 (PCB/camera
hardware) are added. Chinese prose is in `manual/zh.json`.

沿用原手册，只新增 B10「夹爪硬件连接」和 B11「PCB 与相机硬件安装」。

Edit `manual/hardware.en.html` and `manual/hardware.zh.html` for the two added chapters, then:

```bash
python3 scripts/build_docs.py
python3 -m unittest discover -s tests -v
python3 scripts/check_site.py
python3 -m http.server 8000 --directory docs
```

GitHub Pages publishes **main /docs**. No frontend build system or API keys are required.
