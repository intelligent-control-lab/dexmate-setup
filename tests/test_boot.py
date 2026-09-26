import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from boot_config import camera_entry, LABEL
from build_initrd import patch_init, ANCHOR

BASE = '''TIMEOUT 30
DEFAULT Stereolabs
LABEL primary
    LINUX /boot/Image
    APPEND root=PARTUUID=NEW-ROBOT-DISK rw
LABEL Stereolabs
    MENU LABEL Stereolabs kernel
    LINUX /boot/Image
    FDT /boot/dtb/kernel_tegra234-p3768-0000+p3767-0005-nv-super.dtb
    INITRD /boot/initrd
    APPEND ${cbootargs} root=PARTUUID=NEW-ROBOT-DISK rw rootwait
    OVERLAYS /boot/vendor.dtbo
'''


class BootTests(unittest.TestCase):
    def test_preserves_target_root_and_fallback(self):
        text, _ = camera_entry(BASE, True)
        self.assertIn("DEFAULT " + LABEL, text)
        self.assertIn("root=PARTUUID=NEW-ROBOT-DISK", text.split("LABEL " + LABEL)[1])
        self.assertIn("LABEL Stereolabs", text)
        self.assertIn("OVERLAYS /boot/vendor.dtbo", text)

    def test_stage_does_not_change_default(self):
        text, _ = camera_entry(BASE)
        self.assertIn("DEFAULT Stereolabs", text)

    def test_rerun_is_idempotent(self):
        one, _ = camera_entry(BASE, True)
        two, _ = camera_entry(one, True)
        self.assertEqual(one, two)

    def test_wrong_board_missing_root_or_missing_vendor_refused(self):
        for bad in (BASE.replace("p3767-0005", "p3767-0001"),
                    BASE.replace("root=", "other="), BASE.replace("LABEL Stereolabs", "LABEL other")):
            with self.assertRaises(ValueError):
                camera_entry(bad)

    def test_initrd_retains_switch_root_and_both_patches(self):
        text = patch_init("#!/bin/sh\n" + ANCHOR + "\nswitch_root /mnt /sbin/init\n")
        self.assertEqual(text.count(ANCHOR), 1)
        self.assertIn("switch_root /mnt /sbin/init", text)
        self.assertIn("/sys/module/tegra_camera", text)
        self.assertIn("/sys/module/isx031_gmsl_camera_b", text)
        self.assertEqual(text.count("mount --bind"), 2)

    def test_unknown_or_double_patched_initrd_refused(self):
        for bad in ("no anchor", ANCHOR * 2, patch_init(ANCHOR)):
            with self.assertRaises(ValueError):
                patch_init(bad)


if __name__ == "__main__":
    unittest.main()
