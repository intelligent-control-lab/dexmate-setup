# Exact-kernel driver bundle

These ARM64 modules and overlay are for **L4T 36.5.0 / 5.15.185-tegra,
p3767-0005 Orin Nano 8GB on p3768**, with the matched ZED Link baseline only.
Do not install on other Jetsons or use them to bypass package dependencies.

| Artifact | Purpose |
|---|---|
| `gs_usb.ko` | RH-02 USB-CAN, built against the source robot's kernel |
| `tegra-camera.ko` | Nested GPIO/I²C mux parent-walk patch |
| `isx031-gmsl-camera-b.ko` | MAX9295 identification and 3 Gbps register tables |
| `tegra234-head-wrists.dtbo` | Combined CAM0 head / CAM1 dual-wrist topology |

Verify with `cd drivers && sha256sum -c SHA256SUMS` on Linux.
The installer checks hashes, platform, package version and module vermagic before boot changes.

## Rebuild inputs

- `source/gs_usb.c`: captured Linux gs_usb source, retaining its license notice.
  On a matching target with kernel headers:

  ```bash
  mkdir -p /tmp/dexmate-gs-usb
  cp drivers/source/gs_usb.c /tmp/dexmate-gs-usb/
  printf 'obj-m += gs_usb.o\n' > /tmp/dexmate-gs-usb/Makefile
  make -C /lib/modules/$(uname -r)/build M=/tmp/dexmate-gs-usb modules
  ```

- `source/build_candidate.py`, `zedlink-original.dts` and `wrist-original.dts`:
  decompiled vendor-overlay inputs and the combined-overlay generator. Run a copy in
  a temporary working directory, then compile with `dtc -@ -I dts -O dtb`.
  `source/head-wrists.dts` is the robot-exported generated topology.
- `source/sensor-common-nested-gpio-mux.patch`, `sensor_common.original.c`,
  `sensor_common.nested.c`: the exact camera-framework change. Rebuilding the module
  additionally requires matching NVIDIA L4T kernel/oot sources, headers, configuration,
  symbol versions and toolchain. The full NVIDIA source tree is not vendored here.
- `source/patch_wrist_driver.py` plus `isx031-gmsl-camera-b.original.ko`:
  deterministic transformation of the exact original Waveshare module. The script checks
  the original hash. Run in a temporary copy; compare the generated module with the bundle.
  This is a version-pinned binary adaptation, not a portable replacement for upstream source.

## Boot strategy

`scripts/build_initrd.py` extracts **the new robot's own** NVIDIA initrd, checks the exact
switch-root anchor, embeds patched camera modules and re-extracts the result to verify
contents, symlinks and regular-file modes. Unknown multi-archive layouts are refused.
`scripts/boot_config.py` copies the target robot's Stereolabs LINUX/FDT/APPEND values,
adds a new label, and preserves all previous boot entries. DEFAULT changes only with
`--activate-camera-boot`. No old machine's root PARTUUID or initrd is distributed.

Camera modules are supplied through per-boot read-only bind mounts. A missing wrist module
target is populated from the bundled module and indexed by depmod. An existing original
wrist module is retained. Do not hot-unload the camera stack; use a console-accessible boot
entry for recovery. This packaging still needs new-robot cold-boot acceptance.
