"""Windows VM integration via VBoxManage guestcontrol.

Architecture: each high-level operation (debug, execute) runs as a SINGLE
guestcontrol session executing a generated batch script.  Inside that
script, r2mcp is launched with ``start /b`` and curl drives it.  This
avoids session accumulation — the #1 cause of VERR_DUPLICATE and VM aborts.

NEVER use ``pkill`` or ``kill`` on arbitrary VBoxManage processes — that
can abort the VM.  Always stop guest processes via ``taskkill`` inside
the guest, and stop the host-side Popen via its handle.
"""
import json
import secrets
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path

from . import core as c

VM_NAME = 'W11'
VM_USER = 'lab'
VM_PASSWORD = 'lab'
VM_R2_DIR = 'C:\\lab\\r2\\bin'
VM_LAB_DIR = 'C:\\lab'
VM_PORT_BASE = 9800
VM_PORT_RANGE = 200
_GC_TIMEOUT_MS = '480000'

_last_gc = 0.0


def _gc_run(exe, *args, timeout=30):
    global _last_gc
    elapsed = time.monotonic() - _last_gc
    if elapsed < 2.0:
        time.sleep(2.0 - elapsed)
    cmd = ['VBoxManage', 'guestcontrol', VM_NAME, 'run',
           '--exe', exe, '--username', VM_USER, '--password', VM_PASSWORD,
           '--wait-stdout', '--wait-stderr',
           '--timeout', _GC_TIMEOUT_MS, '--']
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=timeout, errors='replace')
    _last_gc = time.monotonic()
    return result.stdout, result.stderr, result.returncode


def _gc_copy(local_path, remote_dir):
    global _last_gc
    elapsed = time.monotonic() - _last_gc
    if elapsed < 2.0:
        time.sleep(2.0 - elapsed)
    subprocess.run(
        ['VBoxManage', 'guestcontrol', VM_NAME, 'copyto',
         '--username', VM_USER, '--password', VM_PASSWORD,
         '--target-directory', remote_dir, str(local_path)],
        check=True, capture_output=True, timeout=60)
    _last_gc = time.monotonic()


def _cmd(command_str, timeout=30):
    return _gc_run('C:\\Windows\\System32\\cmd.exe', '/c', command_str,
                   timeout=timeout)


def vm_ready():
    try:
        out, _, _ = _cmd('echo READY', timeout=15)
        return 'READY' in out
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def copy_binary(local_path):
    local_path = Path(local_path).resolve()
    subdir = f'run-{secrets.token_hex(4)}'
    remote_dir = f'{VM_LAB_DIR}\\bins\\{subdir}'
    _cmd(f'md {remote_dir} 2>nul')
    _gc_copy(local_path, f'{remote_dir}\\')
    return f'{remote_dir}\\{local_path.name}'


def _mcp_curl(token, port, method, params=None, request_id=1, timeout=10):
    """Return a batch-script curl line that calls an MCP method."""
    body = {'jsonrpc': '2.0', 'id': request_id, 'method': method}
    if params is not None:
        body['params'] = params
    payload = json.dumps(body).replace('"', '\\"')
    return (
        f'curl -s -m {timeout} '
        f'-H "Authorization: Bearer {token}" '
        f'-H "Content-Type: application/json" '
        f'-d "{payload}" '
        f'http://127.0.0.1:{port}/')


def _pick_port():
    """Choose a random port in the configured range."""
    import random
    return VM_PORT_BASE + random.randint(0, VM_PORT_RANGE - 1)


