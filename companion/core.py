"""Shared radare2-mcp session management and course state.

Starts a local r2mcp process, exposes MCP RPC calls, and maintains the
notebook (progress, notes, evidence snapshots).  Every high-level action
routes through the same live r2mcp session so student and agent share
analysis state.
"""
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
_children = {}


def workdir():
    path = Path(os.environ.get('ARTIK_COURSE_WORKDIR', ROOT / 'work')).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.is_file() else default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf-8') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)
        out.write('\n')
        temporary = Path(out.name)
    temporary.replace(path)


@contextlib.contextmanager
def locked(name):
    path = workdir() / (name + '.lock')
    with path.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def catalog():
    path = ROOT / 'course' / 'catalog.json'
    if not path.is_file():
        raise RuntimeError('Import the blog first: ./coursectl import ../artikblue.github.io')
    return read_json(path)


def notebook():
    return read_json(workdir() / 'notebook.json', {'schema_version': 1, 'active_lesson': None, 'lessons': {}})


def lesson(value=None):
    value = value or notebook()['active_lesson']
    for item in catalog()['lessons']:
        if value == item['id'] or value in item.get('aliases', []):
            return item
    raise RuntimeError(f'Unknown lesson: {value!r}. Run ./coursectl list.')


def record(item, *, text=None, status=None, active=False):
    with locked('notebook'):
        data = notebook()
        if active:
            data['active_lesson'] = item['id']
        entry = data['lessons'].setdefault(item['id'], {'notes': [], 'status': 'in_progress'})
        if text:
            entry['notes'].append({'at': now(), 'text': text})
        if status:
            entry['status'] = status
        entry['updated_at'] = now()
        write_json(workdir() / 'notebook.json', data)
    return data


def runtime_env():
    from scripts.bootstrap import runtime_env as tool_env
    env = tool_env()
    env['PATH'] = str(ROOT) + os.pathsep + env['PATH']
    env['ARTIK_COURSE_ROOT'] = str(ROOT)
    env['ARTIK_COURSE_WORKDIR'] = str(workdir())
    env['HERMES_HOME'] = str(workdir() / 'hermes')
    return env


def build(item, bits=None, optimization='O0', example=None):
    from .labs import build as build_program
    return build_program(item, bits, optimization, example)


