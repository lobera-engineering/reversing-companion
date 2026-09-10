The `coursectl` launcher manages the course environment. Run it from
`ARTIK_COURSE_ROOT`, or use its absolute path.

| Task | Command |
| --- | --- |
| Browse lessons | `./coursectl list` |
| Select and inspect a chapter | `./coursectl lesson 6` |
| Read the original article | `./coursectl read 6` |
| Open its web page | `./coursectl web 6` |
| Compile a fresh lab or edited workspace source | `./coursectl build 6` |
| Start or reuse the shared session | `./coursectl start 6` |
| Inspect its state | `./coursectl status` |
| Check C type size, alignment and offsets | `./coursectl layout 6` |
| Run a raw radare2 command | `./coursectl r2 'pdf @ main'` |
| Record observations | `./coursectl snapshot` |
| Save a finding | `./coursectl note 'Finding and supporting evidence'` |
| Save a longer finding written with the file tool | `./coursectl note --file work/finding.md` |

`start` preserves an already running session for the same lab. A different lab needs
an explicit `stop` first. `build` retains edited C sources and records compiler flags
and hashes in the build directory. First builds use non-PIE x86-64 at O0 with symbols;
the reader can request `--bits 32` (requires multilib) or `--optimization O2`.

The launcher disables `bin.cache`, `io.cache` and `io.pcache` for live debugging and
verifiable writes. The upstream MCP `open_file` tool enables `bin.cache` again when
opening another file; restore those settings before debugging or patching it.
It also sets `scr.limit=16777216`: upstream defaults to 16768 characters, which can truncate
JSON from larger binaries into invalid data. Prefer focused queries for the model;
never interpret truncated JSON as complete evidence.

For the Books lab, compare inferred type sizes against `layout`. The gap between two
separate stack locals can exceed `sizeof(struct)`; it does not establish the struct's
alignment. The probe reports whether the current source and binary still match the
recorded build. If they differ, account for the edits before using the source as evidence.
Separate the measured stack spacing from hypotheses about why the compiler chose it.

Use the `radare2` MCP tools for the existing session. Both MCP and the human command
console operate on the same server. Inspect current state before reopening a file,
restarting the debugger, or continuing after manual intervention. Tool output comes
from the actual session. For dynamic work, use radare2's debugger commands through
`run_command`; enter debugging with `ood`, set a breakpoint and continue to it.
Check `oo?`, `db?` and `dc?` when needed. Debugger processes persist only
while their session is alive; learner notes persist across restarts.

Create patches and experiments in the working lab. Show the before/after evidence
and verify the changed behavior. Reopen a patched file read-only (`oo`) before executing
it externally; Linux rejects execution while a writable descriptor is open (ETXTBSY).
C/Python and terminal tools can supplement radare2.
Save a brief finding with its supporting command, and leave a concrete next step.
`snapshot` records the actual current target and debugger state. Add an observation
with `--command 'pxj 32 @ address'` when specific memory contents support the finding.

This first release has a text command console. Native radare2 visual/TUI commands
require a real terminal and are not rendered through MCP. The full native `r2` binary
is available in the runtime for separate terminal sessions.