def _start_r2mcp_bg(binary_path, token, port):
    """Start r2mcp on the VM via a host-side Popen (1 persistent session)."""
    _cmd('taskkill /F /IM r2mcp.exe 2>nul', timeout=30)
    time.sleep(5)
    cmd_line = (
        f'set PATH={VM_R2_DIR};%PATH% && '
        f'{VM_R2_DIR}\\r2mcp.exe -H 0.0.0.0:{port} -a {token} '
        f'-r -g all '
        f'-c "e scr.color=0;e scr.utf8=false" '
        f'{binary_path} > {VM_LAB_DIR}\\r2mcp.log 2>&1')
    bg = subprocess.Popen(
        ['VBoxManage', 'guestcontrol', VM_NAME, 'run',
         '--exe', 'C:\\Windows\\System32\\cmd.exe',
         '--username', VM_USER, '--password', VM_PASSWORD,
         '--wait-stdout', '--wait-stderr', '--', '/c', cmd_line],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL)
    poll_cmd = (
        f'for /L %i in (1,1,30) do ('
        f'netstat -an 2>nul | findstr {port} | findstr LISTENING >nul '
        f'&& (echo PORT_READY & exit /b 0) '
        f'& ping -n 4 127.0.0.1 >nul)')
    try:
        out, _, _ = _cmd(poll_cmd, timeout=150)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        out = ''
    if bg.poll() is not None or 'PORT_READY' not in out:
        bg.terminate()
        try:
            bg.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bg.kill()
        raise RuntimeError('r2mcp did not start on the Windows VM.')
    return bg


def _stop_r2mcp_bg(bg):
    """Stop r2mcp on the VM."""
    try:
        _cmd('taskkill /F /IM r2mcp.exe 2>nul', timeout=30)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    if bg and bg.poll() is None:
        bg.terminate()
        try:
            bg.wait(timeout=8)
        except subprocess.TimeoutExpired:
            bg.kill()
    time.sleep(3)
    for _ in range(6):
        if vm_ready():
            break
        time.sleep(3)


def debug_session(binary_path):
    """Run full debug flow using host-side Popen for r2mcp + batch for curl.

    r2mcp runs in its own guestcontrol session (via host Popen).
    All MCP curl commands run in a SINGLE second guestcontrol session
    via a batch script — this avoids session accumulation.
    """
    token = secrets.token_hex(16)
    port = _pick_port()
    rid = [0]

    def r2curl(cmd, timeout=30):
        rid[0] += 1
        return _mcp_curl(token, port, 'tools/call', {
            'name': 'run_command',
            'arguments': {'command': cmd, 'page_size': 100000}
        }, rid[0], timeout=timeout)

    bg = _start_r2mcp_bg(binary_path, token, port)
    try:
        rid[0] += 1
        init_curl = _mcp_curl(token, port, 'initialize', {
            'protocolVersion': '2025-03-26', 'capabilities': {},
            'clientInfo': {'name': 'artik-course-vm', 'version': '0.1.0'}
        }, rid[0], timeout=10)

        rid[0] += 1
        open_curl = _mcp_curl(token, port, 'tools/call', {
            'name': 'open_file', 'arguments': {'file_path': binary_path}
        }, rid[0], timeout=15)

        dc_block = []
        dc_cmd = 'dc;?e ---DRJ---;drj;?e ---DIJ---;dij'
        for i in range(8):
            dc_block.append(f'echo DC_START:{i}')
            dc_out = f'{VM_LAB_DIR}\\dc_out.txt'
            dc_timeout = 40 if i == 0 else 20
            dc_block.append(
                r2curl(dc_cmd, timeout=dc_timeout)
                + f' > {dc_out} 2>&1')
            dc_block.append(f'type {dc_out}')
            dc_block.append('echo.')
            dc_block.append(f'echo DC_END:{i}')
            if i > 0:
                dc_block.append(
                    f'findstr "breakpoint" {dc_out} '
                    '>nul 2>&1 && goto dc_done')
        dc_block.append(':dc_done')

        dc_section = '\n'.join(dc_block)

        script = textwrap.dedent(f"""\
            @echo off
            echo PHASE:initialize
            {init_curl}
            echo.

            echo PHASE:open_file
            {open_curl}
            echo.

            echo PHASE:aaa1
            {r2curl('aaa', timeout=55)}
            echo.

            echo PHASE:ood
            {r2curl('ood', timeout=25)}
            echo.

            echo PHASE:aaa2
            {r2curl('aaa', timeout=55)}
            echo.

            echo PHASE:debug_config
            {r2curl('e dbg.bpinmaps=false', timeout=10)}
            echo.
            {r2curl('e dbg.hwbp=true', timeout=10)}
            echo.

            echo PHASE:resolve_main
            echo ADDR_START
            {r2curl('?v dbg.main', timeout=10)}
            echo.
            echo ADDR_END

            echo PHASE:clear_and_set_breakpoint
            {r2curl('db- *', timeout=10)}
            echo.
            {r2curl('db dbg.main', timeout=10)}
            echo.

            echo PHASE:dc_loop
            {dc_section}

            echo PHASE:stack_dump
            {r2curl('pxj 64 @ rsp', timeout=10)}
            echo.

            echo PHASE:done
        """)

        local_script = Path(tempfile.gettempdir()) / 'coursectl_debug.bat'
        local_script.write_text(script, encoding='utf-8')
        _gc_copy(local_script, f'{VM_LAB_DIR}\\')

        out, err, code = _gc_run(
            'C:\\Windows\\System32\\cmd.exe', '/c',
            f'{VM_LAB_DIR}\\coursectl_debug.bat',
            timeout=420)

        return _parse_debug_output(out)
    finally:
        _stop_r2mcp_bg(bg)