def layout(item):
    if item.get('lab') != 'structs':
        raise RuntimeError('The C layout probe is available for the Books lab (lesson 6).')
    try:
        state = session()
        if state['lesson'] != item['id']:
            raise RuntimeError('Another lab is active.')
        if state.get('example', 'books') != 'books':
            raise RuntimeError('The layout probe requires the Books example.')
        target = Path(state['source']).parent
        metadata = read_json(target / 'build.json')
    except RuntimeError:
        target = workdir() / 'labs' / item['id'] / 'x64-O0'
        metadata = read_json(target / 'build.json')
        if not metadata:
            metadata = build(item)
    source = Path(metadata['source'])
    probe = target / 'layout-probe.c'
    executable = target / 'layout-probe'
    fields = ('title', 'author', 'subject', 'book_id')
    text = ['#include <stddef.h>', '#include <stdio.h>', '#define main course_example_main',
            f'#include "{source.name}"', '#undef main', 'int main(void) {',
            'printf("%zu %zu\\n", sizeof(struct Books), _Alignof(struct Books));']
    for field in fields:
        text.append(f'printf("{field} %zu %zu\\n", offsetof(struct Books, {field}), sizeof(((struct Books *)0)->{field}));')
    text += ['return 0;', '}']
    probe.write_text('\n'.join(text) + '\n')
    command_line = [metadata['command'][0], '-std=c11', f'-m{metadata["bits"]}', str(probe), '-o', str(executable)]
    result = subprocess.run(command_line, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Layout probe could not compile the current source:\n' + result.stderr)
    lines = subprocess.check_output([str(executable)], text=True, timeout=10).splitlines()
    size, alignment = map(int, lines[0].split())
    values = {}
    for line in lines[1:]:
        name, offset, field_size = line.split()
        values[name] = {'offset': int(offset), 'size': int(field_size)}
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    binary_hash = hashlib.sha256(Path(metadata['binary']).read_bytes()).hexdigest()
    evidence = {'type': 'struct Books', 'sizeof': size, 'alignment': alignment, 'fields': values,
                'source_sha256': source_hash, 'binary_sha256': binary_hash, 'compiler_command': command_line,
                'matches_recorded_build': source_hash == metadata['source_sha256'] and binary_hash == metadata['binary_sha256']}
    write_json(target / 'layout.json', evidence)
    return evidence


def process_start(pid):
    try:
        # comm may contain spaces and parentheses; fields after its last ')' start at state.
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return None if stat[0] == 'Z' else stat[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def session():
    state = read_json(workdir() / 'session.json')
    if not state or process_start(state['pid']) != state['process_start']:
        raise RuntimeError('No live radare2 session. Run ./coursectl start <lesson>.')
    return state


def rpc(method, params=None, *, state=None, timeout=60):
    state = state or session()
    request_id = secrets.randbelow(2**30)
    body = {'jsonrpc': '2.0', 'id': request_id, 'method': method}
    if params is not None:
        body['params'] = params
    request = urllib.request.Request(state['url'], data=json.dumps(body).encode(), headers={
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
        'Authorization': 'Bearer ' + state['token']})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f'radare2 connection failed ({type(exc).__name__}); check ./coursectl status.') from None
    if raw.startswith('event:') or raw.startswith('data:'):
        messages = [json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
        value = next((m for m in messages if m.get('id') == request_id), None)
        if value is None:
            raise RuntimeError('MCP stream did not return a response for this request.')
    else:
        value = json.loads(raw)
    if value.get('id') != request_id:
        raise RuntimeError('MCP response ID does not match the request.')
    if 'error' in value:
        raise RuntimeError('MCP error: ' + json.dumps(value['error']))
    return value['result']


def tool(name, arguments=None, *, state=None, timeout=60):
    value = rpc('tools/call', {'name': name, 'arguments': arguments or {}}, state=state, timeout=timeout)
    if value.get('isError'):
        raise RuntimeError('radare2 tool failed: ' + json.dumps(value['content']))
    return value


def output(value):
    return '\n'.join(block.get('text', '') for block in value.get('content', []) if block['type'] == 'text')


def command(text, **kwargs):
    value = tool('run_command', {'command': text, 'page_size': 10000}, **kwargs)
    pagination = value.get('pagination', {})
    if pagination.get('hasMore'):
        raise RuntimeError('The command returned more than one page. Use a focused query or the MCP tool cursor; do not treat this page as a complete result.')
    return value


def start_file(item, path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise RuntimeError('Select a regular file for analysis.')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = {'lesson': item['id'], 'example': 'file-' + digest[:12], 'binary': str(path),
                'source': None, 'binary_sha256': digest, 'bits': 64, 'optimization': 'external',
                'lab': item['lab'], 'platform': item['platform'], 'external': True, 'built_at': now()}
    return start(item, prepared=metadata)


def start(item, bits=None, optimization='O0', example=None, *, prepared=None):
    from .labs import select, prepare
    if prepared:
        spec, program = {'default': prepared['example']}, {'id': prepared['example']}
        bits, optimization = prepared['bits'], prepared['optimization']
    else:
        spec, program = select(item, example)
    bits = bits or program.get('bits', 64)
    executable = RUNTIME / 'src/radare2-mcp/src/r2mcp'
    if not executable.is_file():
        raise RuntimeError('Install tools first: ./coursectl bootstrap')
    with locked('session'):
        try:
            old = session()
        except RuntimeError:
            old = None
        if old:
            if (old['lesson'] != item['id'] or old['bits'] != bits or old['optimization'] != optimization
                    or old.get('example', spec['default']) != program['id']):
                raise RuntimeError('A different lab is active. Save your notes and run ./coursectl stop first.')
            rpc('ping', state=old, timeout=5)
            record(item, active=True)
            return old
        metadata = prepared or prepare(item, bits, optimization, program['id'])
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        token = secrets.token_hex(32)
        env = runtime_env()
        env['R2MCP_AUTH_TOKEN'] = token
        logfile = workdir() / 'r2-server.log'
        with logfile.open('ab') as log:
            os.chmod(logfile, 0o600)
            proc = subprocess.Popen([str(executable), '-H', f'127.0.0.1:{port}', '-r', '-g', 'all', '-n', '-N',
                                     '-c', 'e scr.color=0;e scr.utf8=false'], env=env,
                                    cwd=Path(metadata['binary']).parent, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=log, start_new_session=True)
        state = {**metadata, 'pid': proc.pid, 'process_start': process_start(proc.pid),
                 'url': f'http://127.0.0.1:{port}/', 'token': token, 'started_at': now()}
        try:
            deadline = time.monotonic() + 15
            while True:
                if proc.poll() is not None:
                    raise RuntimeError('radare2-mcp exited at startup. See work/r2-server.log.')
                try:
                    rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                                      'clientInfo': {'name': 'artik-course', 'version': '0.1.0'}}, state=state, timeout=1)
                    break
                except RuntimeError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)
            opened = tool('open_file', {'file_path': metadata['binary']}, state=state)
            if 'Failed to open file.' in output(opened):
                raise RuntimeError('radare2-mcp could not open the binary. Its open_file tool requires an absolute path without hidden directories.')
            # r2mcp opens with bin.cache=true; stale cached bytes can hide debugger
            # breakpoint writes. This lab must observe live memory and real writes.
            command('e bin.cache=false;e io.cache=false;e io.pcache=false;e scr.limit=16777216', state=state)
            command('aaa', state=state)
            write_json(workdir() / 'session.json', state)
            record(item, active=True)
            configure_hermes(state)
            _children[proc.pid] = proc
            return state
        except BaseException:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            raise


