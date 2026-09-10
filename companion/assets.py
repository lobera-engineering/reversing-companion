"""Pinned course specimens and static extraction; specimens are never executed."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from . import core as c
from scripts.bootstrap import download


def specification(item):
    return c.read_json(c.ROOT / 'course/assets.lock.json').get(item['id'], {})


def fetch(item):
    spec = specification(item)
    if not spec.get('sha256'):
        raise RuntimeError(spec.get('reason', 'No external asset is registered for this lesson.'))
    directory = c.workdir() / 'assets' / item['id']
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / spec['name']
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == spec['sha256']:
        return target
    cache = c.RUNTIME / 'assets'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive_hash = spec.get('archive_sha256', spec['sha256'])
    cached = cache / archive_hash
    local = spec.get('local_archive')
    if local:
        src = c.ROOT / local
        if not src.is_file():
            raise RuntimeError(f'Local archive not found: {src}')
        if hashlib.sha256(src.read_bytes()).hexdigest() != archive_hash:
            raise RuntimeError(f'Local archive checksum mismatch: {src}')
        import shutil
        shutil.copy2(src, cached)
    else:
        download(spec['url'], cached, archive_hash)
    if spec.get('archive_member'):
        with zipfile.ZipFile(cached) as archive:
            # Read a single named member; never extract arbitrary archive paths.
            data = archive.read(spec['archive_member'], pwd=spec['password'].encode())
    else:
        data = cached.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise RuntimeError('The unpacked specimen does not match the pinned hash.')
    target.write_bytes(data)
    target.chmod(0o600)
    c.write_json(directory / 'provenance.json', spec | {'fetched_at': c.now(), 'path': str(target)})
    return target


def rc4(key, data):
    table = list(range(256))
    j = 0
    for i in range(256):
        j = (j + table[i] + key[i % len(key)]) % 256
        table[i], table[j] = table[j], table[i]
    i = j = 0
    output = bytearray()
    for byte in data:
        i = (i + 1) % 256
        j = (j + table[i]) % 256
        table[i], table[j] = table[j], table[i]
        output.append(byte ^ table[(table[i] + table[j]) % 256])
    return bytes(output)


def extract(path, kind):
    if kind == 'iceid':
        import pefile
        pe = pefile.PE(str(path))
        try:
            section = next(s for s in pe.sections if s.Name.rstrip(b'\0') == b'.data')
            data = section.get_data()
            decoded = rc4(data[:8], data[8:])
            output = path.parent / 'config-decoded.bin'
            output.write_bytes(decoded)
            strings = [s.decode('ascii') for s in re.findall(rb'[\x20-\x7e]{5,}', decoded)]
            expected = ['/index.php', 'boldidiotruss.xyz', 'nizaoplov.xyz', '153ishak.best', 'ilu21plane.xyz']
            if not all(any(needle in value for value in strings) for needle in expected):
                raise RuntimeError('The decrypted configuration differs from the article evidence.')
            return {'status': 'passed', 'scope': 'RC4 configuration extraction from the unpacked article PE',
                    'key_hex': data[:8].hex(), 'section_rva': section.VirtualAddress,
                    'strings': strings, 'output': str(output), 'unpacking': 'pending'}
        finally:
            pe.close()
    if kind == 'emotet':
        from oletools.olevba import VBA_Parser
        parser = VBA_Parser(str(path))
        try:
            macros = '\n'.join(code for _, _, _, code in parser.extract_macros())
            if 'Rebnfkihsrl' not in macros:
                raise RuntimeError('This document is not the macro illustrated in the article.')
            (path.parent / 'macros.vba.txt').write_text(macros)
            separator = '//====dsfnnJJJsm388//='
            strings = [row[-1].decode(errors='replace') if isinstance(row[-1], bytes) else row[-1]
                       for row in parser.extract_form_strings()]
            cleaned = [s.replace(separator, '') for s in strings]
            powershell = []
            for value in cleaned:
                for candidate in re.findall(r'[A-Za-z0-9+/=]{200,}', value):
                    try:
                        text = base64.b64decode(candidate, validate=True).decode('utf-16-le')
                    except (ValueError, UnicodeError):
                        continue
                    if '$' in text and 'http://' in text:
                        powershell.append(text)
            if len(powershell) != 1:
                raise RuntimeError('Expected one encoded PowerShell payload in the form fields.')
            output = path.parent / 'powershell-decoded.txt'
            output.write_text(powershell[0])
            urls = re.findall(r'https?://[^\s\x27\x22*]+', powershell[0])
            if len(urls) != 5 or not any('adykurniawan.com/mp3/18ox6h/' in s for s in urls):
                raise RuntimeError('The decoded download locations differ from the article.')
            return {'status': 'passed', 'scope': 'VBA/form extraction and base64 UTF-16 decoding without execution',
                    'macro': 'Rebnfkihsrl', 'separator': separator, 'urls': urls,
                    'decoded_payload': str(output), 'execution': 'not performed'}
        finally:
            parser.close()
    raise RuntimeError('No static extraction recipe for this asset.')


def analyze(item):
    spec = specification(item)
    if not spec.get('analysis'):
        raise RuntimeError(spec.get('reason', 'No extraction recipe for this lesson.'))
    path = c.workdir() / 'assets' / item['id'] / spec['name']
    if not path.is_file():
        raise RuntimeError(f'Fetch the pinned asset first: ./coursectl assets {item["id"]} --fetch')
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
        raise RuntimeError('The specimen has changed since it was fetched.')
    result = subprocess.run([str(c.RUNTIME / 'venv/bin/python'), '-m', 'companion.assets',
                             str(path), spec['analysis']], cwd=c.ROOT, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Static extraction failed: ' + result.stderr)
    observation = json.loads(result.stdout) | {'asset_sha256': spec['sha256'], 'at': c.now()}
    c.write_json(path.parent / 'analysis.json', observation)
    return observation


if __name__ == '__main__':
    print(json.dumps(extract(Path(sys.argv[1]), sys.argv[2])))
