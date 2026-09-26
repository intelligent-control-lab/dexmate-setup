#!/usr/bin/env python3
"""Publish the supplied manual unchanged, adding only B10/B11 and a translation."""
import html
from html.parser import HTMLParser
import json
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


def build(lang):
    source = (SOURCE / 'vega1umanual.html').read_text()
    if lang == 'zh':
        translations = json.loads((SOURCE / 'zh.json').read_text())
        source = Translator(source, translations).result()
        # Copy-button feedback is UI text, outside the original prose nodes.
        source = source.replace("'Copied'", "'已复制'").replace("'Copy'", "'复制'").replace("'Failed'", "'复制失败'")
    titles = ('Gripper hardware setup', 'PCB / camera hardware setup') if lang == 'en' else ('夹爪硬件连接', 'PCB／相机硬件安装')
    entries = '\n'.join(f'<li><a href="#{ident}"><span>B{n}</span>{title}</a></li>' for n, ident, title in zip((10, 11), ('gripper-hardware', 'pcb-hardware'), titles))
    source = source.replace('<li><a href="#src">', entries + '\n    <li><a href="#src">', 1)
    source = source.replace('<section id="src">', (SOURCE / f'hardware.{lang}.html').read_text() + '\n<section id="src">', 1)
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
    print('Built original manual + B10/B11, in English and Chinese.')
