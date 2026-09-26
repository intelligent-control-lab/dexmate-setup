# Export status — 2026-09-26

Custom gripper code, the latest pose scripts, `/opt/wrist-cameras`, systemd/tmpfiles configuration,
the installed camera overlay and version-specific CAN/camera modules were read over SSH from
the source Vega-1U. No motors were commanded, services restarted, camera registers written,
or robot configuration changed during export.

The source machine runs L4T 36.5.0 / `5.15.185-tegra`, p3768 + p3767-0005.

The installer is new packaging code. Static/unit checks and target dependency resolution are
separate from installation on a second robot, cold-boot acceptance and live motion tests.
No new-robot install, reboot, or physical movement is claimed.

`source-files.json` records original imported file hashes. Packaged `goto_pose.py` additionally
refuses missing FK dependencies, rejects invalid step/wait/clearance parameters, rejects banned
folded poses before `Robot()`, and corrects the dry-run message. All other exported runtime Python
files retain their source bytes unless explicitly noted in version control.

The source's `goto_ready.py` was updated September 21–23, after the supplied manual: it uses
right-arm-first, step 0.04 rad, wait 0.8 s and head radians approximately `[0, 0, -0.505622]`.
Those are reference robot values, not camera calibration for a replacement robot.

The supplied manual is retained as the website source, with the requested hardware chapters,
hardware/control and calibration references, and a corresponding Chinese translation.
Robot certificates, private keys and per-robot calibration files are excluded from the software
export. The separately requested calibration reference records are available in
`docs/files/calibration/`; they are not installed on new robots by the installer.

## Packaging checks completed

- 9 unit tests pass: target disk/fallback preservation, idempotence, unsupported boot/initrd rejection, and pose refusal paths without Robot construction.
- 37 CPython 3.10 / Linux aarch64 wheels resolved, downloaded, and rechecked against the committed SHA256 lock; this is resolution validation, not target import/runtime validation.
- Wrist binary adaptation reproduced the exported module byte-for-byte.
- The bilingual pages pass local asset/fragment checks. Original English chapter bodies are checked against the supplied manual, allowing the requested renumbering, workstation badge and camera-help additions; Chinese pages retain the same command blocks.
- Source /boot/initrd hash still matches the historical baseline; no boot files were changed.
- Historical software README files have context banners; the arm README robot identifier was replaced by a placeholder.
