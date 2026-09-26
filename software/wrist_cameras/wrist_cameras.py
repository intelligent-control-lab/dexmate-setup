"""Local dual-wrist RGB API. Camera A/B are connector labels, not left/right.

with WristCameras() as cameras:
    observations = cameras.get_obs(timeout=3)
    rgb = observations['wrist_a']['rgb']  # uint8 HxWx3, RGB

Requires wrist-camera-init.service. Owns both V4L2 devices and software trigger.
"""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

LOCK_PATH = '/run/lock/wrist-cameras.lock'
READY_PATH = '/run/wrist-cameras/ready.json'


def discover_devices():
    result = {}
    for entry in Path('/sys/class/video4linux').glob('video*'):
        name = (entry / 'name').read_text().strip()
        if 'gmsl-031-b ' not in name:
            continue
        address = name.rsplit(' ', 1)[-1]
        bus, _, suffix = address.partition('-')
        if suffix in ('001a', '001b') and bus.isdigit():
            key = 'wrist_a' if suffix == '001a' else 'wrist_b'
            if key in result:
                raise RuntimeError('Ambiguous wrist devices: ' + key)
            result[key] = {'device': '/dev/' + entry.name, 'bus': int(bus)}
    if set(result) != {'wrist_a', 'wrist_b'}:
        raise RuntimeError('Both wrist V4L2 devices are required')
    if result['wrist_a']['bus'] != result['wrist_b']['bus']:
        raise RuntimeError('Wrist devices are on different I2C buses')
    return result


class WristCameras:
    def __init__(self):
        self._pipeline = self._trigger = self._lock = None
        self._condition = threading.Condition()
        self._latest = {}
        self._counts = {'wrist_a': 0, 'wrist_b': 0}
        self._returned = dict(self._counts)
        self._error = None
        self._closed = True

    def open(self):
        if not self._closed:
            return self
        try:
            ready = json.loads(Path(READY_PATH).read_text())
        except FileNotFoundError as error:
            raise RuntimeError('Wrists are not initialized; check wrist-camera-init.service') from error
        if ready['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
            raise RuntimeError('Wrist initialization marker is from another boot')
        devices = discover_devices()
        self._lock = open(LOCK_PATH, 'r+')
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lock.close(); self._lock = None
            raise RuntimeError('Wrist cameras are already owned by another reader or initializer')
        self._closed = False
        self._latest = {}; self._counts = {'wrist_a': 0, 'wrist_b': 0}
        self._returned = dict(self._counts); self._error = None
        try:
            paths = [v['device'] for v in devices.values()]
            if subprocess.run(['fuser', *paths], capture_output=True).returncode == 0:
                raise RuntimeError('Wrist V4L2 devices are busy')
            Gst.init(None)
            parts = []
            for index, (name, device) in enumerate(devices.items()):
                parts.append(f"v4l2src device={device['device']} ! video/x-raw,format=UYVY,width=1920,height=1536,framerate=30/1 ! videoconvert ! video/x-raw,format=RGB ! appsink name=sink{index} emit-signals=true sync=false max-buffers=2 drop=true")
            self._pipeline = Gst.parse_launch(' '.join(parts))
            for index, name in enumerate(devices):
                self._pipeline.get_by_name(f'sink{index}').connect('new-sample', self._sample, name)
            if self._pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError('Cannot start wrist capture pipeline')
            self._trigger = subprocess.Popen([
                sys.executable, str(Path(__file__).with_name('trigger.py')),
                '--bus', str(devices['wrist_a']['bus']), '--parent', str(os.getpid())],
                pass_fds=(self._lock.fileno(),))
            self.get_obs(timeout=10)
            return self
        except BaseException:
            self.close()
            raise

    def _sample(self, sink, name):
        sample = sink.emit('pull-sample')
        if sample is None:
            return Gst.FlowReturn.ERROR
        buf = sample.get_buffer()
        ok, mapped = buf.map(Gst.MapFlags.READ)
        if not ok:
            return Gst.FlowReturn.ERROR
        try:
            if len(mapped.data) != 1920 * 1536 * 3:
                raise RuntimeError('Unexpected RGB frame size')
            rgb = np.frombuffer(mapped.data, dtype=np.uint8).reshape(1536, 1920, 3).copy()
            with self._condition:
                self._counts[name] += 1
                self._latest[name] = {'rgb': rgb, 'timestamp_ns': int(buf.pts),
                    'received_monotonic_ns': time.monotonic_ns(), 'frame_id': self._counts[name]}
                self._condition.notify_all()
            return Gst.FlowReturn.OK
        except Exception as error:
            with self._condition:
                self._error = str(error); self._condition.notify_all()
            return Gst.FlowReturn.ERROR
        finally:
            buf.unmap(mapped)

    def get_obs(self, timeout=2.0, fresh=True):
        """Return both RGB frames. PTS is pipeline time, not Unix time.

        fresh=True waits for a newer frame on BOTH cameras than the prior call.
        Received monotonic timestamps share the host clock; no hardware sync.
        Returned RGB arrays are copies and can be modified by the caller.
        """
        if self._closed:
            raise RuntimeError('Camera reader is not open')
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                if self._error:
                    raise RuntimeError(self._error)
                if self._trigger is not None and self._trigger.poll() is not None:
                    raise RuntimeError('Wrist trigger worker exited')
                message = self._pipeline.get_bus().pop_filtered(Gst.MessageType.ERROR)
                if message:
                    raise RuntimeError(str(message.parse_error()))
                complete = len(self._latest) == 2
                if complete and (not fresh or all(self._counts[n] > self._returned[n] for n in self._counts)):
                    result = {n: {**v, 'rgb': v['rgb'].copy()} for n, v in self._latest.items()}
                    self._returned = dict(self._counts)
                    return result
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('No fresh frame from both wrist cameras')
                self._condition.wait(min(remaining, .2))

    def close(self):
        # Drain V4L2 while trigger still runs, then restore trigger pins.
        try:
            if self._pipeline is not None:
                self._pipeline.set_state(Gst.State.NULL)
                self._pipeline = None
        finally:
            try:
                if self._trigger is not None:
                    if self._trigger.poll() is None:
                        self._trigger.send_signal(signal.SIGTERM)
                    returncode = self._trigger.wait(timeout=8)
                    self._trigger = None
                    if returncode:
                        raise RuntimeError('Trigger worker failed during cleanup')
            finally:
                self._closed = True
                if self._lock is not None:
                    fcntl.flock(self._lock, fcntl.LOCK_UN)
                    self._lock.close(); self._lock = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *_):
        self.close()
