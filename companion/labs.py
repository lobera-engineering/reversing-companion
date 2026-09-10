"""Program selection and builds for the course's multi-example laboratories."""
import hashlib
import base64
from pathlib import Path
import shutil
import subprocess

from . import core as c


def specification(item):
    spec = c.read_json(c.ROOT / 'labs' / item['lab'] / 'lab.json')
    if not spec:
        raise RuntimeError('No lab manifest for this article.')
    return spec


def select(item, name=None):
    spec = specification(item)
    name = name or spec.get('default')
    for example in spec.get('examples', []):
        if example['id'] == name:
            return spec, example
    if not spec.get('examples'):
        raise RuntimeError('This article needs external laboratory assets. See its lab manifest and coverage report.')
    raise RuntimeError(f'Unknown example {name!r}. Run ./coursectl examples {item["id"]}.')


def directory(item, spec, program, bits, optimization):
    target = c.workdir() / 'labs' / item['id']
    if program['id'] != spec['default']:
        target /= program['id']
    return target / f'x{bits}-{optimization}'


def prepare(item, bits=None, optimization='O0', example=None):
    """Reuse a working executable, including patches, until an explicit build."""
    spec, program = select(item, example)
    bits = bits or program.get('bits', 64)
    target = directory(item, spec, program, bits, optimization)
    metadata = c.read_json(target / 'build.json')
    if metadata and Path(metadata['binary']).is_file():
        source = Path(metadata['source'])
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != metadata['source_sha256']:
            raise RuntimeError('The source has changed. Run ./coursectl build for this example before starting it.')
        for name, digest in metadata.get('support_sha256', {}).items():
            if hashlib.sha256((target / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError('A support source has changed. Rebuild this example before starting it.')
        return metadata | {'current_binary_sha256': hashlib.sha256(Path(metadata['binary']).read_bytes()).hexdigest()}
    return build(item, bits, optimization, example)


def build(item, bits=None, optimization='O0', example=None):
    spec, program = select(item, example)
    bits = bits or program.get('bits', 64)
    target = directory(item, spec, program, bits, optimization)
    target.mkdir(parents=True, exist_ok=True)
    packaged = c.ROOT / 'labs' / item['lab']
    source = target / program['source']
    for name in [program['source'], *program.get('support_files', [])]:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(packaged / name, dest)
    for name, text in program.get('fixtures', {}).items():
        dest = target / name
        if not dest.exists():
            if isinstance(text, dict):
                dest.write_bytes(base64.b64decode(text['base64']))
            else:
                dest.write_text(text)
    if program.get('kind') == 'binary':
        if bits != program['bits']:
            raise RuntimeError(f'This supplied binary is x{program["bits"]}; it cannot be recompiled for x{bits}.')
        binary = target / program['id']
        if not binary.exists():
            shutil.copy2(source, binary)
            binary.chmod(0o700)
        loader = c.RUNTIME / 'multilib/usr/lib32/ld-linux.so.2'
        patcher = c.RUNTIME / 'multilib/usr/bin/patchelf'
        if not loader.is_file() or not patcher.is_file():
            raise RuntimeError('The IOLI lab needs the private 32-bit loader and patchelf runtime.')
        command = [str(patcher), '--set-interpreter', str(loader), '--set-rpath', str(loader.parent), str(binary)]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=20)
        metadata = {'lesson': item['id'], 'example': program['id'], 'built_at': c.now(), 'binary': str(binary),
                    'source': str(source), 'platform': program['platform'], 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'command': command,
                    'compiler': 'Original IOLI prebuilt ELF; private loader relocation only',
                    'bits': bits, 'optimization': optimization, 'lab': item['lab']}
        c.write_json(target / 'build.json', metadata)
        return metadata
    windows = program['platform'] == 'windows'
    cpp = program.get('language') == 'cpp'
    if windows:
        triplet = 'x86_64' if bits == 64 else 'i686'
        name = f'{triplet}-w64-mingw32-' + ('g++' if cpp else 'gcc')
        local = c.RUNTIME / 'mingw/usr/bin' / (name + '-posix')
        compiler = str(local) if local.is_file() else shutil.which(name)
    else:
        compiler = shutil.which('g++' if cpp else 'gcc')
    if not compiler:
        raise RuntimeError(f'Missing compiler for {program["platform"]} x{bits}; see ./coursectl doctor.')
    binary = target / (source.stem + program.get('output_suffix', '.exe' if windows else ''))
    command = [compiler, '-std=gnu++17' if cpp else '-std=' + program.get('standard', 'gnu11'),
               '-g', f'-{optimization}', f'-m{bits}', '-fno-omit-frame-pointer', '-Wall', '-Wextra']
    if not windows:
        command += ['-fPIE', '-pie'] if program.get('pie') else ['-fno-pie', '-no-pie']
        if bits == 32:
            runtime = c.RUNTIME / 'multilib/usr'
            if not (runtime / 'lib32/crt1.o').is_file():
                raise RuntimeError('Install the pinned i386 development runtime with ./coursectl bootstrap.')
            command += ['-B', str(runtime / 'lib/gcc/x86_64-linux-gnu/13/32') + '/',
                        '-B', str(runtime / 'lib32') + '/',
                        '-isystem', str(runtime / 'include/x86_64-linux-gnu'),
                        '-isystem', '/usr/include/x86_64-linux-gnu', '-L', str(runtime / 'lib32'),
                        '-Wl,--dynamic-linker=' + str(runtime / 'lib32/ld-linux.so.2'),
                        '-Wl,-rpath,' + str(runtime / 'lib32')]
    command += program.get('cflags', [])
    command += [str(source), *(str(target / name) for name in program.get('extra_sources', [])),
                '-o', str(binary)] + program.get('ldflags', [])
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (target / 'compiler.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'Compilation failed for {item["id"]}/{program["id"]}:\n' + result.stderr)
    metadata = {'lesson': item['id'], 'example': program['id'], 'built_at': c.now(),
                'binary': str(binary), 'source': str(source), 'platform': program['platform'],
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'support_sha256': {name: hashlib.sha256((target / name).read_bytes()).hexdigest()
                                   for name in program.get('support_files', [])},
                'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                'command': command, 'compiler': subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                'bits': bits, 'optimization': optimization, 'lab': item['lab']}
    c.write_json(target / 'build.json', metadata)
    return metadata