def stop():
    with locked('session'):
        try:
            state = session()
        except RuntimeError:
            return False
        try:
            if output(command('e cfg.debug', state=state, timeout=2)).strip() == 'true':
                command('dk 9', state=state, timeout=2)
        except RuntimeError:
            pass
        os.kill(state['pid'], signal.SIGTERM)
        deadline = time.monotonic() + 5
        while process_start(state['pid']) == state['process_start'] and time.monotonic() < deadline:
            time.sleep(0.1)
        if process_start(state['pid']) == state['process_start']:
            os.kill(state['pid'], signal.SIGKILL)
        owned = _children.pop(state['pid'], None)
        if owned:
            owned.wait(timeout=5)
        (workdir() / 'session.json').unlink(missing_ok=True)
        configure_hermes(None)
        return True


def settings():
    return read_json(workdir() / 'settings.json', {
        'provider': 'openrouter', 'model': 'anthropic/claude-sonnet-4.6',
        'key_env': 'OPENROUTER_API_KEY', 'key_file': None, 'base_url': None})


def update_settings(changes):
    config = settings()
    if changes.get('provider') and changes['provider'] != config['provider']:
        config.update(key_file=None, base_url=None,
                      key_env={'openrouter': 'OPENROUTER_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY',
                               'custom': 'OPENAI_API_KEY'}.get(changes['provider'], 'ARTIK_MODEL_API_KEY'))
    config.update({key: value for key, value in changes.items() if value is not None})
    write_json(workdir() / 'settings.json', config)
    return config


def load_key(path):
    text = Path(path).expanduser().read_text().strip()
    matches = set(re.findall(r'sk-or-v1-[A-Za-z0-9_-]+', text))
    if len(matches) == 1:
        return matches.pop()
    if len(matches) > 1:
        raise RuntimeError('The key file contains more than one OpenRouter credential.')
    if '\n' not in text and text and not any(c.isspace() for c in text):
        return text.strip('\"\'')
    raise RuntimeError('Use a key file containing one API key, or set the configured environment variable.')


