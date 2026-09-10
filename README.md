<p align="center">
  <img src="assets/logo.png" alt="RadarAI" width="400">
</p>

<h1 align="center">Reversing Companion</h1>

<p align="center">
  A terminal companion for studying a reversing course with an AI agent and radare2.<br>
  The student and the agent share the <b>same radare2 session</b> — both can inspect, debug, patch, and annotate the same binary at the same time.
</p>

> **This is a learning tool, not an enterprise product.**  It was built to make the course interactive and approachable.  Expect rough edges, opinionated defaults, and room for improvement.  If you find it useful, break something, or have ideas — contributions and issues are welcome.

## What's inside

- **33 original articles** from the course, with provenance hashes.
- **109 lab programs**: 99 C/C++ examples and the 10 IOLI crackmes, with build recipes, test cases, and verification evidence.
- **7 malware analysis labs** (Agent Tesla, Emotet, SmokeLoader, Ramnit, IcedID, DLL injection, PE injection) with pinned samples and static extraction recipes — no malware is executed.
- A shared radare2-mcp session that both you and the AI can drive.
- A notebook that tracks your progress, notes, and evidence snapshots across sessions.

The AI integration uses [Hermes](https://github.com/NousResearch/hermes-agent) with a course-specific skill and [radare2-mcp](https://github.com/radareorg/radare2-mcp) as the bridge to radare2. The provider, model, and credential source are configurable — it has been tested with OpenRouter and `anthropic/claude-sonnet-4.6`.

## Quick start

Linux x86-64, Python 3.11+, plus `git`, `gcc`, `make`, `pkg-config`, and `dpkg-deb`:

```bash
./coursectl bootstrap
./coursectl configure --provider openrouter \
  --model anthropic/claude-sonnet-4.6 \
  --key-file ~/path/to/openrouter-key.txt
./coursectl doctor
./coursectl chat 6
```

`bootstrap` installs Hermes, radare2, and radare2-mcp locally inside `.runtime/` — no system packages are modified and no root is needed. Pinned versions are in [dependencies.lock.json](dependencies.lock.json) and [requirements.lock](requirements.lock).

The key file should contain a single API key. You can also export `OPENROUTER_API_KEY` and use `./coursectl configure --clear-key-file`.

## Usage

### Studying with the agent

Start a lesson and let the agent guide you:

```bash
./coursectl chat 6
```

In the conversation you might say:

> Build the Books example from chapter 6. Analyze its struct fields, set a breakpoint, read the values from memory, and contrast the struct size with what C reports. Save the evidence and show me how to repeat it.

Or ask for hints, step-by-step explanations, or a complete walkthrough — the agent adapts.

### Shared radare2 console

In another terminal, while the agent is working:

```bash
./coursectl console
```

Type `pdf @ main`, `dr`, `px 64 @ rsp`, or any radare2 command. The agent sees your changes, and you see its. `:quit` exits the console but keeps the session alive.

### Common commands

| Command | What it does |
| --- | --- |
| `./coursectl list` | List all 33 lessons and their status |
| `./coursectl lesson 6` | Select a lesson and show its references |
| `./coursectl read 6` | Print the original Markdown article |
| `./coursectl web 6` | Open the article in your browser |
| `./coursectl build 6` | Compile the working copy (preserves your edits) |
| `./coursectl start 6` | Start or reuse the shared r2 session |
| `./coursectl examples 3` | List available programs for a lesson |
| `./coursectl r2 'pdf @ main'` | Run a command in the shared session |
| `./coursectl status` | Show active lesson, binary, and current address |
| `./coursectl snapshot` | Capture evidence from the current state |
| `./coursectl note 'my finding'` | Save a note to the notebook |
| `./coursectl stop` | Stop the r2 server and debugger |
| `./coursectl assets malware5` | Inspect pinned malware sample info |
| `./coursectl assets malware5 --fetch --analyze` | Fetch sample and run static extraction |
| `./coursectl open malware2 /path/to/sample` | Open an external file in the shared session |

### Malware labs

Malware samples are shipped in `course/samples.zip` (password: `infected`). They are **never executed** — the companion performs static analysis only, using a local radare2-mcp session on the Linux host.

For IcedID (malware5), the companion extracts the RC4-encrypted C2 configuration from the unpacked PE. For Emotet (malware2), it extracts VBA macros and decodes the base64 PowerShell payload. Both recipes validate their output against known article evidence.

### Changing the model

```bash
# Different OpenRouter model
./coursectl configure --model anthropic/claude-sonnet-4

# Anthropic API directly
./coursectl configure --provider anthropic --model claude-sonnet-4 \
  --key-file ~/path/to/anthropic-key.txt

# Local server (e.g. ollama, llama.cpp)
./coursectl configure --provider custom \
  --model local-model-name \
  --base-url http://127.0.0.1:1234/v1
```

## Project structure

```
companion/          Python package — session management, CLI, labs, assets, verification
course/             33 original articles + catalog + sample archive
labs/               Lab manifests, C sources, patches, IOLI crackmes
scripts/            Bootstrap, import, verification helpers
skills/             Hermes skill for the course
tests/              Integration tests (real GCC + r2, no API calls)
patches/            Patches applied to radare2-mcp during bootstrap
.runtime/           (gitignored) Installed tools — radare2, r2mcp, Hermes, venv
work/               (gitignored) Your notebook, builds, evidence, Hermes profile
```

## Testing

Unit and integration tests use real GCC, radare2, and MCP — no LLM calls:

```bash
python3 -m pytest tests/ -v
```

Full verification of all 109 lab programs (builds, execution, debugging):

```bash
./coursectl verify all
```

Agent integration check using the configured model (costs API credits):

```bash
./coursectl verify-agent all
```

See [VALIDATION.md](VALIDATION.md) for detailed results.

## Adapting to your setup

### What works out of the box

`./coursectl bootstrap` sets up everything needed for the **Linux labs** (chapters 1–13, 15–16, 19–24) and **static malware analysis** (malware 1–5). No VM, no extra configuration — just the prerequisites listed in [Quick start](#quick-start).

### Windows VM (optional — chapters 14, 17–18, malware 6–7)

The Windows labs use VirtualBox **guestcontrol** to copy binaries, run r2mcp, and execute programs inside a guest VM. This is entirely optional — you only need it if you want to do dynamic Windows analysis (debugging PE files, running the DLL/PE injection examples).

**What you need:**

1. [VirtualBox](https://www.virtualbox.org/) with a Windows 10/11 guest and Guest Additions installed (guestcontrol requires them).
2. A user account on the guest that the host can reach via `VBoxManage guestcontrol`.
3. radare2 for Windows extracted somewhere on the guest (download from [radare2 releases](https://github.com/radareorg/radare2/releases)).

**What to change in the code:**

Edit the constants at the top of [`companion/windows.py`](companion/windows.py) to match your VM:

```python
VM_NAME = 'W11'              # VBoxManage VM name (VBoxManage list vms)
VM_USER = 'lab'              # Guest OS username
VM_PASSWORD = 'lab'          # Guest OS password
VM_R2_DIR = 'C:\\lab\\r2\\bin'  # Where you extracted radare2 on the guest
VM_LAB_DIR = 'C:\\lab'        # Working directory on the guest
```

These are plain constants, not secrets — they control a local lab VM. Change them to match whatever you named your VM and user.

**Known issues with Windows VMs:**

- **Windows Defender** quarantines known malware samples within seconds of file creation. You cannot add exclusions via guestcontrol because it requires UAC elevation. Workaround: disable Defender before deploying samples, or use the Linux-side static analysis (`./coursectl open`) which avoids the VM entirely.
- **WoW64 debugging**: radare2's debugger cannot handle the 64→32-bit transition on Win11 for 32-bit PEs. 64-bit PEs work fine.
- **guestcontrol sessions**: The companion is careful to use minimal guestcontrol sessions. Never kill VBoxManage processes from the host side (`pkill`, `kill`) — that can abort the VM. The code uses `taskkill` inside the guest instead.

### Using a different agent framework

The companion is built around [Hermes](https://github.com/NousResearch/hermes-agent), but the architecture separates concerns:

- **`companion/core.py`** manages the r2mcp session and MCP RPC calls. It does not depend on Hermes.
- **`companion/cli.py`** wires `coursectl chat` to Hermes specifically — this is the part you'd replace.
- **`.hermes.md`** is the system prompt. The `skills/` directory holds the course-specific Hermes skill.
- **`work/hermes/config.yaml`** is the Hermes profile, auto-configured by `coursectl configure`.

To adapt for another MCP-capable agent (Claude Code, Cursor, a custom agent, etc.), point it at the running r2mcp server. After `./coursectl start <lesson>`, the session details are in `work/session.json`:

```json
{
  "url": "http://127.0.0.1:<port>/",
  "token": "<bearer-token>",
  "lesson": "reversing-radare-6",
  "binary": "/path/to/binary"
}
```

Connect your agent's MCP client to that URL with the bearer token, and it has full access to the shared radare2 session.

### Using a different model provider

`coursectl configure` supports three provider modes:

| Provider | Key variable | Notes |
| --- | --- | --- |
| `openrouter` (default) | `OPENROUTER_API_KEY` | Any model on OpenRouter |
| `anthropic` | `ANTHROPIC_API_KEY` | Anthropic API directly |
| `custom` | `OPENAI_API_KEY` | Any OpenAI-compatible server (requires `--base-url`) |

You can also use `--key-env VAR_NAME` to read the key from a different environment variable, or `--key-file /path/to/key.txt` to read it from a file.

## Scope and limitations

- The shared console is text-based. Interactive radare2 views (`V`, `VV`) need a separate terminal and are not shared through the MCP bridge.
- Windows dynamic analysis requires a VirtualBox VM — see [Adapting to your setup](#adapting-to-your-setup).
- Malware samples are analyzed statically on the Linux host. Dynamic malware analysis requires either bare metal or a VM with Defender disabled.
- Addresses and disassembly will differ from the blog articles depending on your compiler version and flags. The agent works with what it actually observes, not what the article shows.
- The editorial error in chapter 2 (index says "conditionals" but content is buffer overflows) is preserved and documented in the catalog.

## Contributing

This is a companion built for learning. If you find a bug, have an idea for a better lab recipe, want to add support for another agent framework, or want to extend the malware analysis coverage — open an issue or send a PR. There's no formal process; just explain what you changed and why.

The AI bridge uses [radare2-mcp](https://github.com/radareorg/radare2-mcp) and [Hermes](https://github.com/NousResearch/hermes-agent).

## License

The lab programs and companion code are provided as-is for learning purposes.

<sub>Course articles taken from the [original reversing course](https://artik.blue/reversing) by Pau Muñoz (artikblue, [lobera.ai](https://lobera.ai) founder) — edited, expanded, and adapted for use with the companion.</sub>
