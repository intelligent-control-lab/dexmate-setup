#!/usr/bin/env python3
"""Check local HTML assets, fragment links and language section parity."""
from html.parser import HTMLParser
from pathlib import Path
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


def main():
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
