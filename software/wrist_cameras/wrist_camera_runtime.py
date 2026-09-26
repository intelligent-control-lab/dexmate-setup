"""Run on the robot with sudo; temporary, bounded wrist-camera diagnostic.

Requires the isolated MAX9295/3Gbps module already loaded and aliases A=0x44,
B=0x42. Does not load modules, change boot files, or manipulate host GPIO/CAN.
Vendor sensor initialization is optional; software pulses are diagnostic only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

BUS = 9


def read(address, register):
    return int(subprocess.check_output([
        'i2ctransfer', '-y', str(BUS), f'w2@{address:#x}',
        hex(register >> 8), hex(register & 255), 'r1'], text=True, stderr=subprocess.PIPE, timeout=3).strip(), 16)


def write(address, register, value):
    subprocess.run(['i2ctransfer', '-y', str(BUS), f'w3@{address:#x}',
                    hex(register >> 8), hex(register & 255), hex(value)],
                   check=True, capture_output=True, timeout=3)


CAMERAS = (0x44, 0x42)
VIDEO = {
    0x44: [(2, 3), (0x330, 0), (0x331, 0x33), (0x332, 0xe0),
           (0x333, 4), (0x316, 0x5e), (0x318, 0), (0x311, 0xf0),
           (0x308, 0x7e), (0x57, 0x11), (2, 0x23)],
    0x42: [(2, 3), (0x330, 0), (0x331, 0x33), (0x332, 0xe0),
           (0x333, 4), (0x316, 0), (0x318, 0x5e), (0x311, 0x55),
           (0x308, 0x7c), (0x5b, 0x12), (2, 0x43)],
}
VENDOR = [(0x2be, 0), (0x318, 0x5e), (6, 0xb0), (0x3f0, 0x59), (3, 3)]
VENDOR_RELEASE = [(0x2be, 0x10), (0x2d3, 0), (0x2d5, 0xa7), (0x2d3, 0x84)]
DESER = [(0x51, 1), (0x52, 2), (0x11, 0x0f), (0x10, 0x23)]
FRAME_SIZE = 1920 * 1536 * 2


def main():
    global BUS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize', action='store_true',
                        help='Apply vendor camera reset/clock sequence first')
    parser.add_argument('--frames', type=int, default=20)
    parser.add_argument('--mp4', action='store_true', help='Save H.264 MP4 instead of raw UYVY')
    parser.add_argument('--bus', type=int, default=9)
    parser.add_argument('--devices', nargs=2, default=['/dev/video0', '/dev/video1'])
    parser.add_argument('--output', type=Path,
                        default=Path('/home/dexmate/wrist-camera-debug'))
    args = parser.parse_args()
    BUS = args.bus
    if not 1 <= args.frames <= 300:
        parser.error('frames must be between 1 and 300')
    assert read(0x48, 0x0d) == 0x94, 'Unexpected deserializer'
    assert read(0x48, 1) & 3 == 1, 'Requires 3Gbps receiver configuration'
    assert read(0x48, 0x13) & 8, 'GMSL link is not locked'
    for address in CAMERAS:
        # 0x91 before initialization, 0x93 observed after vendor sequence.
        # This runtime guard is not a proposal to broaden kernel probe IDs.
        assert read(address, 0x0d) in (0x91, 0x93), 'Unexpected serializer'
        assert read(address, 0) >> 1 == address, 'Wrong serializer alias'
    busy = subprocess.run(['fuser', *args.devices],
                          capture_output=True, text=True)
    if busy.returncode == 0:
        raise RuntimeError('Video devices are already in use: ' + busy.stdout)
    args.output.mkdir(parents=True, exist_ok=True)
    run = args.output / ('capture-' + time.strftime('%Y%m%d-%H%M%S'))
    run.mkdir()
    snapshots = {}
    for address in CAMERAS:
        registers = sorted({r for r, _ in VIDEO[address] + VENDOR + VENDOR_RELEASE})
        snapshots[hex(address)] = {hex(r): read(address, r) for r in registers}
    snapshots['0x48'] = {hex(r): read(0x48, r) for r, _ in DESER}
    (run / 'before.json').write_text(json.dumps(snapshots, indent=2))
    for address in CAMERAS:
        if args.initialize:
            for register, value in VENDOR:
                write(address, register, value)
            time.sleep(.765)
            for register, value in VENDOR_RELEASE:
                write(address, register, value)
        for register, value in VIDEO[address]:
            write(address, register, value)
    for register, value in DESER:
        write(0x48, register, value)
    time.sleep(.3)
    cmd = ['gst-launch-1.0', '-e']
    for i in range(2):
        cmd += ['v4l2src', f'device={args.devices[i]}', f'num-buffers={args.frames}',
                '!', 'video/x-raw,format=UYVY,width=1920,height=1536,framerate=30/1']
        if args.mp4:
            cmd += ['!', 'queue', '!', 'videoconvert', '!', 'video/x-raw,format=I420',
                    '!', 'x264enc', 'speed-preset=ultrafast', 'tune=zerolatency',
                    'bitrate=6000', 'key-int-max=30', 'byte-stream=false',
                    '!', 'video/x-h264,stream-format=avc,alignment=au', '!', 'mp4mux']
        suffix = '.mp4' if args.mp4 else '.uyvy'
        cmd += ['!', 'filesink', f'location={run / (str(i) + suffix)}']
    # 30/1 is the driver's negotiated mode, not a measured frame rate.
    # Diagnostic MFP7 pulses are roughly 10Hz and not hardware synchronized.
    log = (run / 'gstreamer.log').open('w')
    process = None
    try:
        for address in CAMERAS:
            write(address, 0x2d3, 0x80)
        process = subprocess.Popen(cmd, stdout=log, stderr=log)
        deadline = time.monotonic() + 10 + args.frames / 4
        while time.monotonic() < deadline and process.poll() is None:
            for address in CAMERAS:
                write(address, 0x2d3, 0x90)
            time.sleep(.005)
            for address in CAMERAS:
                write(address, 0x2d3, 0x80)
            time.sleep(.09)
    finally:
        # Restore both trigger pins even if restoring one fails.
        errors = []
        for address in CAMERAS:
            try:
                write(address, 0x2d3, 0x84)
            except Exception as error:
                errors.append(str(error))
        if process is not None and process.poll() is None:
            process.send_signal(2)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        log.close()
        if errors:
            raise RuntimeError('Trigger restore failed: ' + '; '.join(errors))
    results = []
    for i in range(2):
        suffix = '.mp4' if args.mp4 else '.uyvy'
        path = run / f'{i}{suffix}'
        size = path.stat().st_size if path.exists() else 0
        if args.mp4:
            results.append({'video': i, 'path': str(path), 'bytes': size,
                            'requested_frames': args.frames})
            continue
        hashes = []
        if size:
            with path.open('rb') as stream:
                while data := stream.read(FRAME_SIZE):
                    hashes.append(hashlib.sha256(data).hexdigest())
        results.append({'video': i, 'bytes': size, 'frames': size // FRAME_SIZE,
                        'remainder': size % FRAME_SIZE,
                        'unique_frames': len(set(hashes))})
    report = {'directory': str(run), 'exit_code': process.returncode,
              'results': results}
    (run / 'results.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    assert process.returncode == 0, 'Capture failed; inspect gstreamer.log'
    if args.mp4:
        assert all(r['bytes'] > 0 for r in results)
    else:
        assert all(r['frames'] == args.frames and r['remainder'] == 0 for r in results)


if __name__ == '__main__':
    main()
