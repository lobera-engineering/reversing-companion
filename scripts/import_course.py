#!/usr/bin/env python3
"""Import the author's local Markdown, retaining provenance and index order."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class Index(HTMLParser):
    def __init__(self):
        super().__init__()
        self.group = ''
        self.heading = False
        self.link = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h3':
            self.heading = True
            self.group = ''
        if tag == 'a' and attrs.get('href', '').startswith('https://artik.blue/'):
            self.link = {'url': attrs['href'], 'title': '', 'group': self.group.strip()}

    def handle_data(self, data):
        if self.heading:
            self.group += data
        if self.link is not None:
            self.link['title'] += data

    def handle_endtag(self, tag):
        if tag == 'h3':
            self.heading = False
        if tag == 'a' and self.link is not None:
            self.links.append(self.link)
            self.link = None


def import_course(source):
    source = source.expanduser().resolve()
    parser = Index()
    parser.feed((source / '_pages/reversing.md').read_text())
    posts = ROOT / 'course' / 'posts'
    posts.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    rows = []
    for order, entry in enumerate(parser.links, 1):
        slug = urlparse(entry['url']).path.strip('/')
        matches = list((source / '_posts').glob('*-' + slug + '.md'))
        if len(matches) != 1:
            raise RuntimeError(f'Expected one Markdown source for {slug}; found {len(matches)}')
        original = matches[0]
        raw = original.read_bytes()
        text = raw.decode()
        target = posts / original.name
        shutil.copyfile(original, target)
        title = re.search(r'^title:\s*(.+)$', text, re.M)
        suffix = re.sub(r'^reversing-radare2?-', '', slug)
        aliases = [suffix] if suffix != slug else []
        lab = None
        if slug == 'reversing-radare2-1':
            lab = 'hello'
            aliases += ['intro', 'hello']
        if slug == 'reversing-radare-6':
            lab = 'structs'
            aliases += ['structs', 'estructuras']
        issues = []
        if slug == 'reversing-radare2-2':
            issues.append('The index describes conditionals, but this source contains buffer overflows. Original retained pending correction.')
        rows.append({**entry, 'id': slug, 'order': order, 'aliases': aliases, 'title': entry['title'].strip(),
                     'source_title': title.group(1).strip('" ') if title else '',
                     'source_path': str(original.relative_to(source)), 'source_sha256': hashlib.sha256(raw).hexdigest(),
                     'content': str(target.relative_to(ROOT)), 'lab': lab,
                     'validation': 'needs_review' if issues else ('lab_packaged' if lab else 'reading_only'), 'issues': issues})
    data = {'schema_version': 1, 'source_repository': 'https://github.com/artikblue/artikblue.github.io',
            'source_commit': commit, 'source_index': '_pages/reversing.md', 'lessons': rows}
    (ROOT / 'course/catalog.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    # Extract the two complete C examples verbatim from the blog, not disassembly fences.
    for lab, slug, marker in [('hello', 'reversing-radare2-1', 'Hello, World!'),
                              ('structs', 'reversing-radare-6', 'struct Books')]:
        row = next(r for r in rows if r['id'] == slug)
        text = (ROOT / row['content']).read_text()
        fences = re.findall(r'^```[^\n]*\n(.*?)^```\s*$', text, re.M | re.S)
        blocks = [block for block in fences if '#include' in block and marker in block and 'main(' in block]
        if len(blocks) != 1:
            raise RuntimeError(f'Cannot identify the complete C example for {lab}')
        dest = ROOT / 'labs' / lab
        dest.mkdir(parents=True, exist_ok=True)
        name = 'hello.c' if lab == 'hello' else 'books.c'
        (dest / name).write_text(blocks[0].strip() + '\n')
        spec = {'source': name, 'lesson': slug, 'source_url': row['url'], 'source_commit': commit,
                'adaptation': 'C example extracted verbatim; builds use explicit non-PIE flags for the first lab.'}
        (dest / 'lab.json').write_text(json.dumps(spec, indent=2) + '\n')
    from scripts.package_labs import package_labs
    package_labs()
    print(f'Imported {len(rows)} lessons from {commit[:12]}.')


if __name__ == '__main__':
    import_course(Path(sys.argv[1]))
