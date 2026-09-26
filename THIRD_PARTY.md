# Sources and third-party materials

- Custom gripper, pose and wrist initialization files: exported from the lab's Vega-1U;
  see `provenance/source-files.json`. This repository does not relicense third-party files.
- `drivers/source/gs_usb.c` carries its upstream GPL notice. Its bundled module targets
  `5.15.185-tegra`; rebuilding for another kernel requires matching headers and review.
- The camera framework module derives from NVIDIA's L4T 36.5 sources and the included
  nested-I²C-mux patch. The wrist module is the version-pinned Waveshare module adapted for
  MAX9295 / 3 Gbps by the included patch script. See `drivers/README.md` for reproducibility.
- ZED SDK, ZED Link and dexsensor vendor installers are not included in the public repository.
  Their exact names/hashes and official acquisition pages are in `provenance/vendor-installers.json`.
- Python dependencies are installed from their upstream distributions at the captured versions.
  Their licenses and transitive dependencies remain those of the respective upstream projects.
- Three `waveshare-*.webp` product photographs came from user-supplied Waveshare assets;
  credit: [Waveshare hardware guide](https://docs.waveshare.com/MAX9296-GMSL-Deser-Module/Jetson-Orin).
  `jetson-board.jpg` and `jetson-pinout.png` were also supplied by the user as hardware references.
- `IMG_*.jpg` and `IMG_*.mp4` are the user's installation photos/videos, converted for web use.
  EXIF/QuickTime metadata were removed; original video audio is preserved. Original files remain outside Git.
- `manual/vega1umanual.html` preserves the supplied English field manual. The bilingual website
  appends the requested hardware, control and calibration reference chapters.
- `docs/files/urdf/vega_1u.urdf` and `vega_1u_gripper.urdf` are user-supplied files matching
  `dexmate_urdf` 0.8.4. The separately labeled `urdf/custom/` model comes from the lab's
  calibration project. Their existing notices and licensing remain unchanged.
- `docs/files/calibration/` contains the requested lab calibration records. Source paths,
  hashes and the referenced task identifiers are recorded in `docs/files/reference-data.json`.
