"""Behavioral fixtures for printed examples, independent of their implementation."""
import base64
import struct


def case(stdin='', contains=(), *, args=(), files=None, signal=None, env=None):
    value = {'stdin': stdin, 'contains': list(contains), 'args': list(args)}
    if files:
        value['files'] = files
    if signal:
        value['signal'] = signal
    if env:
        value['env'] = env
    return value


CASES = {
    ('1', 'hello'): [case(contains=['Hello, World!'])],
    ('3', 'positive'): [case('4\n\n', ['positive']), case('0\n\n', ['Enter a number'])],
    ('3', 'if-else'): [case('4\n\n', ['positive']), case('-2\n\n', ['negative'])],
    ('3', 'switch-key'): [case(' \n', ['Space']), case('7\n', ['Digit']), case('x\n', ['Neither'])],
    ('3', 'switch-fruit'): [case(f'{i}\n', [text]) for i, text in [(1, 'Apple.'), (2, 'Orange.'), (3, 'Banana.'), (4, 'Pear.'), (9, 'Nothing selected.')]],
    ('3', 'while'): [case('3\n-2\n0\n', ['Positive num', 'Negative num'])],
    ('3', 'for'): [case('\n', ['1 2 3 4 5 6 7 8 9 10'])],
    ('4', 'array-sum'): [case('\n', ['SUM IS 700'])],
    ('4', 'scalar-sum'): [case('\n', ['SUM is 700'])],
    ('4', 'array-loop'): [case('\n', ['val 0', 'val 50', 'val 99'])],
    ('4', 'array-init'): [case('\n', ['SUM is 700'])],
    ('4', 'string-input'): [case('Artik\n\n', ['Hi, Artik'])],
    ('4', 'string-index'): [case('Artik\n\n', ['First letter: A', 'Second letter: r'])],
    ('4-ii', 'scanf'): [case('Artik\n\n\n', ['Hi, Artik'])],
    ('4-ii', 'gets'): [case('Artik Blue\n\n', ['Ho, Artik Blue'])],
    ('4-ii', 'strlen'): [case('Artik Blue\n\n', ['Length: 10 chars'])],
    # The unterminated example has undefined behavior for longer input. This
    # bounded case exercises padding; a separate sanitizer check covers the bug.
    ('4-ii', 'strncpy-unterminated'): [case('Pau\n\n', ['Copied string =  Pau', '4 first chars = Pau'])],
    ('4-ii', 'strncpy-terminated'): [case('Artik Blue\n\n', ['Copied string = Artik Blue', '4 FIRST LETTERS Arti'])],
    ('5', 'float-cast'): [case('\n', ['5\n'])],
    ('5', 'char-cast'): [case('\n', ['97'])],
    ('5', 'promotion'): [case('\n', ['97\n97'])],
    ('6', 'matrix'): [case('\n', ['first group 3', 'second group 13'])],
    ('6', 'students'): [case()],
    ('6', 'books'): [case(contains=['C Programming', 'Telecom Billing', '6495407', '6495700'])],
    ('7', 'student-array'): [case('a\nA\n21\n7.5\nq\n\n', ['Round: 0', 'First letter?', 'Age?', 'Mark?'])],
    ('8', 'write'): [case('\n', files={'test.txt': 'This is a line\nAnother line that follows the second line\n'})],
    ('8', 'read'): [case('\n', ['This is a line', 'Another line that follows the second line'])],
    ('8', 'seek'): [case(files={'fseek.txt': 'This is C Programming Languageee to visit artik.blue to get fresh reversing stuff'})],
    ('8', 'read-lines'): [case(contains=['0: First line', '1: Second line'])],
    ('9', 'pointer-write'): [case(contains=['Value of i: 2', 'Value of c: c', 'Value of c: b'])],
    ('9', 'stack-array'): [case('3\n10\n20\n30\n', ['SUM: 60'])],
    ('9', 'heap-array'): [case('3\n10\n20\n30\n', ['SUM: 60'])],
    ('10', 'value-step'): [case('\n', ['3\n4'])],
    ('10', 'pointer-argument'): [case('\n', ['value= 5', 'updated_value= 10'])],
    ('10', 'pointer-array'): [case('\n', ['20 40'])],
    ('10', 'heap-struct'): [case('\n', ['Peter, p@p.p, and the age is: 21'])],
    ('11', 'linked-list'): [case(contains=['1 2 3'])],
    ('11', 'random-list'): [case()],
    ('11', 'bitwise'): [case('\n', ['Complement of a = -68', 'a AND b = 1', 'a OR b =  99', 'a XOR b = 98', 'A left shifted 1 = 134', 'A right shifted 1 = 33'])],
    ('11', 'enum-week'): [case(contains=['Day 4'])],
    ('11', 'enum-flags'): [case(contains=['5'])],
    ('12', 'union'): [case('\n\n', ["Size of 'sample' union = 4", '50'])],
    ('12', 'union-array'): [case('\n\n', ["Size of 'sample' union = 20", 'value= 50', 'value= hello world', 'value= A'])],
    ('12', 'bitfield-size'): [case(contains=['status1 : 8', 'status2 : 4'])],
    ('12', 'bitfield-overflow'): [case(contains=['Age.age : 4', 'Age.age : 7', 'Age.age : 0'])],
    ('12', 'defines'): [case('4\n8\n\n', ['SUM = 12', '> MAX']), case('2\n3\n\n', ['SUM = 5'])],
    ('13', 'syscall-write'): [case(contains=['hello world', 'hello world2'], files={'foo': 'hello_world'})],
    ('13', 'libc-print'): [case(contains=['ssssssssyscall'])],
    ('13', 'errno'): [case(files={'foo': 'hello_world'})],
    ('13', 'copy'): [case(files={'bar': 'Course copy fixture\n'})],
    ('13', 'sendfile'): [case(args=['foo', 'bar'], files={'bar': 'Course copy fixture\n'})],
    ('13', 'records-write'): [case()],
    ('13', 'records-seek'): [case(contains=['second person val = 1, artik, blue'])],
    ('13', 'records-xor'): [case()],
    ('15', 'byte-order'): [case(contains=['little-endian'])],
    ('15', 'inet-aton'): [case()],
    ('16', 'hello-function'): [case(contains=['hello world'])],
    ('16', 'nop-buffer'): [case(signal=11)],
    ('16', 'copied-code'): [case(signal=11)],
    ('16', 'write-exit'): [case(contains=['Hello!'])],
    ('21', 'system-shell'): [case('printf COURSE_SHELL_OK\nexit\n', ['COURSE_SHELL_OK'])],
    ('21', 'dep'): [case('Artik\n', ['hi there Artik !!'])],
    ('22', 'stack-exec'): [case('Artik\n', ['Hi there Artik !!'])],
    ('22', 'mprotect'): [case('Artik\n', ['Pagesize:', 'Hi there Artik !!'])],
    ('23', 'canary'): [case('Artik\n', ['Hi there Artik !!'])],
    ('23', 'canary-leak'): [case(contains=['Canary value:'])],
    ('23', 'format-leak'): [case('Artik\n', ['COURSE_LEAK', 'Hi there Artik !!'], args=['COURSE_LEAK'])],
    ('24', 'pie'): [case(contains=['Hello World!'])],
    ('24', 'ret2win'): [case('Artik\n', ['Hi there Artik !!'])],
    ('24', 'plt-got'): [case('Artik\n', ['Artik !it is you again'])],
    ('24', 'call-reuse'): [case('Artik\n', ['hi Artik !'])],
    ('24', 'gadget'): [case('Artik\n', ['hi Artik !'])],
}

