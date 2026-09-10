"""Integration checks use real GCC, radare2 and MCP; no LLM/API charges."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from companion import core as c


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='artik-course-test-')
        self.previous = os.environ.get('ARTIK_COURSE_WORKDIR')
        os.environ['ARTIK_COURSE_WORKDIR'] = self.temp.name

    def tearDown(self):
        c.stop()
        if self.previous is None:
            os.environ.pop('ARTIK_COURSE_WORKDIR', None)
        else:
            os.environ['ARTIK_COURSE_WORKDIR'] = self.previous
        self.temp.cleanup()

    def cli(self, *args):
        return subprocess.check_output([str(c.ROOT / 'coursectl'), *args], env=c.runtime_env(), text=True)

    def test_imported_sources_and_editorial_gap(self):
        rows = c.catalog()['lessons']
        self.assertEqual(33, len(rows))
        self.assertEqual(33, len({r['id'] for r in rows}))
        for row in rows:
            self.assertEqual(row['source_sha256'], hashlib.sha256((c.ROOT / row['content']).read_bytes()).hexdigest())
        self.assertTrue(c.lesson('2')['issues'])

    def test_build_keeps_reader_changes_and_records_the_actual_binary(self):
        item = c.lesson('1')
        before = c.build(item)
        self.assertEqual('Hello, World!', subprocess.check_output([before['binary']], text=True))
        source = Path(before['source'])
        source.write_text(source.read_text().replace('Hello, World!', 'Reader experiment'))
        after = c.build(item)
        self.assertEqual('Reader experiment', subprocess.check_output([after['binary']], text=True))
        self.assertNotEqual(before['source_sha256'], after['source_sha256'])
        self.assertEqual(after['binary_sha256'], hashlib.sha256(Path(after['binary']).read_bytes()).hexdigest())

    def test_two_clients_share_address_comments_and_flags(self):
        first = c.start(c.lesson('1'))
        main = int(c.output(c.command('?v main')).strip(), 0)
        self.cli('r2', f's {main};f reader_marker={main};CC reader-observation @ {main}')
        self.assertEqual(main, int(c.output(c.command('s')).strip(), 0))
        self.assertIn('reader_marker', c.output(c.command('fj')))
        self.assertIn('reader-observation', c.output(c.command('CCj')))
        again = c.start(c.lesson('1'))
        self.assertEqual(first['pid'], again['pid'])
        self.assertIn('reader_marker', c.output(c.command('fj')))
        with self.assertRaises(RuntimeError):
            c.start(c.lesson('6'))
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(first['url'], data=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
                                   headers={'Content-Type': 'application/json'}), timeout=5)
        self.assertEqual(401, error.exception.code)

    def test_breakpoint_hits_and_memory_can_be_read(self):
        c.start(c.lesson('6'))
        operations = json.loads(c.output(c.command('pdfj @ main')))['ops']
        first_print = next(op['addr'] for op in operations if op.get('type') == 'call' and 'printf' in op.get('disasm', ''))
        c.command('ood')
        c.command(f'db {first_print}')
        c.command('dc')
        regs = json.loads(c.output(c.command('drj')))
        self.assertEqual(first_print, regs['rip'])
        reason = json.loads(c.output(c.command('dij')))
        self.assertEqual('breakpoint', reason['stopreason'])
        # Both initialized book IDs must exist in the main stack frame, in order.
        memory = bytes(json.loads(c.output(c.command(f'pxj 512 @ {regs["rbp"] - 512}'))))
        first = (6495407).to_bytes(4, 'little')
        second = (6495700).to_bytes(4, 'little')
        self.assertIn(first, memory)
        self.assertIn(second, memory)
        self.assertEqual(208, memory.index(second) - memory.index(first))
        c.command('dk 9')

    def test_patch_changes_the_executed_binary(self):
        state = c.start(c.lesson('1'))
        strings = json.loads(c.output(c.command('izj')))
        greeting = next(s for s in strings if s['string'] == 'Hello, World!')
        c.command('oo+')
        c.command(f'wx 4a @ {greeting["vaddr"]}')
        c.command('oo')
        self.assertEqual('Jello, World!', subprocess.check_output([state['binary']], text=True))
        c.stop()
        reopened = c.start(c.lesson('1'))
        self.assertEqual('Jello, World!', subprocess.check_output([reopened['binary']], text=True))

    def test_large_pe_analysis_is_valid_complete_json(self):
        c.start(c.lesson('14'))
        value = c.output(c.command('aflj'))
        self.assertGreater(len(value), 16768)
        functions = json.loads(value)
        self.assertGreater(len(functions), 50)
        # Native pagination must declare omitted values instead of pretending
        # a shortened list contains all the functions.
        page = c.tool('run_command', {'command': 'aflj', 'page_size': 10})
        self.assertTrue(page['pagination']['hasMore'])

    def test_switching_files_restores_calling_conventions_before_analysis(self):
        c.start(c.lesson('8'))
        for name in ('read', 'seek', 'read-lines'):
            binary = c.build(c.lesson('8'), example=name)
            c.tool('open_file', {'file_path': binary['binary']})
            result = c.tool('analyze', {'level': 2})
            self.assertIn('Analysis completed', c.output(result))
            functions = json.loads(c.output(c.command('aflj')))
            self.assertTrue(any(f['name'].split('.')[-1] == 'main' for f in functions))

    def test_all_programs_have_original_hashes_and_separate_workspaces(self):
        from companion import labs
        count = 0
        for item in c.catalog()['lessons']:
            for program in labs.specification(item)['examples']:
                packaged = c.ROOT / 'labs' / item['lab']
                original = packaged / program['source'] if program.get('kind') == 'binary' else packaged / 'original' / program['source']
                self.assertEqual(program['original_sha256'], hashlib.sha256(original.read_bytes()).hexdigest())
                count += 1
        self.assertEqual(109, count)
        one = c.build(c.lesson('3'), example='if-else')
        two = c.build(c.lesson('3'), example='switch-fruit')
        self.assertNotEqual(one['binary'], two['binary'])
        self.assertIn('positive', subprocess.check_output([one['binary']], input='4\n\n', text=True))
        self.assertIn('Apple', subprocess.check_output([two['binary']], input='1\n', text=True))

    def test_private_i386_runtime_executes_and_debugs(self):
        state = c.start(c.lesson('1'), bits=32)
        self.assertEqual('Hello, World!', subprocess.check_output([state['binary']], text=True))
        self.assertEqual(32, json.loads(c.output(c.command('ij')))['bin']['bits'])
        c.command('ood')
        address = int(c.output(c.command('?v main')).strip(), 0)
        c.command(f'db {address};dc')
        self.assertEqual(address, json.loads(c.output(c.command('drj')))['eip'])

    def test_layout_checks_type_size_instead_of_stack_spacing(self):
        state = c.start(c.lesson('6'))
        value = c.layout(c.lesson('6'))
        self.assertEqual(204, value['sizeof'])
        self.assertEqual(4, value['alignment'])
        self.assertEqual(200, value['fields']['book_id']['offset'])
        self.assertTrue(value['matches_recorded_build'])
        source = Path(state['source'])
        source.write_text(source.read_text().replace('   int   book_id;', '').replace('struct Books {', 'struct Books {\n   int book_id;'))
        changed = c.layout(c.lesson('6'))
        self.assertEqual(0, changed['fields']['book_id']['offset'])
        self.assertFalse(changed['matches_recorded_build'])

    def test_snapshot_tracks_a_target_opened_by_another_client(self):
        original = c.start(c.lesson('1'))
        other = c.build(c.lesson('6'))
        c.tool('open_file', {'file_path': other['binary']})
        evidence = c.read_json(c.snapshot())
        self.assertEqual(other['binary'], evidence['target']['file'])
        self.assertEqual(other['binary_sha256'], evidence['target']['sha256'])
        self.assertEqual(original['binary'], evidence['prepared_binary'])

    def test_notebook_and_evidence_survive_session_restart(self):
        c.start(c.lesson('1'))
        self.cli('note', 'A reader note that survives the process.')
        self.cli('progress', '--set', 'ai_completed')
        evidence = c.snapshot()
        c.stop()
        data = json.loads(self.cli('progress'))
        entry = data['lessons'][c.lesson('1')['id']]
        self.assertEqual('ai_completed', entry['status'])
        self.assertTrue(any('survives' in n['text'] for n in entry['notes']))
        self.assertTrue(evidence.is_file())
        self.assertEqual(4, len(c.read_json(evidence)['observations']))
        c.start(c.lesson('1'))
        self.assertEqual(entry, c.notebook()['lessons'][c.lesson('1')['id']] | {'updated_at': entry['updated_at']})

    def test_note_file_preserves_quotes_and_multiple_lines(self):
        c.record(c.lesson('1'), active=True)
        file = Path(self.temp.name) / 'note.md'
        text = 'Observed sizeof(T).\nReader said: "check $(literal) and `literal`".\n'
        file.write_text(text)
        self.cli('note', '--file', str(file))
        self.assertEqual(text, c.notebook()['lessons'][c.lesson('1')['id']]['notes'][0]['text'])

    def test_provider_switch_does_not_reuse_another_providers_key_file(self):
        config = c.update_settings({'provider': 'openrouter', 'key_file': '/example/openrouter.txt'})
        self.assertEqual('/example/openrouter.txt', config['key_file'])
        config = c.update_settings({'provider': 'custom', 'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'})
        self.assertIsNone(config['key_file'])
        self.assertEqual('OPENAI_API_KEY', config['key_env'])
        c.configure_hermes(None)
        profile = json.loads((c.workdir() / 'hermes/config.yaml').read_text())
        self.assertEqual('local-model', profile['model']['default'])
        self.assertEqual('http://127.0.0.1:1234/v1', profile['model']['base_url'])

    def test_hermes_resolves_the_selected_endpoint_and_credential(self):
        # Use Hermes' real resolver with a fake credential; no API request occurs.
        for provider, endpoint in [('openrouter', None), ('custom', 'http://127.0.0.1:1234/v1')]:
            with self.subTest(provider=provider), patch.dict(os.environ, {'ARTIK_TEST_KEY': 'course-test-key'}):
                config = c.update_settings({'provider': provider, 'model': 'test-model',
                                            'base_url': endpoint, 'key_env': 'ARTIK_TEST_KEY'})
                c.configure_hermes(None)
                script = '''
import json, sys
from hermes_cli.runtime_provider import resolve_runtime_provider
r = resolve_runtime_provider(requested=sys.argv[1], target_model='test-model')
print(json.dumps({'provider': r['provider'], 'base_url': r['base_url'], 'key_matches': r['api_key'] == 'course-test-key'}))
'''
                result = subprocess.check_output([str(c.RUNTIME / 'venv/bin/python'), '-c', script,
                                                  c.hermes_provider(config)], env=c.hermes_env(), text=True)
                value = json.loads(result)
                self.assertTrue(value['key_matches'])
                self.assertEqual(provider, value['provider'])
                if endpoint:
                    self.assertEqual(endpoint, value['base_url'])


if __name__ == '__main__':
    unittest.main()
