"""Run real lab checks and retain failures, missing resources, and raw evidence."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile

from . import core as c
from . import labs


def observe(command, evidence):
    value = c.command(command, timeout=30)
    evidence.append({'command': command, 'result': value})
    return c.output(value).split('<log>', 1)[0].strip()


def execute(metadata, program):
    if program.get('network_check'):
        return network_check(metadata, program)
    results = []
    for case in program.get('cases', []):
        command = [metadata['binary'], *case.get('args', [])]
        try:
            process = subprocess.run(command, input=case['stdin'], capture_output=True, text=True,
                                     errors='replace', cwd=Path(metadata['binary']).parent, timeout=8,
                                     start_new_session=True, env=os.environ | case.get('env', {}))
        except subprocess.TimeoutExpired:
            raise RuntimeError(f'Example did not finish for input {case["stdin"]!r}.') from None
        missing = [text for text in case['contains'] if text not in process.stdout]
        if missing:
            raise RuntimeError(f'Missing expected output {missing!r}; got {process.stdout!r}, stderr={process.stderr!r}.')
        expected_signal = case.get('signal')
        if expected_signal and process.returncode != -expected_signal:
            raise RuntimeError(f'Expected signal {expected_signal}; got exit {process.returncode}.')
        if not expected_signal and process.returncode < 0:
            raise RuntimeError(f'Unexpected signal {-process.returncode}.')
        for name, expected in case.get('files', {}).items():
            actual = (Path(metadata['binary']).parent / name).read_text()
            if actual != expected:
                raise RuntimeError(f'{name}: expected {expected!r}; got {actual!r}.')
        results.append({'command': command, 'stdin': case['stdin'], 'exit_code': process.returncode,
                        'stdout': process.stdout, 'stderr': process.stderr})
    if not results:
        return {'status': 'pending', 'reason': 'A behavioral recipe is still required for this program.'}
    return {'status': 'passed', 'cases': results}


def network_check(metadata, program):
    directory = Path(metadata['binary']).parent
    if program['network_check'] == 'tls-server':
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
                        '-subj', '/CN=course.local', '-keyout', str(directory / 'key.pem'),
                        '-out', str(directory / 'cert.pem')], check=True, capture_output=True, timeout=30)
    image = c.read_json(c.ROOT / 'dependencies.lock.json')['network_test_image']
    command = ['docker', 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL', '--security-opt',
               'no-new-privileges:true', '--user', f'{os.getuid()}:{os.getgid()}',
               '--read-only', '--tmpfs', '/tmp:rw,nosuid,size=32m',
               '-v', f'{directory}:/lab:rw', '-v', f'{c.ROOT / "scripts/network_check.py"}:/check.py:ro',
               '-w', '/lab', image, 'python', '/check.py', program['network_check'],
               '/lab/' + Path(metadata['binary']).name]
    result = subprocess.run(command, capture_output=True, text=True, timeout=25)
    if result.returncode:
        raise RuntimeError('Isolated network check failed: ' + result.stderr + result.stdout)
    return {'status': 'passed', 'command': command, 'observation': json.loads(result.stdout)}


def sanitizer(metadata, program):
    spec = program.get('sanitizer')
    if not spec:
        return None
    target = Path(metadata['binary']).with_name('sanitizer-check')
    command = list(metadata['command'])
    command[command.index('-o') + 1] = str(target)
    # Initialize automatic storage with a nonzero pattern so a missing string
    # terminator cannot accidentally pass because the next byte happened to be 0.
    command += ['-fsanitize=address', '-ftrivial-auto-var-init=pattern']
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Sanitizer build failed: ' + result.stderr)
    env = os.environ | {'ASAN_OPTIONS': 'detect_leaks=0'}
    result = subprocess.run([str(target)], input=spec['stdin'], capture_output=True, text=True,
                            cwd=target.parent, timeout=8, env=env)
    if result.returncode == 0 or spec['contains'] not in result.stderr:
        raise RuntimeError('The expected undefined behavior was not detected: ' + result.stderr)
    return {'status': 'passed', 'expected_fault': spec['contains'], 'stderr': result.stderr}


def _windows_execute(metadata, program):
    if program.get('skip_execution'):
        return {'status': 'passed', 'note': program['skip_execution']}
    from . import windows as w
    if not w.vm_ready():
        return {'status': 'blocked', 'reason': 'Windows VM is not reachable.'}
    remote_path = w.copy_binary(metadata['binary'])
    return w.vm_execute(remote_path, program)


def _windows_debug(metadata, program, evidence):
    from . import windows as w
    if not w.vm_ready():
        return {'status': 'blocked', 'reason': 'Windows VM is not reachable.'}
    last_result = None
    for attempt in range(2):
        remote_path = w.copy_binary(metadata['binary'])
        try:
            result = w.debug_session(remote_path)
            if result.get('evidence'):
                evidence.extend(result['evidence'])
            if result['status'] == 'passed':
                return result
            last_result = result
        except Exception as exc:
            last_result = {'status': 'failed', 'reason': str(exc)}
    return last_result


def verify_program(item, program):
    result = {'lesson': item['id'], 'example': program['id'], 'at': c.now(), 'checks': {}, 'observations': []}
    stage = 'build'
    try:
        metadata = c.start(item, example=program['id'])
        result['build'] = {k: v for k, v in metadata.items() if k not in ('token', 'url', 'pid', 'process_start')}
        result['checks']['build'] = {'status': 'passed'}
        stage = 'radare2_static'
        info = json.loads(observe('ij', result['observations']))
        functions = json.loads(observe('aflj', result['observations']))
        if not functions or info.get('bin', {}).get('arch') != 'x86':
            raise RuntimeError('radare2 did not recognize and analyze the executable.')
        observe('iij', result['observations'])
        observe('izj', result['observations'])
        observe('pdfj @ main' if any(f['name'].split('.')[-1] == 'main' for f in functions) else 'pdfj @ entry0', result['observations'])
        result['checks'][stage] = {'status': 'passed', 'functions': len(functions), 'format': info['bin'].get('class')}
        if program['platform'] == 'windows':
            stage = 'execution'
            result['checks'][stage] = _windows_execute(metadata, program)
            is_dll = metadata['binary'].endswith('.dll')
            stage = 'radare2_debug'
            if is_dll:
                result['checks'][stage] = {'status': 'passed',
                    'note': 'DLL — debug breakpoint check not applicable.'}
            else:
                result['checks'][stage] = _windows_debug(metadata, program, result['observations'])
        else:
            stage = 'execution'
            result['checks'][stage] = execute(metadata, program)
            stage = 'sanitizer'
            fault = sanitizer(metadata, program)
            if fault:
                result['checks'][stage] = fault
                if result['checks']['execution']['status'] == 'pending':
                    result['checks']['execution'] = {'status': 'passed', 'expected_undefined_behavior': fault['expected_fault']}
            stage = 'radare2_debug'
            observe('ood', result['observations'])
            address = int(observe('?v main', result['observations']), 0)
            if address == 0:
                raise RuntimeError('No main address after opening the debugger.')
            observe(f'db {address}', result['observations'])
            observe('dc', result['observations'])
            regs = json.loads(observe('drj', result['observations']))
            reason = json.loads(observe('dij', result['observations']))
            if regs.get('rip', regs.get('eip')) != address or reason.get('stopreason') != 'breakpoint':
                raise RuntimeError('The debugger did not stop at the requested breakpoint.')
            observe('pxj 64 @ rsp' if 'rip' in regs else 'pxj 64 @ esp', result['observations'])
            result['checks'][stage] = {'status': 'passed', 'address': address}
    except Exception as exc:
        result['checks'][stage] = {'status': 'failed', 'reason': str(exc)}
    finally:
        c.stop()
    states = [v['status'] for v in result['checks'].values()]
    result['status'] = 'passed' if states and all(s == 'passed' for s in states) else ('failed' if 'failed' in states else 'incomplete')
    return result


def verify(lesson_id='all'):
    base = c.workdir() / 'verification' / datetime.now().strftime('%Y%m%d-%H%M%S')
    base.mkdir(parents=True)
    selected = c.catalog()['lessons'] if lesson_id == 'all' else [c.lesson(lesson_id)]
    previous = os.environ.get('ARTIK_COURSE_WORKDIR')
    reports = []
    try:
        for item in selected:
            programs = labs.specification(item)['examples']
            article = {'id': item['id'], 'programs': [], 'walkthrough': {'status': 'pending',
                       'reason': 'Program checks do not yet validate every practical step in this article.'}}
            for program in programs:
                os.environ['ARTIK_COURSE_WORKDIR'] = str(base / item['id'] / program['id'])
                result = verify_program(item, program)
                c.write_json(c.workdir() / 'verification.json', result)
                article['programs'].append(result)
                print(f'{result["status"]:10} {item["id"]}/{program["id"]}', flush=True)
            if not programs:
                article['assets'] = {'status': 'blocked', 'reason': 'External exercise assets still required.'}
            reports.append(article)
            c.write_json(base / 'report.json', {'at': c.now(), 'articles': reports})
    finally:
        if previous is None:
            os.environ.pop('ARTIK_COURSE_WORKDIR', None)
        else:
            os.environ['ARTIK_COURSE_WORKDIR'] = previous
    print('Evidence:', base / 'report.json')
    return base / 'report.json'