FIXTURES = {
    ('8', 'read'): {'test.txt': 'This is a line\nAnother line that follows the second line\n'},
    ('8', 'read-lines'): {'myinputfile.txt': 'First line\nSecond line\n'},
    ('13', 'copy'): {'foo': 'Course copy fixture\n'},
    ('13', 'sendfile'): {'foo': 'Course copy fixture\n'},
}
RECORDS = struct.pack('<i20s20s', 2, b'john', b'doe') + struct.pack('<i20s20s', 1, b'artik', b'blue')
for name in ('records-seek', 'records-xor'):
    FIXTURES[('13', name)] = {'person.dat': {'base64': base64.b64encode(RECORDS).decode()}}

SANITIZERS = {
    ('4-ii', 'strncpy-unterminated'): {'stdin': 'ArtikBlue\n\n', 'contains': 'stack-buffer-overflow'},
    ('10', 'pointer-step'): {'stdin': '\n', 'contains': 'heap-buffer-overflow'},
    ('13', 'esil-xor'): {'stdin': '', 'contains': 'stack-buffer-overflow'},
}

for index, password in enumerate(['250382', '5274', '338724', '338724', '69', *['970'] * 5]):
    environment = {'LOLO': '1'} if index >= 6 else {}
    wrong = 'Invalid Password!' if index <= 3 else 'Password Incorrect!'
    CASES[('8-i', f'crackme0x{index:02x}')] = [
        case('0\n', [wrong], env=environment),
        case(password + '\n', ['Password OK'], env=environment),
    ]