def _parse_debug_output(raw_output):
    """Parse the all-in-one debug batch script output."""
    lines = raw_output.splitlines()
    evidence = []

    if 'RESULT:port_timeout' in raw_output:
        return {'status': 'failed', 'reason': 'r2mcp did not start listening.'}

    addr_text = _extract_between(lines, 'ADDR_START', 'ADDR_END')
    address = 0
    if addr_text:
        try:
            text = _parse_mcp_text(addr_text)
            address = int(text, 0)
            evidence.append({'command': '?v dbg.main', 'address': hex(address)})
        except (json.JSONDecodeError, ValueError):
            pass

    if address == 0:
        return {'status': 'failed', 'reason': 'No main function found after debug analysis.'}

    for i in range(8):
        dc_text = _extract_between(lines, f'DC_START:{i}', f'DC_END:{i}')
        if not dc_text:
            continue
        try:
            full_text = _parse_mcp_text(dc_text)
        except (json.JSONDecodeError, ValueError, IndexError):
            continue
        drj_raw, dij_raw = '', ''
        if '---DRJ---' in full_text and '---DIJ---' in full_text:
            parts = full_text.split('---DRJ---', 1)
            rest = parts[1] if len(parts) > 1 else ''
            drj_dij = rest.split('---DIJ---', 1)
            drj_raw = drj_dij[0].strip()
            dij_raw = drj_dij[1].strip() if len(drj_dij) > 1 else ''
        if not drj_raw:
            evidence.append({'dc_iter': i, 'raw': full_text[:200]})
            continue
        try:
            regs = json.loads(drj_raw)
            reason = json.loads(dij_raw) if dij_raw else {}
            pc = regs.get('rip', regs.get('eip', 0))
            evidence.append({'dc_iter': i, 'pc': hex(pc),
                             'stopreason': reason.get('stopreason')})
            if pc == address and reason.get('stopreason') == 'breakpoint':
                return {'status': 'passed', 'address': address, 'evidence': evidence}
        except (json.JSONDecodeError, ValueError):
            evidence.append({'dc_iter': i, 'raw': full_text[:200]})
            continue

    return {'status': 'failed',
            'reason': 'Debugger did not stop at breakpoint after multiple continues.',
            'evidence': evidence}


def _extract_between(lines, start_marker, end_marker):
    """Extract text between two marker lines."""
    capturing = False
    captured = []
    for line in lines:
        stripped = line.strip()
        if start_marker in stripped:
            capturing = True
            continue
        if end_marker in stripped:
            return '\n'.join(captured).strip()
        if capturing:
            captured.append(stripped)
    return '\n'.join(captured).strip()


def _parse_mcp_text(raw):
    """Extract the text content from an MCP tools/call response."""
    if not raw:
        return ''
    if raw.startswith('event:') or raw.startswith('data:'):
        for part in raw.split('\n'):
            if part.startswith('data:'):
                raw = part[5:].strip()
                break
    resp = json.loads(raw)
    result = resp.get('result', {})
    content = result.get('content', [{}])
    text = content[0].get('text', '') if content else ''
    return text.split('<log>', 1)[0].strip()


