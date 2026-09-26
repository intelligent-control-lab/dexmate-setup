#!/usr/bin/env python3
"""Publish the original manual with bilingual hardware and calibration additions."""
import html
from html.parser import HTMLParser
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'manual'
DOCS = ROOT / 'docs'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Translator(HTMLParser):
    """Translate prose in place; retain tags, code, styles and scripts verbatim."""
    def __init__(self, source, translations):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.translations = translations
        self.stack = []
        self.edits = []
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, data):
        if any(t in self.stack for t in ('pre', 'code', 'style', 'script', 'svg')):
            return
        key = data.strip()
        if key not in self.translations:
            return
        line, col = self.getpos()
        start = self.offsets[line - 1] + col
        end = self.source.find('<', start)
        if end < 0:
            end = len(self.source)
        raw = self.source[start:end]
        # Do not allow a parser event to consume a different source text node.
        assert html.unescape(raw).strip() == key, (key, raw)
        prefix = raw[:len(raw) - len(raw.lstrip())]
        suffix = raw[len(raw.rstrip()):]
        self.edits.append((start, end, prefix + html.escape(self.translations[key], quote=False) + suffix))

    def result(self):
        result = self.source
        for start, end, replacement in reversed(self.edits):
            result = result[:start] + replacement + result[end:]
        return result


def reference_chapters(lang):
    data = json.loads((DOCS / 'files/reference-data.json').read_text())
    relative = data['relative_transforms']
    matrices = {
        'CLEAN_TCP': data['clean_T_R_ee_tip_r'],
        'CLEAN_CAMERA': data['clean_T_base_camera'],
        'ADJUSTED_TCP': data['adjusted_T_R_ee_tip_r'],
        'ADJUSTED_CAMERA': data['adjusted_T_base_camera'],
        'URDF_CAMERA': data['urdf_T_base_zed_left_camera'],
        'CUSTOM_RIGHT_TCP': relative['custom_T_R_ee_tip_r'],
        'CUSTOM_LEFT_TCP': relative['custom_T_L_ee_tip_l'],
        'LEFT_WRIST': relative['T_L_ee_L_camera_link'],
        'RIGHT_WRIST': relative['T_R_ee_R_camera_link'],
    }
    source = (SOURCE / f'reference.{lang}.html').read_text()
    for key, matrix in matrices.items():
        rows = ['[' + ', '.join(f'{(0 if abs(x) < 0.5e-9 else x): .9f}' for x in row) + ']' for row in matrix]
        source = source.replace('{{' + key + '}}', '[\n  ' + ',\n  '.join(rows) + '\n]')
    for key, records in [('URDF_MOUNT_ROWS', data['urdf_fixed_joints']), ('CUSTOM_MOUNT_ROWS', data['custom_fixed_joints'])]:
        rows = ''.join('<tr><td><code>' + html.escape(row['parent']) + ' → ' + html.escape(row['child']) + '</code></td><td><code>' + html.escape(row['xyz_m']) + '</code></td><td><code>' + html.escape(row['rpy_rad']) + '</code></td></tr>' for row in records)
        source = source.replace('{{' + key + '}}', rows)
    assert '{{' not in source, 'Unresolved reference placeholder'
    return source


# Stable anchors preserve existing links while visible chapter numbers change.
MANDATORY = ('hardware-control-reference', 'tcp-extrinsics', 'net', 'cert', 'comm', 'libs', 'verify', 'camera-setup')
ADVANCED = ('arch', 'dof', 'gripper', 'reflash', 'gripper-hardware', 'pcb-hardware')
NUMBERS = {ident: f'{part}{n}' for part, order in [('B', MANDATORY), ('C', ADVANCED)] for n, ident in enumerate(order, 1)}
SECTION_PATTERN = r'<section id="([^"]+)"[^>]*>.*?</section>'


def renumber(source):
    # Change chapter labels and linked references only, never command text / image data.
    for ident, number in NUMBERS.items():
        source = re.sub(r'(<a href="#' + re.escape(ident) + r'">)B\d+(</a>)', lambda m: m[1] + number + m[2], source)
    def section(match):
        text = match[0]
        if match[1] in NUMBERS:
            text = re.sub(r'(<span class="num">)[BC]\d+(</span>)', lambda m: m[1] + NUMBERS[match[1]] + m[2], text, count=1)
        return text
    return re.sub(SECTION_PATTERN, section, source, flags=re.S)


