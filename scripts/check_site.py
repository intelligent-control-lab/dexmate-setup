#!/usr/bin/env python3
"""Check local HTML assets, fragment links and language section parity."""
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1] / "docs"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path, self.ids, self.refs, self.sections = path, set(), [], []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, (self.path, "duplicate id", attrs["id"])
            self.ids.add(attrs["id"])
        if tag == "section":
            self.sections.append(attrs.get("id"))
        if tag == "img":
            assert attrs.get("alt"), (self.path, "image needs alt text")
        for key in ("href", "src", "poster"):
            if attrs.get(key):
                self.refs.append(attrs[key])


def check_original_preserved():
    original = (ROOT.parent / "manual/vega1umanual.html").read_text()
    english = (ROOT / "en.html").read_text()
    chinese = (ROOT / "index.html").read_text()
    pattern = r'<section id="([^"]+)"[^>]*>.*?</section>'
    sections = {m.group(1): m.group(0) for m in re.finditer(pattern, original, re.S)}
    en_sections = {m.group(1): m.group(0) for m in re.finditer(pattern, english, re.S)}
    zh_sections = {m.group(1): m.group(0) for m in re.finditer(pattern, chinese, re.S)}
    assert set(en_sections) - set(sections) == {"gripper-hardware", "pcb-hardware", "hardware-control-reference", "tcp-extrinsics"}
    for ident, source in sections.items():
        assert en_sections[ident] == source, f"Original chapter rewritten: {ident}"
        for tag in ("pre", "code"):
            blocks = rf'<{tag}\b[^>]*>.*?</{tag}>'
            assert re.findall(blocks, source, re.S) == re.findall(blocks, zh_sections[ident], re.S), (ident, "translated command/code changed")
    assert re.search(r'<style>.*?</style>', original, re.S).group() in english
    assert re.search(r'<style>.*?</style>', original, re.S).group() in chinese
    print(f"PASS: all {len(sections)} original English sections unchanged; Chinese commands and original CSS preserved")


def main():
    check_original_preserved()
    pages = {path.resolve(): Page(path) for path in ROOT.glob("*.html")}
    count = 0
    for path, page in pages.items():
        for ref in page.refs:
            u = urlsplit(ref)
            if u.scheme or u.netloc:
                continue
            target = (path.parent / unquote(u.path)).resolve() if u.path else path
            assert target.is_relative_to(ROOT.resolve()), (path, "path outside docs", ref)
            assert target.exists(), (path, "missing asset", ref)
            if u.fragment and target in pages:
                assert unquote(u.fragment) in pages[target].ids, (path, "missing fragment", ref)
            count += 1
    assert pages[(ROOT / "index.html").resolve()].sections == pages[(ROOT / "en.html").resolve()].sections
    print(f"PASS: {len(pages)} pages, {count} local references, matching bilingual sections")


if __name__ == "__main__":
    main()
