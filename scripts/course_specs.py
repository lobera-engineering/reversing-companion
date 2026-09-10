"""Reviewed mapping from article fences to exercises; indexes are zero based.

Keep adaptations explicit. Original Markdown and original extracted programs are
retained next to working variants so a compiler fix cannot silently rewrite the course.
"""

PROGRAMS = {
    '1': [(0, 'hello', 'Hello world')],
    '2': [(1, 'smart-server', 'Stack overflow authentication server')],
    '3': [(0, 'positive', 'Functions and positive branch'), (8, 'if-else', 'Positive and negative branches'),
          (11, 'switch-key', 'Character switch'), (25, 'switch-fruit', 'Integer switch'),
          (27, 'while', 'Sentinel while loop'), (36, 'for', 'Counting for loop')],
    '4': [(0, 'array-sum', 'Indexed array sum'), (6, 'scalar-sum', 'Compare independent variables'),
          (8, 'array-loop', 'Initialize and traverse an array'), (13, 'array-init', 'Array initializer'),
          (15, 'string-input', 'Read a character array'), (19, 'string-index', 'Index individual characters')],
    '4-ii': [(0, 'scanf', 'Read a string'), (4, 'gets', 'Unbounded gets'), (8, 'strlen', 'Measure string length'),
             (13, 'strncpy-unterminated', 'Observe a missing terminator'), (22, 'strncpy-terminated', 'Terminate a copied string')],
    '5': [(0, 'float-cast', 'Cast float to int'), (6, 'char-cast', 'Cast char to int'), (9, 'promotion', 'Integer promotion')],
    '6': [(0, 'matrix', 'Two dimensional array'), (5, 'students', 'Struct containing arrays'), (20, 'books', 'Books layout')],
    '7': [(0, 'student-array', 'Array of structs and program patching')],
    '8': [(0, 'write', 'Write text'), (9, 'read', 'Read two lines'), (16, 'seek', 'Seek and overwrite'),
          (20, 'read-lines', 'Read all lines')],
    '9': [(0, 'pointer-write', 'Modify through a pointer'), (15, 'stack-array', 'Sum stack array'),
          (19, 'heap-array', 'Allocate and free a dynamic array')],
    '10': [(0, 'pointer-step', 'Pointer increment and out of bounds read'), (8, 'value-step', 'Increment pointed value'),
           (11, 'pointer-argument', 'Modify caller through a pointer'), (19, 'pointer-array', 'Pointer arithmetic'),
           (26, 'heap-struct', 'Allocate and populate a structure')],
    '11': [(0, 'linked-list', 'Three linked nodes'), (14, 'random-list', 'Dynamic linked list'),
           (18, 'bitwise', 'Bitwise operations'), (25, 'enum-week', 'Enum values'), (27, 'enum-flags', 'Combine flags')],
    '12': [(0, 'union', 'Overlapping union members'), (5, 'union-array', 'Union with a character array'),
           (12, 'bitfield-size', 'Bitfield storage size'), (14, 'bitfield-overflow', 'Truncation to three bits'),
           (19, 'defines', 'Preprocessor macros')],
    '13': [(0, 'syscall-write', 'File descriptors and write'), (5, 'libc-print', 'libc and system calls'),
           (9, 'errno', 'Open error handling'), (10, 'copy', 'Read and write copy'), (16, 'sendfile', 'Kernel file copy'),
           (21, 'records-write', 'Serialize structs'), (27, 'records-seek', 'Seek to a record'),
           (30, 'records-xor', 'XOR records and sizeof pointer'), (42, 'esil-xor', 'XOR loop for ESIL')],
    '14': [(0, 'messagebox', 'MessageBox and Beep'), (6, 'write-file', 'CreateFile and WriteFile'),
           (15, 'read-write-file', 'ReadFile and WriteFile'), (22, 'copy-file', 'CopyFile'),
           (24, 'seek-file', 'Seek inside files'), (27, 'list-directory', 'FindFirstFile and FindNextFile'),
           (34, 'xor-files', 'XOR file contents')],
    '15': [(4, 'byte-order', 'Network byte order'), (9, 'inet-aton', 'Parse an IPv4 address'),
           (20, 'tcp-server', 'TCP server'), (35, 'tcp-client', 'TCP client')],
    '16': [(11, 'hello-function', 'Extract a function'), (13, 'nop-buffer', 'Data versus executable memory'),
           (20, 'copied-code', 'Relocation in copied machine code'), (23, 'write-exit', 'Position independent write and exit'),
           (26, 'http-code', 'Download code over a local HTTP connection')],
    '17': [(0, 'http-client', 'Winsock HTTP client'), (15, 'udp-client', 'UDP client'),
           (24, 'dns-query', 'DNS packet fields'), (27, 'dns-client', 'Construct DNS queries'),
           (37, 'dns-command', 'Analyze DNS command transport'), (47, 'dns-file', 'Analyze DNS file transport')],
    '18': [(0, 'bind-shell', 'Analyze bind shell process and handles'), (13, 'reverse-shell', 'Analyze reverse shell process and handles')],
    '19': [(0, 'tls-server', 'TLS command server')],
    '20': [(1, 'smart-server', 'Stack overflow authentication server')],
    '21': [(0, 'system-shell', 'system calling convention'), (3, 'dep', 'DEP and return to libc')],
    '22': [(0, 'stack-exec', 'Stack execution permissions'), (5, 'mprotect', 'Change memory permissions')],
    '23': [(0, 'canary', 'Stack protector'), (8, 'canary-leak', 'Read a stack canary'),
           (10, 'format-leak', 'Format string memory leak')],
    '24': [(2, 'pie', 'PIE load addresses'), (5, 'ret2win', 'Reuse an existing function'),
           (11, 'plt-got', 'PLT and GOT'), (19, 'call-reuse', 'Call reuse'), (25, 'gadget', 'Custom assembly gadget')],
    'malware6': [(0, 'demo-dll', 'Demonstration DLL'), (1, 'dll-injector', 'LoadLibrary injector')],
    'malware7': [(3, 'pe-injector', 'PE relocation and process injection'), (16, 'shellcode-injector', 'Process shellcode injection')],
}