def _bg_execute(binary_path, args_str, remote_dir, wait_seconds):
    """Run a program as a background Popen, collect output after timeout."""
    out_file = f'{VM_LAB_DIR}\\exec_out.txt'
    cmd_line = f'cd /d {remote_dir} && {binary_path} {args_str} > {out_file} 2>&1'
    bg = subprocess.Popen(
        ['VBoxManage', 'guestcontrol', VM_NAME, 'run',
         '--exe', 'C:\\Windows\\System32\\cmd.exe',
         '--username', VM_USER, '--password', VM_PASSWORD,
         '--wait-stdout', '--wait-stderr', '--', '/c', cmd_line],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL)
    time.sleep(wait_seconds)
    binary_name = binary_path.rsplit('\\', 1)[-1]
    try:
        _cmd(f'taskkill /F /IM {binary_name} 2>nul', timeout=10)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    if bg.poll() is None:
        bg.terminate()
        try:
            bg.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bg.kill()
    time.sleep(1)
    out, _, _ = _cmd(f'type {out_file} 2>nul', timeout=10)
    return out, '', 0


def vm_execute(binary_path, program):
    results = []
    for case in program.get('cases', []):
        for setup_cmd in case.get('setup', []):
            _cmd(setup_cmd, timeout=15)
        args_str = ' '.join(case.get('args', []))
        remote_dir = '\\'.join(binary_path.rsplit('\\', 1)[:-1])
        cmd_line = f'cd /d {remote_dir} && {binary_path} {args_str}'
        bg_timeout = case.get('bg_timeout')
        if bg_timeout:
            out, err, code = _bg_execute(
                binary_path, args_str, remote_dir, bg_timeout)
        else:
            out, err, code = _gc_run(
                'C:\\Windows\\System32\\cmd.exe', '/c', cmd_line,
                timeout=15)
        missing = [text for text in case['contains'] if text not in out]
        if missing:
            raise RuntimeError(
                f'Missing expected output {missing!r}; got {out!r}, stderr={err!r}.')
        expected_signal = case.get('signal')
        if not expected_signal and code < 0:
            raise RuntimeError(f'Unexpected exit code {code}.')
        for name, expected in case.get('files', {}).items():
            file_out, _, _ = _cmd(f'type {remote_dir}\\{name}', timeout=10)
            if file_out.strip() != expected.strip():
                raise RuntimeError(f'{name}: expected {expected!r}; got {file_out!r}.')
        for path, expected in case.get('check_files', {}).items():
            file_out, _, _ = _cmd(f'type {path}', timeout=10)
            if expected not in file_out:
                raise RuntimeError(
                    f'{path}: expected to contain {expected!r}; got {file_out!r}.')
        for teardown_cmd in case.get('teardown', []):
            try:
                _cmd(teardown_cmd, timeout=15)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
        results.append({'command': cmd_line, 'stdin': case.get('stdin', ''),
                        'exit_code': code, 'stdout': out, 'stderr': err})
    if not results:
        return {'status': 'pending',
                'reason': 'A behavioral recipe is still required for this program.'}
    return {'status': 'passed', 'cases': results}


def install_r2():
    """Copy radare2 + r2mcp binaries to the VM. Idempotent."""
    out, _, _ = _cmd(f'if exist {VM_R2_DIR}\\r2mcp.exe (echo INSTALLED) '
                     f'else (echo MISSING)', timeout=15)
    if 'INSTALLED' in out:
        return True
    r2_win = c.RUNTIME / 'radare2-w64'
    r2_bin = r2_win / 'bin'
    sdb_dll = r2_win / 'lib' / 'libsdb.dll'
    if not r2_bin.is_dir():
        raise RuntimeError(
            f'radare2 Windows binaries not found at {r2_win}. '
            'Extract the radare2 Windows release into .runtime/radare2-w64/.')
    _cmd(f'md {VM_LAB_DIR}\\r2\\bin 2>nul')
    subprocess.run(
        ['VBoxManage', 'guestcontrol', VM_NAME, 'copyto',
         '--username', VM_USER, '--password', VM_PASSWORD,
         '--target-directory', f'{VM_R2_DIR}\\', '--recursive',
         str(r2_bin) + '/'],
        check=True, capture_output=True, timeout=120)
    if sdb_dll.is_file():
        _gc_copy(sdb_dll, f'{VM_R2_DIR}\\')
    out, _, _ = _cmd(f'echo test & {VM_R2_DIR}\\radare2.exe -v', timeout=15)
    if 'radare2' not in out:
        raise RuntimeError('radare2 installation verification failed.')
    return True
