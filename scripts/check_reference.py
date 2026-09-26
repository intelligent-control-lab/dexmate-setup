#!/usr/bin/env python3
"""Verify the published calibration matrices against their source records and URDFs."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

FILES = Path(__file__).resolve().parents[1] / 'docs/files'


def joint_transform(joint, q):
    origin = joint.find('origin')
    xyz = np.fromstring(origin.get('xyz', '0 0 0'), sep=' ')
    roll, pitch, yaw = np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')
    def rotate(axis, angle):
        axis = np.asarray(axis, dtype=float)
        axis /= np.linalg.norm(axis)
        x, y, z = axis
        k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * (k @ k)
    transform = np.eye(4)
    transform[:3, :3] = rotate([0, 0, 1], yaw) @ rotate([0, 1, 0], pitch) @ rotate([1, 0, 0], roll)
    transform[:3, 3] = xyz
    motion = np.eye(4)
    value = q.get(joint.get('name'), 0)
    if value:
        axis = np.fromstring(joint.find('axis').get('xyz'), sep=' ')
        if joint.get('type') == 'prismatic':
            motion[:3, 3] = axis * value
        elif joint.get('type') in ('revolute', 'continuous'):
            motion[:3, :3] = rotate(axis, value)
    return transform @ motion


def transform(path, parent, child, q):
    joints = {j.find('child').get('link'): j for j in ET.parse(path).findall('joint')}
    def from_root(frame):
        if frame not in joints:
            return np.eye(4)
        joint = joints[frame]
        return from_root(joint.find('parent').get('link')) @ joint_transform(joint, q)
    return np.linalg.inv(from_root(parent)) @ from_root(child)


def main():
    data = json.loads((FILES / 'reference-data.json').read_text())
    for record in data['files']:
        assert hashlib.sha256((FILES / record['file']).read_bytes()).hexdigest() == record['sha256'], record['file']
    for name in ('clean', 'adjusted'):
        original = json.loads((FILES / f'calibration/{name}-20260924.json').read_text())
        assert data[f'{name}_T_R_ee_tip_r'] == original['tcp']['T_R_ee_tip_r']
        assert data[f'{name}_T_base_camera'] == original['camera']['T_base_camera']
    q = data['reference_joint_positions']
    for filename in ('vega_1u.urdf', 'vega_1u_gripper.urdf'):
        actual = transform(FILES / 'urdf' / filename, 'base_link', 'zed_left_camera', q)
        np.testing.assert_allclose(actual, data['urdf_T_base_zed_left_camera'], atol=1e-12, rtol=0)
    for side in ('L', 'R'):
        for target in (f'{side}_camera_link', f'{side}_gripper_base'):
            actual = transform(FILES / 'urdf/vega_1u_gripper.urdf', f'{side}_ee', target, q)
            np.testing.assert_allclose(actual, data['relative_transforms'][f'T_{side}_ee_{target}'], atol=1e-12, rtol=0)
        actual = transform(FILES / 'urdf/custom/vega_1u_gripper.urdf', f'{side}_ee', f'tip_{side.lower()}', {})
        np.testing.assert_allclose(actual, data['relative_transforms'][f'custom_T_{side}_ee_tip_{side.lower()}'], atol=1e-12, rtol=0)
    print('PASS: source hashes, paired calibration matrices, head FK, wrist mounts and custom TCP transforms')


if __name__ == '__main__':
    main()