WINDOWS = {'14', '17', '18', 'malware6', 'malware7'}
DEFAULTS = {'1': 'hello', '6': 'books'}

# Minimal corrections required to compile the printed examples on the tested
# toolchain. No changing algorithms, vulnerabilities, or expected observations.
REPLACEMENTS = {
    ('7', 'student-array'): [('"td struct stud { char fletter; int age; float mark;};"',
                              '/* radare2 command from the article: td struct stud { char fletter; int age; float mark;}; */',
                              'The article places a radare2 type command at C file scope; retain it as a comment.')],
    ('12', 'bitfield-overflow'): [('#include <stdio.h>\n#include <string.h>\n\nstruct {\n   unsigned int age : 3;\n} Age;\n', '',
                                   'Remove the first of two duplicate declarations of Age.')],
    ('13', 'errno'): [('    fd = open(', '    int fd = open(', 'Declare the file descriptor printed without its type.')],
    ('13', 'copy'): [('ffout = open(', 'fout = open(', 'Correct ffout/fout spelling so the opened descriptor is used.')],
    ('22', 'stack-exec'): [('“', '"', 'Replace typographic opening quotes in C.'), ('”', '"', 'Replace typographic closing quotes in C.')],
    ('23', 'format-leak'): [('printf("\\n")\n', 'printf("\\n");\n', 'Add the missing statement terminator.')],
    ('14', 'list-directory'): [('#include <string.h>', '#include <string.h>\n#define MAX_DIR_LEN MAX_PATH',
                                'Define the directory buffer limit missing from this example.')],
    ('18', 'bind-shell'): [('    port 4443 on all interfaces', '    // port 4443 on all interfaces',
                           'Turn the explanatory sentence at C statement scope into a comment.')],
}

HEADERS = {
    '3': [], '4': [], '4-ii': ['string.h'], '5': [], '6': ['time.h'],
    '7': [], '8': ['stdlib.h'], '9': [], '10': ['stdlib.h', 'string.h'],
    '11': [], '12': ['string.h'],
    '13': ['stdio.h', 'stdlib.h', 'unistd.h', 'errno.h', 'sys/stat.h', 'sys/sendfile.h'],
    '15': ['stdlib.h', 'string.h', 'strings.h', 'unistd.h', 'sys/socket.h'],
    '16': ['stdlib.h', 'unistd.h', 'strings.h'], '19': ['stdlib.h'],
    '24': ['stdlib.h'],
}
