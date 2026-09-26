"""Build an additive extlinux entry using THIS robot's root disk and boot files."""
import re

LABEL = "DexmateSetupHeadWrists"


def camera_entry(text, activate=False):
    blocks = re.split(r"(?m)^(?=LABEL\s+)", text)
    candidates = {}
    for block in blocks:
        match = re.match(r"LABEL\s+(\S+)", block)
        if match:
            candidates[match[1]] = block
    if "Stereolabs" not in candidates:
        raise ValueError("Install the matching ZED Link driver first: Stereolabs boot entry is required")
    fields = {}
    for line in candidates["Stereolabs"].splitlines()[1:]:
        match = re.match(r"\s*(LINUX|INITRD|FDT|APPEND)\s+(.+)$", line)
        if match:
            fields[match[1]] = match[2]
    if not {"LINUX", "FDT", "APPEND", "INITRD"} <= fields.keys():
        raise ValueError("Incomplete Stereolabs entry; preserve and inspect extlinux manually")
    if "p3768-0000+p3767-0005" not in fields["FDT"]:
        raise ValueError("Unexpected carrier/module DTB; this bundle is for p3768 + p3767-0005")
    if "root=" not in fields["APPEND"]:
        raise ValueError("Source boot entry has no root device")
    kept = "".join(b for b in blocks if not re.match(r"LABEL\s+" + LABEL + r"\s*(?:\n|$)", b))
    if activate:
        if not re.search(r"(?m)^DEFAULT\s+", kept):
            raise ValueError("Missing DEFAULT; refusing to guess boot policy")
        kept = re.sub(r"(?m)^DEFAULT\s+\S+.*$", "DEFAULT " + LABEL, kept)
    entry = ["LABEL " + LABEL, "    MENU LABEL Dexmate setup - head and both wrists",
             "    LINUX " + fields["LINUX"], "    FDT " + fields["FDT"],
             "    INITRD /boot/initrd-dexmate-setup", "    APPEND " + fields["APPEND"],
             "    OVERLAYS /boot/tegra234-dexmate-setup.dtbo"]
    return kept.rstrip() + "\n\n" + "\n".join(entry) + "\n", fields
