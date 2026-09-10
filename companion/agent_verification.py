"""Exercise the real configured Hermes provider, retaining its actual tool trace.

This measures agent integration. It never substitutes an LLM verdict for the
independent program checks or marks a whole article as validated.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess

from . import assets
from . import core as c
from . import labs


FOCUS = {
    '1': 'ABI x86-64, imports, function analysis, a real breakpoint, and a verified string patch.',
    '2': 'The index/content mismatch: this file duplicates the buffer overflow chapter. Identify its stack and unsafe input; do not invent the missing conditionals text.',
    '3': 'Compare conditional branches, switch cases, and loop back edges across the printed examples.',
    '4': 'Array indexing and contiguous memory, array initialization, and string byte indexing.',
    '4-ii': 'String input, strlen, and strncpy termination. Demonstrate the unterminated example using the existing sanitizer check.',
    '5': 'Integer/character promotion and float-to-integer conversion instructions and actual outputs.',
    '6': 'Multi-dimensional array layout and Books fields in memory. Contrast sizeof/alignment with stack spacing using coursectl layout.',
    '7': 'Student array record layout and the printed patching exercise. Patch a working binary and verify the effect.',
    '8': 'Write/read/seek/line reads and the actual files created; identify libc calls and buffers.',
    '8-i': 'The original IOLI crackmes. Recover passwords through disassembly, verify accepted/rejected inputs, and demonstrate one control-flow patch. List which of all ten you actually solve.',
    '9': 'Pointers and stack versus heap allocation; inspect pointer values and dereferenced arrays at a breakpoint.',
    '10': 'Pointer arithmetic versus value arithmetic, pointer arguments and heap structs. Explicitly identify the original pointer-step undefined behavior.',
    '11': 'Follow linked-list nodes in memory and use r2pipe on a separate analysis session; inspect enums and bitwise operations.',
    '12': 'Union overlapping fields, bitfields, and the absence of preprocessor macros as runtime objects.',
    '13': 'Libc versus direct syscalls, file descriptors/records, XOR decoding, and ESIL emulation using current radare2 syntax.',
    '14': 'PE headers and WinAPI imports for file operations; explain Windows calling convention from actual code. Windows execution is unavailable.',
    '15': 'Network byte order, sockaddr layout and both TCP client/server paths. Use coursectl verify for isolated live network checks.',
    '16': 'HTTP download, indirect execution, NX stack faults, rasm2/ragg2 and harmless shellcode examples. Network tests only through coursectl verify.',
    '17': 'Winsock imports, UDP/DNS packet construction and file encoding. Static only: do not contact external DNS or command servers.',
    '18': 'WinAPI process/socket plumbing of the bind and reverse shell examples, static only.',
    '19': 'TLS API flow and command execution path. Use coursectl verify for the isolated TLS test; do not launch the server directly on the host.',
    '20': 'Stack frame, unsafe input, overwrite offset and control-flow consequences. Network behavior only through the isolated verifier.',
    '21': 'NX/DEP and return-to-libc/ROP using the course binary; distinguish a normal main breakpoint from an actual successful ROP exercise.',
    '22': 'mprotect arguments, page alignment, and executable-stack behavior; distinguish static inspection from a successfully executed exploit.',
    '23': 'Canary prologue/epilogue, a real stack-smashing failure, and the leak path. Do not call the full bypass solved without proof.',
    '24': 'PIE/ASLR mappings over separate launches, PLT/GOT and existing call reuse. Verify any claimed bypass against the actual binary.',
    'malware1': 'C#/.NET analysis of Ziraat. The original Mediafire sample is missing; derive a study checklist from the source and report the missing specimen explicitly.',
    'malware2': 'The exact Emotet document is available. Extract VBA and form strings, decode the base64 UTF-16 PowerShell without executing it, and verify the five URLs against the article.',
    'malware3': 'Dridex unpacking: identify the debugger observations required at each stage and the missing original specimen/Windows environment. Never manufacture an unpacking trace.',
    'malware4': 'Ramnit multi-stage unpacking: identify each stage and required memory dumps. The original specimen and isolated Windows debugger are unavailable.',
    'malware5': 'The article unpacked IceID PE is available. Reverse its .data RC4 key/configuration, run the static extraction helper, and corroborate offsets/bytes in radare2. Packed-stage unpacking remains pending.',
    'malware6': 'DLL injection: inspect the actual compiled DLL exports and injector imports/code, and map LoadLibrary/remote-thread steps. Windows execution and reflective injection are pending.',
    'malware7': 'Inspect the printed PE/shellcode injection implementations and relocations. Separate these examples from the unavailable Parallax/process-hollowing dynamic exercise.',
}


def trace(directory):
    database = directory / 'hermes/state.db'
    if not database.is_file():
        return {'sessions': [], 'mcp_calls': 0, 'tool_calls': 0}
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        sessions = [dict(r) for r in db.execute('SELECT id,model,api_call_count,tool_call_count,estimated_cost_usd,end_reason FROM sessions')]
        tools = [dict(r) for r in db.execute("SELECT tool_name,content FROM messages WHERE role='tool'")]
        transcript = [dict(r) for r in db.execute('SELECT role,content,tool_calls,tool_name FROM messages ORDER BY id')]
    c.write_json(directory / 'transcript.json', transcript)
    return {'sessions': sessions, 'mcp_calls': sum(str(t['tool_name']).startswith('mcp__radare2__') for t in tools),
            'tool_calls': len(tools)}


def invoke(item, prompt, *, turns, seconds, log_path, resume=False):
    command = [str(c.ROOT / 'coursectl'), 'chat', item['id'], '--oneshot', '--max-turns', str(turns),
               '--run-budget', str(max(30, seconds - 20)), '--prompt', prompt]
    if resume:
        command += ['--resume', 'latest']
    with log_path.open('w') as log:
        process = subprocess.Popen(command, cwd=c.ROOT, env=c.runtime_env(), stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=seconds)
        except BaseException:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise


def complete(item, directory, state, report):
    from .conversations import persist_response
    saved = persist_response(item)
    if saved:
        report['saved_response'] = saved
    artifact = directory / 'agent-review.md'
    report.update(trace(directory))
    report['review'] = str(artifact) if artifact.is_file() else None
    report['snapshots'] = [str(p) for p in (directory / 'evidence').glob('*.json')]
    notes = c.notebook()['lessons'].get(item['id'], {}).get('notes', [])
    has_evidence = report['mcp_calls'] and (report['snapshots'] or (saved and saved.get('snapshot_error')))
    return (saved and notes
            and (not state or has_evidence))


def verify(lesson_id='all', max_turns=28, seconds=240, resume_run=None):
    if max_turns < 4 or seconds < 30:
        raise RuntimeError('Use at least 4 turns and 30 seconds for an agent check.')
    selected = c.catalog()['lessons'] if lesson_id == 'all' else [c.lesson(lesson_id)]
    config = c.settings()
    base = Path(resume_run).resolve(strict=True) if resume_run else c.workdir() / 'agent-verification' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    base.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get('ARTIK_COURSE_WORKDIR')
    reports = []
    try:
        for item in selected:
            directory = base / item['id']
            prior = c.read_json(directory / 'result.json')
            if prior and prior.get('status') in ('passed', 'reading_only') and prior.get('source_sha256') == item['source_sha256']:
                reports.append(prior)
                print(f'preserved    {item["id"]}', flush=True)
                continue
            os.environ['ARTIK_COURSE_WORKDIR'] = str(directory)
            c.write_json(c.workdir() / 'settings.json', config)
            report = {'lesson': item['id'], 'scope': 'Real Hermes integration and bounded practical review; not full article certification',
                      'source_sha256': item['source_sha256'], 'at': c.now()}
            try:
                programs = labs.specification(item)['examples']
                try:
                    state = c.session()
                except RuntimeError:
                    state = None
                if state and state['lesson'] != item['id']:
                    c.stop()
                    state = None
                if state:
                    c.configure_hermes(state)
                elif programs:
                    state = c.start(item)
                elif assets.specification(item).get('sha256'):
                    state = c.start_file(item, assets.fetch(item))
                else:
                    c.record(item, active=True)
                alias = item['aliases'][0] if item['aliases'] else item['id']
                prompt = (
                    'Realiza una revisión práctica autónoma de este artículo para un lector español. '
                    'Lee el artículo original y el manifiesto completo de ejemplos. Trabaja en el directorio privado '
                    f'{directory}; conserva todos los archivos distribuidos del repositorio. '
                    f'Objetivos: {FOCUS[alias]} '
                    'Usa las herramientas MCP radare2 directamente cuando haya un objetivo abierto y comprueba '
                    'tus conclusiones con datos reales. Puedes compilar otros ejemplos con coursectl build --example '
                    'y abrirlos con open_file en el mismo servidor; restablece bin.cache/io.cache/io.pcache=false. '
                    'No detengas el servidor MCP durante la conversación. Nunca ejecutes muestras de malware ni '
                    'binarios Windows en este anfitrión. Las pruebas de red se ejecutan con coursectl verify, que '
                    'las aísla sin salida a Internet. No supongas que los resultados del artículo coinciden con esta compilación. '
                    f'Antes de agotar el tiempo, escribe {directory / "agent-review.md"} con hallazgos, '
                    'comandos reproducibles, prácticas realmente comprobadas y prácticas pendientes. '
                    'Guarda una nota con coursectl note --file y, si hay sesión, un coursectl snapshot. '
                    'No marques el capítulo completo ni la práctica del lector como aprobados. '
                    'Empieza guardando un breve esquema del informe y actualízalo con la evidencia obtenida.'
                )
                # Reserve a separate turn for writing evidence. Exhausting the
                # analysis budget must not discard otherwise useful work.
                prior_trace = trace(directory)
                resumed = any(s.get('api_call_count', 0) for s in prior_trace['sessions'])
                if not resumed:
                    stale_db = directory / 'hermes/state.db'
                    if stale_db.is_file():
                        stale_db.unlink()
                    try:
                        code = invoke(item, prompt, turns=max_turns, seconds=seconds,
                                      log_path=directory / 'hermes.log')
                    except subprocess.TimeoutExpired:
                        code = 124
                        report['analysis_timeout'] = True
                else:
                    code = prior.get('exit_code', 0) if prior else 0
                    report['resumed'] = True
                if not complete(item, directory, state, report):
                    finalize = (
                        'Termina y guarda la revisión anterior ahora, usando la evidencia que ya obtuviste. '
                        'El presupuesto anterior se agotó; no empieces otras prácticas ni amplíes el alcance. '
                        f'Escribe el informe completo en {directory / "agent-review.md"}, sustituyendo el esquema vacío. '
                        'Distingue resultados observados, inferencias y ejercicios pendientes. '
                        'La sesión de radare2 puede haberse reiniciado: consulta su estado actual y no atribuyas '
                        'registros históricos al nuevo proceso. Si existe MCP, realiza una observación actual '
                        'con su run_command y guarda coursectl snapshot. '
                        f'Guarda coursectl note --file {directory / "agent-review.md"}. '
                        'No declares el capítulo entero aprobado ni marques práctica del lector. '
                        'Prioriza escribir el informe y la nota en tus primeras llamadas a herramientas.'
                    )
                    try:
                        code = invoke(item, finalize, turns=12, seconds=180,
                                      log_path=directory / 'hermes-finalize.log', resume=bool(trace(directory)['sessions']))
                    except subprocess.TimeoutExpired:
                        code = 124
                        report['finalization_timeout'] = True
                report['exit_code'] = code
                finished = complete(item, directory, state, report)
                if not finished:
                    raise RuntimeError('Incomplete agent integration check: requires a review, saved note, and actual MCP calls/snapshot when a target is present.')
                report['status'] = 'passed' if state else 'reading_only'
                if not state:
                    report['reason'] = assets.specification(item).get('reason', 'No target asset available.')
            except Exception as exc:
                report.update(trace(directory))
                report.update(status='failed', reason=str(exc))
            finally:
                c.stop()
            c.write_json(directory / 'result.json', report)
            reports.append(report)
            c.write_json(base / 'report.json', {'at': c.now(), 'articles': reports})
            print(f'{report["status"]:12} {item["id"]} ({report.get("mcp_calls", 0)} MCP calls)', flush=True)
    finally:
        if previous is None:
            os.environ.pop('ARTIK_COURSE_WORKDIR', None)
        else:
            os.environ['ARTIK_COURSE_WORKDIR'] = previous
    print('Agent evidence:', base / 'report.json')
    return base / 'report.json'
