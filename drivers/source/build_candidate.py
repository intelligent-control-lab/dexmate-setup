"""Build a boot-test candidate from the installed vendor overlays, offline.

Inputs are canonical dtc decompilations. Internal/external fixups become label
references before rearranging nodes; dtc will regenerate relocation metadata.
"""
from dataclasses import dataclass, field
from pathlib import Path
import copy
import re


@dataclass
class Node:
    name: str
    props: dict = field(default_factory=dict)
    children: dict = field(default_factory=dict)
    label: str = ''

    def at(self, path):
        n = self
        for key in path.strip('/').split('/'):
            if key:
                n = n.children[key]
        return n

    def walk(self, path=''):
        yield path or '/', self
        for name, child in self.children.items():
            yield from child.walk(path + '/' + name)


def parse(path):
    root = None
    stack = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line == '/dts-v1/;':
            continue
        if line.endswith(' {'):
            node = Node(line[:-2])
            if stack:
                assert node.name not in stack[-1].children
                stack[-1].children[node.name] = node
            else:
                root = node
            stack.append(node)
        elif line == '};':
            stack.pop()
        elif line.endswith(';'):
            key, sep, value = line[:-1].partition(' = ')
            assert key not in stack[-1].props
            stack[-1].props[key] = value if sep else None
        else:
            raise ValueError(line)
    assert root and not stack
    return root


def references(tree, prefix):
    ids = {}
    for path, node in tree.walk():
        if path.startswith('/__'):
            continue
        if 'phandle' in node.props:
            value = int(node.props.pop('phandle').strip('<>'), 0)
            assert value not in ids
            node.label = f'{prefix}_{value:x}'
            ids[value] = node.label

    def replace(path, prop, offsets, external=None):
        node = tree.at(path)
        cells = node.props[prop].strip('<>').split()
        for offset in offsets:
            assert offset % 4 == 0
            index = offset // 4
            old = int(cells[index], 0)
            if external:
                assert old == 0xffffffff
            cells[index] = '&' + (external or ids[old])
        node.props[prop] = '<' + ' '.join(cells) + '>'

    for path, node in tree.children['__local_fixups__'].walk():
        for prop, offsets in node.props.items():
            replace(path, prop, [int(x, 0) for x in offsets.strip('<>').split()])
    for symbol, paths in tree.children['__fixups__'].props.items():
        for entry in paths.strip('"').split('\\0'):
            path, prop, offset = entry.rsplit(':', 2)
            replace(path, prop, [int(offset)], symbol)
    for name in ['__local_fixups__', '__fixups__', '__symbols__']:
        tree.children.pop(name, None)


def merge(a, b):
    for key, value in b.props.items():
        assert key not in a.props or a.props[key] == value, (a.name, key)
        a.props[key] = value
    for key, node in b.children.items():
        if key in a.children:
            merge(a.children[key], node)
        else:
            a.children[key] = node


def render(node, depth=0):
    indent = '    ' * depth
    label = node.label + ': ' if node.label else ''
    lines = [indent + label + node.name + ' {']
    for key, value in node.props.items():
        lines.append(indent + '    ' + key + (' = ' + value if value is not None else '') + ';')
    for child in node.children.values():
        lines.extend(render(child, depth + 1))
    lines.append(indent + '};')
    return lines


def main():
    here = Path(__file__).resolve().parent
    zed = parse(here / 'zedlink-original.dts')
    wrist = parse(here / 'wrist-original.dts')
    references(zed, 'head')
    references(wrist, 'wrist')
    z = zed.at('/fragment-camera-zedx-zedlink-duo@0/__overlay__')
    w = wrist.at('/fragment@0/__overlay__')
    # Preserve the ZED capture card's own I2C mux below the carrier's CAM0 mux
    # branch. The carrier mux exclusively owns PCC.03 and can select CAM1 too.
    old = '/bus@0/i2c@3180000/tca9546@70'
    new = '/bus@0/cam_i2cmux/i2c@0/tca9546@70'
    tca = z.at('/bus@0/i2c@3180000').children.pop('tca9546@70')
    cam0 = w.at('/bus@0/cam_i2cmux/i2c@0')
    cam0.props.update({'status': '"okay"', 'reg': '<0>',
                       '#address-cells': '<1>', '#size-cells': '<0>'})
    cam0.children[tca.name] = tca
    # Remove the competing permanent CAM0 I2C select GPIO hog.
    z.at('/bus@0').children.pop('gpio@c2f0000')
    # Do not import wrist overlay's unrelated CAM0 reset/power GPIO hogs.
    w.at('/bus@0').children.pop('gpio@2200000')
    w.at('/bus@0').children.pop('gpio@6000d000')
    for tree in (z, w):
        for _, node in tree.walk():
            for key, value in node.props.items():
                if value:
                    node.props[key] = value.replace(old, new)
    for path, prefix in [('/tegra-capture-vi/ports', 'port'),
                         ('/bus@0/host1x@13e00000/nvcsi@15a00000', 'channel')]:
        parent = w.at(path)
        for i in range(2):
            node = parent.children.pop(f'{prefix}@{i}')
            node.name = f'{prefix}@{26+i}'
            node.props['reg'] = f'<{26+i}>'
            parent.children[node.name] = node
    for tree in (z, w):
        tree.at('/tegra-capture-vi').props['num-channels'] = '<28>'
        tree.at('/bus@0/host1x@13e00000/nvcsi@15a00000').props['num-channels'] = '<28>'
    modules = w.at('/tegra-camera-platform/modules')
    for i in range(2):
        node = modules.children.pop(f'module{i}')
        node.name = f'module{14+i}'
        node.props['badge'] = f'"wrist_{i}_isx031"'
        modules.children[node.name] = node
        sensor = w.at('/bus@0/cam_i2cmux/i2c@1/' +
                      ('rbpcv2_gmsl_linka@1a' if i == 0 else 'rbpcv2_gmsl_linkb@1b'))
        sensor.props['devnode'] = f'"video{26+i}"'
    z.at('/tegra-camera-platform').props['num_csi_lanes'] = '<6>'
    merge(z, w)
    # Both directions of every media endpoint must resolve to each other.
    labels = {node.label: node for _, node in z.walk() if node.label}
    pairs = 0
    for _, node in z.walk():
        if 'remote-endpoint' in node.props:
            target = node.props['remote-endpoint'].strip('<>& ')
            assert target in labels, target
            assert labels[target].props['remote-endpoint'] == f'<&{node.label}>'
            pairs += 1
    output = Node('/')
    output.props = copy.deepcopy(wrist.props)
    output.props['overlay-name'] = '"ZED CAM0 plus MAX9295 wrists CAM1 - TEST"'
    fragment = Node('fragment@0', {'target-path': '"/"'}, {'__overlay__': z})
    output.children[fragment.name] = fragment
    text = '/dts-v1/;\n/plugin/;\n\n' + '\n'.join(render(output)) + '\n'
    (here / 'head-wrists-test.dts').write_text(text)
    print(f'Generated candidate: {pairs} reciprocal endpoint references checked')


if __name__ == '__main__':
    main()
