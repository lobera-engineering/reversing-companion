"""Command-line interface exposed as ``./coursectl``."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import webbrowser

from . import core as c
from . import labs


def show(item):
    print(item['title'])
    print(item['url'])
    print('Local text:', c.ROOT / item['content'])
    print('Lab:', item['lab'] or 'not packaged yet')
    print('Examples:', item.get('examples', 0))
    for issue in item['issues']:
        print('Editorial note:', issue)


def chat(args):
    item = c.lesson(args.lesson)
    if labs.specification(item).get('examples'):
        try:
            state = c.session()
        except RuntimeError:
            state = None
        if state and state['lesson'] != item['id']:
            raise RuntimeError('Another lab is active. Run ./coursectl stop before changing lessons.')
        if state and args.example and state.get('example', labs.specification(item)['default']) != args.example:
            raise RuntimeError('Another example is active. Run ./coursectl stop before changing examples.')
        state = state or c.start(item, example=args.example)
    else:
        try:
            state = c.session()
        except RuntimeError:
            state = None
        if state and state['lesson'] != item['id']:
            raise RuntimeError('Another lab is active. Run ./coursectl stop before changing lessons.')
    c.configure_hermes(state)
    config = c.settings()
    env = c.hermes_env()
    hermes = c.RUNTIME / 'venv/bin/hermes'
    if not hermes.is_file():
        raise RuntimeError('Install Hermes first: ./coursectl bootstrap')
    if config['provider'] == 'openrouter' and not env.get('OPENROUTER_API_KEY'):
        raise RuntimeError('Configure OpenRouter: ./coursectl configure --key-file /path/to/key.txt')
    c.record(item, active=True)
    context = (f'Active course lesson: {item["id"]}. Article: {item["content"]}. '
               f'Web: {item["url"]}. Notebook: {c.workdir() / "notebook.json"}. '
               f'The shared radare2 session is {"running" if state else "not running"}. '
               'Read the current lab state before deciding what to do. ')
    request = args.prompt or 'Presenta brevemente esta lección y pregunta qué me gustaría trabajar.'
    command = [str(hermes), 'chat', '--provider', c.hermes_provider(config), '--model', config['model'],
               '--skills', 'artik-reversing', '--query', context + request]
    if args.oneshot:
        command.append('--oneshot')
    if args.resume:
        command += ['--resume', args.resume]
    if args.max_turns:
        command += ['--max-turns', str(args.max_turns)]
    if args.run_budget:
        command += ['--run-budget', str(args.run_budget)]
    result = subprocess.run(command, cwd=c.ROOT, env=env)
    from .conversations import persist_response
    saved = persist_response(item)
    if saved:
        print('Saved model response:', saved['path'])
    raise SystemExit(result.returncode)


def doctor():
    env = c.runtime_env()
    okay = True
    for name, path, args in [
        ('radare2', c.RUNTIME / 'radare/usr/bin/r2', ['-v']),
        ('radare2-mcp', c.RUNTIME / 'src/radare2-mcp/src/r2mcp', ['-v']),
        ('Hermes', c.RUNTIME / 'venv/bin/python', ['-c', 'from importlib.metadata import version; print(version("hermes-agent"))'])]:
        if not path.is_file():
            print(f'{name}: missing (./coursectl bootstrap)')
            okay = False
            continue
        result = subprocess.run([str(path), *args], capture_output=True, text=True, env=env, timeout=20)
        text = (result.stdout or result.stderr).splitlines()
        print(name + ': ' + (text[0] if text else str(result.returncode)))
        okay &= result.returncode == 0
    data = c.catalog()
    missing = [x['id'] for x in data['lessons'] if not (c.ROOT / x['content']).is_file()]
    print(f'Course: {len(data["lessons"])} lessons; {len(missing)} missing files')
    config = c.settings()
    print(f'Model: {config["provider"]} / {config["model"]}')
    configured = bool(os.environ.get(config['key_env']))
    if config.get('key_file'):
        try:
            configured = bool(c.load_key(config['key_file']))
        except (OSError, RuntimeError):
            configured = False
    print('Credential: ' + ('configured' if configured else 'not configured'))
    try:
        state = c.session()
    except RuntimeError:
        print('Shared session: stopped')
    else:
        try:
            tools = c.rpc('tools/list', state=state, timeout=5)['tools']
            print(f'Shared session: {state["lesson"]}; {len(tools)} tools')
            okay &= any(x['name'] == 'run_command' for x in tools)
        except RuntimeError:
            print('Shared session: process alive, MCP not responding')
            okay = False
    return 0 if okay and not missing else 1


def main():
    parser = argparse.ArgumentParser(description='Artik Blue: reversing course with Hermes and radare2.')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('bootstrap', help='Install pinned tools locally')
    sub.add_parser('doctor', help='Check installation and configuration')
    p = sub.add_parser('import', help='Import the local blog sources')
    p.add_argument('source', type=Path)
    p = sub.add_parser('list', help='List all lessons')
    p.add_argument('--json', action='store_true')
    p = sub.add_parser('verify', help='Run real program checks and preserve the evidence')
    p.add_argument('lesson', nargs='?', default='all')
    p = sub.add_parser('verify-agent', help='Run real Hermes checks (uses the configured model API)')
    p.add_argument('lesson', nargs='?', default='all')
    p.add_argument('--max-turns', type=int, default=28)
    p.add_argument('--seconds', type=int, default=240)
    p.add_argument('--resume-run', type=Path, help='Resume a retained batch without repeating successful checks')
    p = sub.add_parser('open', help='Open a supplied exercise file in the shared session')
    p.add_argument('lesson')
    p.add_argument('path', type=Path)
    p = sub.add_parser('assets', help='Inspect or fetch the original external exercise assets')
    p.add_argument('lesson')
    p.add_argument('--fetch', action='store_true')
    p.add_argument('--analyze', action='store_true')
    for name in ('lesson', 'read', 'web', 'build', 'start', 'layout', 'examples'):
        p = sub.add_parser(name)
        p.add_argument('lesson', nargs='?')
        if name in ('build', 'start'):
            p.add_argument('--example', help='Program identifier shown by examples')
            p.add_argument('--bits', type=int, choices=(32, 64))
            p.add_argument('--optimization', choices=('O0', 'O1', 'O2', 'O3', 'Os'), default='O0')
    for name in ('status', 'stop', 'console'):
        sub.add_parser(name)
    p = sub.add_parser('snapshot', help='Capture observations from the current target')
    p.add_argument('--command', action='append', default=[], help='Additional radare2 observation to capture')
    p = sub.add_parser('r2', help='Run a command in the shared radare2 session')
    p.add_argument('command')
    p.add_argument('--timeout', type=float, default=120)
    p.add_argument('--json', action='store_true')
    p = sub.add_parser('note', help='Add a note to the active lesson')
    p.add_argument('text', nargs='?')
    p.add_argument('--file', type=Path, help='Read a longer note from a UTF-8 file')
    p = sub.add_parser('progress', help='Show progress or set the active lesson status')
    p.add_argument('--set', choices=('in_progress', 'ai_completed', 'practiced', 'reviewed'))
    p = sub.add_parser('configure', help='Choose a provider, model and credential source')
    p.add_argument('--provider')
    p.add_argument('--model')
    p.add_argument('--key-env')
    p.add_argument('--key-file')
    p.add_argument('--base-url')
    p.add_argument('--clear-key-file', action='store_true')
    p = sub.add_parser('chat', help='Study and reverse with Hermes')
    p.add_argument('lesson', nargs='?')
    p.add_argument('--example')
    p.add_argument('--prompt')
    p.add_argument('--oneshot', action='store_true')
    p.add_argument('--resume')
    p.add_argument('--max-turns', type=int)
    p.add_argument('--run-budget', type=float, help='Per-turn time budget in seconds')
    p = sub.add_parser('hermes', help='Use the native Hermes CLI with the course profile')
    p.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        dispatch(args)
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        raise SystemExit(130) from None


def dispatch(args):
    action = args.action
    if action == 'bootstrap':
        from scripts.bootstrap import main
        main()
    elif action == 'import':
        from scripts.import_course import import_course
        import_course(args.source)
    elif action == 'doctor':
        raise SystemExit(doctor())
    elif action == 'verify':
        from .verification import verify
        verify(args.lesson)
    elif action == 'verify-agent':
        from .agent_verification import verify
        verify(args.lesson, args.max_turns, args.seconds, args.resume_run)
    elif action == 'open':
        state = c.start_file(c.lesson(args.lesson), args.path)
        print('Shared analysis target:', state['binary'])
    elif action == 'assets':
        from . import assets
        item = c.lesson(args.lesson)
        if args.fetch:
            print(assets.fetch(item))
        if args.analyze:
            print(json.dumps(assets.analyze(item), indent=2))
        if not args.fetch and not args.analyze:
            print(json.dumps(assets.specification(item), indent=2))
    elif action == 'list':
        rows = c.catalog()['lessons']
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                label = row['aliases'][0] if row['aliases'] else row['id']
                print(f'{label:12} [{row["validation"]}] {row["title"]}')
    elif action in ('lesson', 'read', 'web'):
        item = c.lesson(args.lesson)
        c.record(item, active=True)
        if action == 'read':
            print((c.ROOT / item['content']).read_text())
        elif action == 'web':
            print(item['url'])
            webbrowser.open(item['url'])
        else:
            show(item)
    elif action in ('build', 'start'):
        item = c.lesson(args.lesson)
        value = (c.start if action == 'start' else c.build)(item, args.bits, args.optimization, args.example)
        print('Binary:', value['binary'])
        if action == 'start':
            print('Shared session ready. Use ./coursectl console or ./coursectl chat')
    elif action == 'layout':
        print(json.dumps(c.layout(c.lesson(args.lesson)), indent=2))
    elif action == 'examples':
        for example in labs.specification(c.lesson(args.lesson))['examples']:
            print(f'{example["id"]:24} {example["platform"]:8} {example["title"]}')
    elif action == 'stop':
        print('Session stopped.' if c.stop() else 'No live session.')
    elif action == 'status':
        data = c.notebook()
        print('Lesson:', data['active_lesson'] or 'not selected')
        try:
            state = c.session()
            print('Active lab lesson:', state['lesson'])
            target, _ = c.current_target(state)
            print('Prepared binary:', state['binary'])
            print('Current target:', target['file'] or 'no file open')
            print('Process:', state['pid'])
            print('Current address:', c.output(c.command('s')))
        except RuntimeError as exc:
            print(str(exc))
    elif action == 'r2':
        value = c.command(args.command, timeout=args.timeout)
        print(json.dumps(value, indent=2) if args.json else c.output(value))
    elif action == 'console':
        import readline
        history = c.workdir() / 'console.history'
        if history.exists():
            readline.read_history_file(history)
        c.session()
        print('Shared radare2 command console. :quit exits this console; the session stays alive.')
        try:
            while True:
                try:
                    text = input('r2> ')
                except EOFError:
                    break
                if text.strip() in (':quit', ':q'):
                    break
                if text.strip():
                    try:
                        print(c.output(c.command(text, timeout=120)))
                    except RuntimeError as exc:
                        print(str(exc), file=sys.stderr)
        finally:
            readline.write_history_file(history)
    elif action == 'snapshot':
        print(c.snapshot(args.command))
    elif action == 'note':
        if bool(args.text is not None) == bool(args.file):
            raise RuntimeError('Supply note text or --file, exactly one.')
        c.record(c.lesson(), text=args.file.read_text() if args.file else args.text)
        print('Note saved.')
    elif action == 'progress':
        if args.set:
            c.record(c.lesson(), status=args.set)
        print(json.dumps(c.notebook(), indent=2, ensure_ascii=False))
    elif action == 'configure':
        changes = {}
        for key in ('provider', 'model', 'key_env', 'key_file', 'base_url'):
            value = getattr(args, key)
            if value is not None:
                changes[key] = str(Path(value).expanduser().resolve()) if key == 'key_file' else value
        config = c.update_settings(changes)
        if args.clear_key_file:
            config['key_file'] = None
        c.write_json(c.workdir() / 'settings.json', config)
        try:
            state = c.session()
        except RuntimeError:
            state = None
        c.configure_hermes(state)
        print(f'Provider: {config["provider"]}; model: {config["model"]}')
    elif action == 'chat':
        chat(args)
    elif action == 'hermes':
        env = c.hermes_env()
        arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
        raise SystemExit(subprocess.call([str(c.RUNTIME / 'venv/bin/hermes'), *arguments], cwd=c.ROOT, env=env))
