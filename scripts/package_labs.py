#!/usr/bin/env python3
"""Extract every reviewed program, preserving source and adaptation provenance."""
import difflib
import hashlib
import json
from pathlib import Path
import re

from scripts.course_specs import DEFAULTS, HEADERS, PROGRAMS, REPLACEMENTS, WINDOWS
from scripts.course_checks import CASES, FIXTURES, SANITIZERS

ROOT = Path(__file__).resolve().parents[1]


def package_labs():
    path = ROOT / 'course/catalog.json'
    catalog = json.loads(path.read_text())
    count = 0
    for item in catalog['lessons']:
        alias = item['aliases'][0] if item['aliases'] else item['id']
        text = (ROOT / item['content']).read_text()
        fences = list(re.finditer(r'^```([^\n]*)\n(.*?)^```[ \t]*$', text, re.M | re.S))
        programs = PROGRAMS.get(alias, [])
        name = {'1': 'hello', '6': 'structs'}.get(alias, item['id'])
        dest = ROOT / 'labs' / name
        dest.mkdir(parents=True, exist_ok=True)
        examples = []
        for index, example_id, title in programs:
            match = fences[index]
            original = match[2].strip() + '\n'
            modified = original
            changes = []
            for before, after, reason in REPLACEMENTS.get((alias, example_id), []):
                if before not in modified:
                    raise RuntimeError(f'Expected source for adaptation missing: {alias}/{example_id}: {reason}')
                modified = modified.replace(before, after, 1)
                changes.append(reason)
            for header in HEADERS.get(alias, []):
                if not re.search(r'#\s*include\s*[<"]' + re.escape(header) + r'[>"]', modified):
                    modified = f'#include <{header}>\n' + modified
                    changes.append(f'Add missing declaration header <{header}>.')
            if alias in WINDOWS:
                modified = modified.replace('<Windows.h>', '<windows.h>').replace('"Windows.h"', '<windows.h>')
                if modified != original and 'Windows.h' in original:
                    changes.append('Use lower-case windows.h for the case-sensitive cross compiler filesystem.')
            if (alias, example_id) == ('17', 'dns-file'):
                modified = '#include "base64.h"\n' + modified
                modified = modified.replace('int i = 0;', 'size_t i = 0;').replace('int hFile = CreateFile', 'HANDLE hFile = CreateFile')
                changes += ['Declare the article-linked base64 implementation and its size_t output length.',
                            'Use HANDLE for CreateFile so Win64 file handles are not truncated to int.']
            language = 'cpp' if (alias, example_id) in [('malware6', 'demo-dll'), ('malware6', 'dll-injector'), ('malware7', 'pe-injector')] else 'c'
            source = f'{example_id}.{language}'
            (dest / 'original').mkdir(exist_ok=True)
            (dest / 'original' / source).write_text(original)
            (dest / source).write_text(modified)
            patch = ''.join(difflib.unified_diff(original.splitlines(True), modified.splitlines(True),
                                                fromfile='original/' + source, tofile=source))
            if patch:
                (dest / (source + '.patch')).write_text(patch)
            example = {'id': example_id, 'title': title, 'source': source, 'language': language,
                       'platform': 'windows' if alias in WINDOWS else 'linux', 'standard': 'gnu11',
                       'article_fence': index, 'article_line': text.count('\n', 0, match.start()) + 2,
                       'original_sha256': hashlib.sha256(original.encode()).hexdigest(),
                       'source_sha256': hashlib.sha256(modified.encode()).hexdigest(), 'adaptations': changes,
                       'cflags': [], 'ldflags': [], 'fixtures': {}, 'validation': 'pending'}
            example['fixtures'] = FIXTURES.get((alias, example_id), {})
            example['cases'] = CASES.get((alias, example_id), [])
            if example_id in ('tcp-server', 'tcp-client', 'smart-server', 'tls-server', 'http-code') and alias not in WINDOWS:
                example['network_check'] = example_id
            if (alias, example_id) in SANITIZERS:
                example['sanitizer'] = SANITIZERS[(alias, example_id)]
            if alias == '19':
                example['ldflags'] += ['-lssl', '-lcrypto']
            if alias in ('17', '18'):
                example['ldflags'] += ['-lws2_32']
            if alias == '14':
                example['ldflags'] += ['-luser32', '-llz32']
            if (alias, example_id) == ('malware6', 'demo-dll'):
                (dest / 'main.h').write_text('#pragma once\n#include <windows.h>\n#define DLL_EXPORT __declspec(dllexport)\n')
                example['support_files'] = ['main.h']
                example['ldflags'] += ['-shared', '-luser32']
                example['output_suffix'] = '.dll'
                example['adaptations'].append('Supply the missing header declaring the WinAPI types and DLL_EXPORT macro; compile the printed extern C entry as C++.')
            if (alias, example_id) == ('17', 'dns-file'):
                vendor = dest / 'vendor/base64.c'
                if not vendor.exists():
                    raise RuntimeError('Missing the base64 dependency referenced by article 17.')
                code = vendor.read_text().replace('#include "includes.h"', '#include <stdlib.h>\n#include <string.h>')
                code = code.replace('#include "os.h"', '#define os_malloc malloc\n#define os_free free\n#define os_memset memset')
                (dest / 'base64.c').write_text(code)
                (dest / 'base64.h').write_text('#pragma once\n#include <stddef.h>\nunsigned char *base64_encode(const unsigned char *, size_t, size_t *);\nunsigned char *base64_decode(const unsigned char *, size_t, size_t *);\n')
                example['support_files'] = ['base64.c', 'base64.h']
                example['extra_sources'] = ['base64.c']
                example['adaptations'].append('Compile the linked BSD base64 source with libc wrappers for its wpa os_* helpers; original retained in vendor/.')
            if alias == '23':
                example['cflags'] += ['-fstack-protector-all']
            if alias in ('2', '20', '21', '22', '24'):
                example['cflags'] += ['-fno-stack-protector']
            if alias == '24':
                example['pie'] = example_id == 'pie'
            examples.append(example)
            count += 1
        default = DEFAULTS.get(alias, examples[0]['id'] if examples else None)
        if alias == '8-i':
            for i in range(10):
                binary = f'crackme0x{i:02x}'
                original = dest / 'original' / binary
                if not original.exists():
                    raise RuntimeError('Fetch the pinned IOLI archive before packaging the crackmes.')
                examples.append({'id': binary, 'title': 'IOLI ' + binary, 'kind': 'binary', 'language': 'binary',
                                 'source': 'original/' + binary, 'platform': 'linux', 'bits': 32,
                                 'source_url': 'https://raw.githubusercontent.com/radareorg/radare2book/5504edf6734f03f1d761288f58422ee6afbf9d3d/crackmes/ioli/IOLI-crackme.tar.gz',
                                 'original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                                 'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                                 'adaptations': ['The working copy receives the private 32-bit loader path; the original ELF is retained unchanged.'],
                                 'cases': CASES[(alias, binary)], 'fixtures': {}, 'validation': 'pending'})
                count += 1
            default = examples[0]['id']
        source = next((e['source'] for e in examples if e['id'] == default), None)
        spec = {'schema_version': 2, 'lesson': item['id'], 'source_url': item['url'],
                'source_commit': catalog['source_commit'], 'source': source, 'default': default,
                'examples': examples, 'sections': re.findall(r'^#{2,6}\s+(.+)', text, re.M),
                'walkthrough_validation': 'pending'}
        (dest / 'lab.json').write_text(json.dumps(spec, indent=2, ensure_ascii=False) + '\n')
        item['lab'] = name
        item['examples'] = len(examples)
        item['validation'] = 'pending_validation'
        item['platform'] = 'windows' if alias in WINDOWS or alias.startswith('malware') else 'linux'
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n')
    print(f'Packaged {count} programs across {len(catalog["lessons"])} lesson manifests; validation pending.')


if __name__ == '__main__':
    package_labs()
