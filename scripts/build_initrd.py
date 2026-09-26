#!/usr/bin/env python3
"""Patch a supported NVIDIA initrd copied from the TARGET robot, never the source disk."""
import argparse
import gzip
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

KERNEL = "5.15.185-tegra"
MODULES = {
    "tegra-camera.ko": "updates/drivers/media/platform/tegra/camera/tegra-camera.ko",
    "isx031-gmsl-camera-b.ko": "updates/drivers/media/i2c/isx031-gmsl-camera-b.ko",
}
ANCHOR = 'echo "Switching from initrd to actual rootfs" > /dev/kmsg;'


def patch_init(text):
    if text.count(ANCHOR) != 1 or "dexmate-setup: staged" in text:
        raise ValueError("Unsupported or already patched initrd; expected one NVIDIA switch-root anchor")
    additions = []
    for name, relative in MODULES.items():
        module_name = name.removesuffix(".ko").replace("-", "_")
        target = "/mnt/usr/lib/modules/" + KERNEL + "/" + relative
        additions.append(f'''# Dexmate setup: preserve the original on-disk module for fallback boots.
if [ ! -d /sys/module/{module_name} ] && [ -f {target} ]; then
    if mount --bind /head-wrists/{name} {target}; then
        mount -o remount,bind,ro {target}
        echo "dexmate-setup: staged {name}" > /dev/kmsg
    else
        echo "dexmate-setup: bind failed for {name}" > /dev/kmsg
    fi
else
    echo "dexmate-setup: early module or missing target {name}" > /dev/kmsg
fi
''')
    return text.replace(ANCHOR, "\n".join(additions) + "\n" + ANCHOR)


def build(base, modules, destination):
    base, modules, destination = map(Path, (base, modules, destination))
    if base.resolve() == destination.resolve():
        raise ValueError("Output must not overwrite the base initrd")
    with tempfile.TemporaryDirectory(prefix="dexmate-initrd-") as tmp:
        tree = Path(tmp) / "tree"
        subprocess.run(["unmkinitramfs", str(base), str(tree)], check=True)
        # Multiple early/main archives need a different reconstruction procedure.
        if not (tree / "init").is_file() or (tree / "main").exists():
            raise ValueError("Unsupported multi-archive initrd layout; no boot config was changed")
        init = tree / "init"
        init.write_text(patch_init(init.read_text()))
        subprocess.run(["bash", "-n", str(init)], check=True)
        (tree / "head-wrists").mkdir(exist_ok=True)
        for name in MODULES:
            shutil.copy2(modules / name, tree / "head-wrists" / name)
        archive = Path(tmp) / "new.cpio.gz"
        with archive.open("wb") as output:
            find = subprocess.Popen(["find", ".", "-print0"], cwd=tree, stdout=subprocess.PIPE)
            cpio = subprocess.Popen(["cpio", "--null", "-o", "--format=newc", "--owner=0:0"],
                                    cwd=tree, stdin=find.stdout, stdout=subprocess.PIPE)
            find.stdout.close()
            gz = subprocess.Popen(["gzip", "-9"], stdin=cpio.stdout, stdout=output)
            cpio.stdout.close()
            statuses = [gz.wait(), cpio.wait(), find.wait()]
        if any(statuses):
            raise RuntimeError("initrd archive pipeline failed: " + str(statuses))
        verify = Path(tmp) / "verify"
        subprocess.run(["unmkinitramfs", str(archive), str(verify)], check=True)
        for path in tree.rglob("*"):
            other = verify / path.relative_to(tree)
            if path.is_symlink():
                if not other.is_symlink() or path.readlink() != other.readlink():
                    raise ValueError("initrd symlink verification failed: " + str(path))
            elif path.is_file():
                if not other.is_file() or path.read_bytes() != other.read_bytes():
                    raise ValueError("initrd content verification failed: " + str(path))
                if path.stat().st_mode & 0o7777 != other.stat().st_mode & 0o7777:
                    raise ValueError("initrd mode verification failed: " + str(path))
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".new")
        shutil.copyfile(archive, temporary)
        temporary.chmod(0o644)
        temporary.replace(destination)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True)
    p.add_argument("--modules", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    print(build(a.base, a.modules, a.output))
