# Hands-Free Enter

<p align="right">
  <a href="README.md">简体中文</a> · <strong>English</strong>
</p>

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Tests](https://github.com/XiangQhello/codex-claude-auto-enter/actions/workflows/tests.yml/badge.svg)](https://github.com/XiangQhello/codex-claude-auto-enter/actions/workflows/tests.yml)

A multi-task auto-Enter controller for terminal AI agents such as Codex and Claude Code. It targets an exact window or Herdr pane and stops automatically when Herdr reports that the current turn is complete.

## The problem

Fixed counts and durations do not match unpredictable AI task times:

- stop too early and the agent may still need confirmation;
- stop too late and Enter can submit your half-written next command;
- active-window automation can send input to the wrong terminal.

Hands-Free Enter pins every task to a stable target. With Herdr, it reads `working`, `blocked`, and `idle`, then stops immediately when the turn becomes `idle`.

## Demo

![Select a Herdr Codex pane and stop automatically on idle](assets/demo.gif)

[Download the full MP4](https://github.com/XiangQhello/codex-claude-auto-enter/releases/download/v1.5.0/demo.mp4) · [Rebuild the demo](scripts/demo/record_demo.py)

> GitHub does not reliably play repository MP4 files inline, so the homepage uses a lightweight GIF preview. The original MP4 remains available in the Release.

## Quick start

On Linux, install [Herdr](https://herdr.dev/docs/install/) first for precise targeting and completion detection:

```bash
curl -fsSL https://herdr.dev/install.sh | sh
herdr
```

Then launch Hands-Free Enter:

```bash
git clone https://github.com/XiangQhello/codex-claude-auto-enter.git
cd codex-claude-auto-enter
chmod +x start.sh
./start.sh
```

The launcher reuses a compatible Python/Conda environment or creates a local `.venv`. Override it with `HANDSFREE_PYTHON=/path/to/python ./start.sh`.

Double-click `start.command` on macOS or `start.bat` on Windows.

## Workflow

1. Start Codex or Claude Code in Herdr.
2. Select the exact Herdr AI Agent / Pane.
3. Choose repeating mode and an Enter interval.
4. Select automatic stop when the AI task completes.
5. Add and start the task.

Herdr is recommended, not required. Regular terminal mode still supports manual, count, and duration limits, but cannot inspect agent completion state.

## Highlights

- Directed Herdr pane input without foreground focus
- Automatic stop on `idle`; fail-closed behavior on status errors
- GUI-configurable polling interval from 0.5 to 10 seconds
- Multiple independent terminal or pane tasks
- Stable target locking instead of active-window input
- Linux, macOS, and Windows launch scripts

| Platform | Herdr input | Regular terminal background input |
|---|---|---|
| Linux + Herdr | Supported, including Wayland | X11 only |
| Linux X11/Xorg | Optional | Supported |
| Linux Wayland | Supported | Not supported |
| Windows | Not integrated yet | Experimental |
| macOS | Not integrated yet | Experimental |

## Documentation

- [Contributing](docs/CONTRIBUTING.md)
- [Security policy](docs/SECURITY.md)
- [Changelog](docs/CHANGELOG.md)
- [Third-party notices](docs/THIRD_PARTY_NOTICES.md)
- [中文说明](README.md)

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Herdr and license

[Herdr](https://herdr.dev/) is an independent Apache-2.0 project. This application only calls its public CLI/API and does not bundle or modify Herdr source. Hands-Free Enter is licensed under [GPL-3.0-only](LICENSE) for compatibility with PyQt5 GPL v3.

Auto-Enter confirms whatever the target terminal currently displays. Never use it to approve destructive or otherwise sensitive actions that require human judgment.