def hermes_provider(config):
    # A named endpoint lets Hermes bind key_env to this URL explicitly. Its bare
    # custom provider intentionally does not forward OPENAI_API_KEY to any host.
    return 'artik-endpoint' if config['provider'] == 'custom' else config['provider']


def hermes_env():
    env = runtime_env()
    config = settings()
    key = load_key(config['key_file']) if config.get('key_file') else env.get(config['key_env'])
    if key:
        env[config['key_env']] = key
        native_key = {'openrouter': 'OPENROUTER_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY'}.get(config['provider'])
        if native_key:
            env[native_key] = key
    return env


def configure_hermes(state):
    config = settings()
    profile = workdir() / 'hermes'
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = profile / 'config.yaml'
    # JSON is valid YAML. Preserve edits made through Hermes' own configuration UI.
    if path.is_file():
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            parser = RUNTIME / 'venv/bin/python'
            data = json.loads(subprocess.check_output([str(parser), '-c',
                'import yaml,json,sys; print(json.dumps(yaml.safe_load(open(sys.argv[1])) or {}))', str(path)], text=True))
    else:
        data = {'terminal': {'backend': 'local', 'cwd': str(ROOT)},
                'memory': {'memory_enabled': True, 'user_profile_enabled': True}}
    data['model'] = {'default': config['model'], 'provider': hermes_provider(config)}
    if config.get('base_url'):
        data['model']['base_url'] = config['base_url']
    providers = data.setdefault('providers', {})
    if config['provider'] == 'custom':
        if not config.get('base_url'):
            raise RuntimeError('A custom provider requires --base-url (for example http://127.0.0.1:1234/v1).')
        providers['artik-endpoint'] = {'name': 'Course endpoint', 'base_url': config['base_url'],
                                       'key_env': config['key_env'], 'default_model': config['model'],
                                       'transport': 'chat_completions'}
    else:
        providers.pop('artik-endpoint', None)
    servers = data.setdefault('mcp_servers', {})
    if state:
        servers['radare2'] = {'url': state['url'], 'headers': {'Authorization': 'Bearer ' + state['token']},
                              'timeout': 120, 'connect_timeout': 10, 'supports_parallel_tool_calls': False}
    else:
        servers.pop('radare2', None)
    write_json(path, data)
    skills = profile / 'skills'
    skills.mkdir(exist_ok=True)
    dest = skills / 'artik-reversing'
    if not dest.exists():
        dest.symlink_to(ROOT / 'skills/artik-reversing', target_is_directory=True)
    return profile


def current_target(state=None):
    state = state or session()
    result = command('ij', state=state)
    info = json.loads(output(result).split('<log>', 1)[0])
    name = info.get('core', {}).get('file')
    path = None
    if name:
        for prefix in ('dbg://', 'file://'):
            if name.startswith(prefix):
                name = name[len(prefix):]
        candidate = Path(name)
        if candidate.is_absolute() and candidate.is_file():
            path = candidate
    return {'file': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path else None}, result


def snapshot(extra_commands=()):
    state = session()
    target, info = current_target(state)
    evidence = {'at': now(), 'lesson': state['lesson'], 'target': target,
                'prepared_binary': state['binary'], 'observations': [{'at': now(), 'command': 'ij', 'result': info}]}
    commands = ['s', 'aflj', 'CCj']
    if output(command('e cfg.debug', state=state)).strip() == 'true':
        commands += ['drj', 'dij', 'dbj']
    for text in [*commands, *extra_commands]:
        evidence['observations'].append({'at': now(), 'command': text, 'result': command(text)})
    dest = workdir() / 'evidence' / (time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3) + '.json')
    write_json(dest, evidence)
    record(lesson(state['lesson']), text='Evidence: ' + str(dest))
    return dest
