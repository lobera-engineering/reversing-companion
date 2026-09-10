#!/usr/bin/env python3
"""Install pinned lab tools into .runtime, without changing system packages."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'


def run(*args, cwd=ROOT, env=None):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def checkout(spec, name):
    target = RUNTIME / 'src' / name
    if not (target / '.git').is_dir():
        run('git', 'clone', '--no-checkout', '--filter=blob:none', spec['repository'], target)
    available = subprocess.run(['git', 'cat-file', '-e', spec['commit']], cwd=target,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if available.returncode:
        run('git', 'fetch', '--depth', '1', 'origin', spec['commit'], cwd=target)
    run('git', 'checkout', '--detach', spec['commit'], cwd=target)
    return target


def download(url, dest, digest):
    if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest() == digest:
        return
    print(f'Downloading {dest.name}', flush=True)
    temporary = dest.with_suffix(dest.suffix + '.part')
    req = urllib.request.Request(url, headers={'User-Agent': 'ArtikCourseCompanion/0.1'})
    with urllib.request.urlopen(req, timeout=60) as response, temporary.open('wb') as output:
        shutil.copyfileobj(response, output)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
        temporary.unlink()
        raise RuntimeError(f'Checksum mismatch: {dest.name}')
    temporary.replace(dest)


def runtime_env():
    env = os.environ.copy()
    prefix = RUNTIME / 'radare' / 'usr'
    bins = [RUNTIME / 'venv' / 'bin', prefix / 'bin', RUNTIME / 'src' / 'radare2-mcp' / 'src']
    env['PATH'] = os.pathsep.join(map(str, bins)) + os.pathsep + env.get('PATH', '')
    libdirs = [prefix / 'lib', prefix / 'lib' / 'x86_64-linux-gnu']
    env['LD_LIBRARY_PATH'] = os.pathsep.join(map(str, libdirs)) + os.pathsep + env.get('LD_LIBRARY_PATH', '')
    env['PKG_CONFIG_PATH'] = os.pathsep.join(str(p / 'pkgconfig') for p in libdirs)
    env['R2_PREFIX'] = str(prefix)
    return env


def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise SystemExit('This bootstrap currently supports Linux x86-64 (including WSL2).')
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11 or newer is required.')
    for tool in ('git', 'gcc', 'make', 'dpkg-deb', 'pkg-config'):
        if not shutil.which(tool):
            raise SystemExit(f'Missing prerequisite: {tool}')
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
    requirements = ROOT / 'requirements.lock'
    patches = sorted((ROOT / 'patches').glob('radare2-mcp-*.patch'))
    installed = {**lock, 'python_requirements_sha256': hashlib.sha256(requirements.read_bytes()).hexdigest(),
                 'patches': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in patches}}
    for name in ('downloads', 'src', 'radare'):
        (RUNTIME / name).mkdir(parents=True, exist_ok=True)
    stamp = RUNTIME / 'installed.json'
    if stamp.is_file() and json.loads(stamp.read_text()) == installed:
        expected = [RUNTIME / 'venv/bin/hermes', RUNTIME / 'radare/usr/bin/r2',
                    RUNTIME / 'src/radare2-mcp/src/r2mcp', RUNTIME / 'mingw/usr/bin/x86_64-w64-mingw32-gcc-posix',
                    RUNTIME / 'multilib/usr/lib32/ld-linux.so.2']
        if all(p.is_file() for p in expected):
            print('Pinned runtime already installed.')
            return
    for package in lock['radare2']['packages']:
        dest = RUNTIME / 'downloads' / package['name']
        url = f"https://github.com/radareorg/radare2/releases/download/{lock['radare2']['version']}/{package['name']}"
        download(url, dest, package['sha256'])
        run('dpkg-deb', '-x', dest, RUNTIME / 'radare')
    for package in lock.get('additional_debs', []):
        target = RUNTIME / package['group']
        downloads = target / 'downloads'
        downloads.mkdir(parents=True, exist_ok=True)
        dest = downloads / package['name']
        download(package['url'], dest, package['sha256'])
        run('dpkg-deb', '-x', dest, target)
    # The private i386 development package ships a linker script with system
    # absolute paths. Relocate those references without touching /usr or /lib.
    linker_script = RUNTIME / 'multilib/usr/lib32/libc.so'
    if linker_script.is_file():
        data = linker_script.read_text()
        for original, relative in [('/lib32/libc.so.6', 'libc.so.6'),
                                   ('/usr/lib32/libc_nonshared.a', 'libc_nonshared.a'),
                                   ('/lib/ld-linux.so.2', 'ld-linux.so.2')]:
            data = data.replace(' ' + original + ' ', ' ' + str(linker_script.parent / relative) + ' ')
        linker_script.write_text(data)
    prefix = RUNTIME / 'radare' / 'usr'
    for pc in prefix.rglob('*.pc'):
        content = pc.read_text().replace('prefix=/usr', f'prefix={prefix}')
        pc.write_text(content)
    env = runtime_env()
    run('r2', '-v', env=env)
    mcp_src = checkout(lock['r2mcp'], 'radare2-mcp')
    for patch in patches:
        applied = subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)], cwd=mcp_src,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if applied.returncode:
            run('git', 'apply', '--check', patch, cwd=mcp_src)
            run('git', 'apply', patch, cwd=mcp_src)
    run('./configure', cwd=mcp_src, env=env)
    # Upstream tracks .inc.c files on the link target but not on its object files.
    # Rebuild objects so a changed included-source patch is actually compiled.
    run('make', 'clean', cwd=mcp_src, env=env)
    run('make', '-j', str(min(os.cpu_count() or 2, 4)), cwd=mcp_src, env=env)
    run(mcp_src / 'src' / 'r2mcp', '-v', env=env)
    hermes_src = checkout(lock['hermes'], 'hermes-agent')
    venv = RUNTIME / 'venv'
    if not (venv / 'bin/python').exists():
        run(sys.executable, '-m', 'venv', venv)
    python = venv / 'bin/python'
    run(python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', requirements,
        '-e', f'{hermes_src}[mcp]')
    run(python, '-m', 'pip', 'check')
    stamp.write_text(json.dumps(installed, indent=2) + '\n')
    print('Runtime ready. Run ./coursectl doctor next.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'Bootstrap failed: {exc}') from None