def organize(source, lang):
    source = renumber(source)
    source = source.replace("Optional · not in use", "Workstation setup").replace("可选 · 目前未使用", "工作站设置")
    chapters = {m[1]: m[0] for m in re.finditer(SECTION_PATTERN, source, re.S)}
    nav_titles = {m[1]: m[2] for m in re.finditer(r'<a href="#([^"]+)"><span>[^<]+</span>(.*?)</a>', source)}
    additions = ('Gripper hardware', 'PCB / camera hardware', 'Hardware &amp; control', 'TCP, extrinsics &amp; URDF') if lang == 'en' else ('夹爪硬件连接', 'PCB／相机硬件安装', '硬件与控制信息', 'TCP、外参与 URDF')
    nav_titles.update(zip(('gripper-hardware', 'pcb-hardware', 'hardware-control-reference', 'tcp-extrinsics'), additions))
    headings = ('Mandatory setup', 'Advanced info') if lang == 'en' else ('必读与必要设置', '进阶信息')
    descriptions = (
        ('Read B1–B8 for every new robot. Complete the applicable setup and checks; workstation configuration in B5 applies when using an external computer.',
         'Architecture, joint limits, CAN details, reflash recovery and illustrated hardware installation references.')
        if lang == 'en' else
        ('每台新机器人都需阅读 B1–B8，并完成适用的设置与检查；B5 中的工作站配置适用于使用外部电脑的情况。',
         '架构、关节限位、CAN 细节、刷机恢复，以及带图片的硬件安装参考。')
    )
    nav = ''
    body = ''
    for part, order, title, description in zip(('B', 'C'), (MANDATORY, ADVANCED), headings, descriptions):
        nav += f'<p class="grp">{part} · {title}</p>\n  <ol>\n'
        body += f'<div class="partline"><p class="eyebrow">Part {part}</p><h2>{title}</h2><p>{description}</p></div>\n'
        for ident in order:
            chapter = chapters[ident]
            heading = nav_titles[ident]
            nav += f'<li><a href="#{ident}"><span>{NUMBERS[ident]}</span>{heading}</a></li>\n'
            body += chapter + '\n\n'
        nav += '</ol>\n'
    src_title = re.search(r'<h2>(.*?)</h2>', chapters['src'], re.S)[1]
    nav += f'<ol><li><a href="#src"><span>—</span>{src_title}</a></li></ol>\n'
    source = re.sub(r'<p class="grp">B .*?</nav>', lambda m: nav + '</nav>', source, count=1, flags=re.S)
    start = source.index('<div class="partline">')
    end = source.index('<section id="src">', start)
    source = source[:start] + body + source[end:]
    intro = ('<strong>Part A</strong> covers everyday operation. <strong>Part B</strong> contains the mandatory reading and setup for a new robot. <strong>Part C</strong> holds advanced information and hardware references.'
             if lang == 'en' else '<strong>Part A</strong> 是日常操作；<strong>Part B</strong> 是新机器人的必读信息与必要设置；<strong>Part C</strong> 是进阶信息及硬件参考。')
    source = re.sub(r'<p class="standfirst">.*?</p>', '<p class="standfirst">' + intro + '</p>', source, count=1, flags=re.S)
    camera = (SOURCE / f'camera-help.{lang}.html').read_text()
    start = source.index('<section id="camera-setup">')
    at = source.index('<div class="note warn">', start)
    source = source[:at] + camera + '\n  ' + source[at:]
    registration = (SOURCE / f'registration.{lang}.html').read_text()
    start = source.index('<section id="cert">')
    at = source.index('<p class="lede">', start)
    source = source[:at] + registration + '\n  ' + source[at:]
    return source


def build(lang):
    source = (SOURCE / 'vega1umanual.html').read_text()
    if lang == 'zh':
        translations = json.loads((SOURCE / 'zh.json').read_text())
        source = Translator(source, translations).result()
        # Copy-button feedback is UI text, outside the original prose nodes.
        source = source.replace("'Copied'", "'已复制'").replace("'Copy'", "'复制'").replace("'Failed'", "'复制失败'")
    source = source.replace('<section id="src">', (SOURCE / f'hardware.{lang}.html').read_text() + reference_chapters(lang) + '\n<section id="src">', 1)
    source = organize(source, lang)
    switch = '<div class="manual-language"><a href="index.html" lang="zh-CN">中文</a><span> / </span><a href="en.html" lang="en">English</a></div>'
    source = source.replace('<div class="masthead-inner">', '<div class="masthead-inner">\n' + switch, 1)
    cut = source.index('</style>') + len('</style>')
    head, body = source[:cut], source[cut:]
    locale = 'en' if lang == 'en' else 'zh-CN'
    result = f'<!doctype html>\n<html lang="{locale}">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n' + head + '\n<link rel="stylesheet" href="hardware.css">\n</head>\n<body>\n' + body + '\n<script>document.querySelectorAll(".manual-language a").forEach(function(a){a.addEventListener("click",function(){a.hash=location.hash;});});</script>\n</body>\n</html>\n'
    (DOCS / ('en.html' if lang == 'en' else 'index.html')).write_text(result)


if __name__ == '__main__':
    for language in ('en', 'zh'):
        build(language)
    print('Built bilingual manual: Part A, mandatory B1–B8, advanced C1–C6.')
