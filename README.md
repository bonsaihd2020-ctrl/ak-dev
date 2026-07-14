# Devin Clone

> A polished, pro-level **desktop AI coding agent** inspired by Devin & OpenCode — packaged as a **single .exe**.

## Features

### Core
- **Multi-agent workflow** (Plan → Architecture → Code → Review → Test) — all agents' activity visible in chat
- **Hybrid execution**: local file editing on host + on-demand Docker sandbox for running/testing
- **Live Ubuntu desktop** (XFCE + noVNC) — watch the agent work, PAUSE/STOP, and TAKE OVER
- **In-UI provider management**: OpenAI, Anthropic, DeepSeek, Groq, OpenRouter, Together, Ollama
- **Free model filter** — toggle to show only FREE models with tool-calling support indicator
- **Browser-login auth** (experimental) for OpenAI/DeepSeek + API-key auth as primary
- **Web search**: Tavily and Brave Search integration
- **Local file/folder connect** (Codex-style) — agent reads, edits, and fixes files in-place
- **Export** — download your entire workspace as a ZIP

### Git Integration
- **Git tools** built into the agent — `git init`, `status`, `diff`, `log`, `commit`, `branch`, `push`
- **Git Panel** in sidebar — view changes, commit inline, recent commit history
- Agent auto-commits after each phase

### Session Management
- **Save/Resume sessions** — continue tasks later from where you left off
- Session history with task, provider, model, files tracked
- Restore any session with one click

### Code Diff Viewer
- **Side-by-side diff** view (like GitHub) with color-coded additions/deletions
- Unified diff format with stats (+additions, -deletions)

### Voice Input
- **Microphone button** in chat — speak your task instead of typing
- Browser-based speech recognition (15s max)

### Progress Dashboard
- **Real-time stats**: Time, Tokens, Tool Calls, Cost
- Phase-by-phase breakdown (Plan/Arch/Code/Review/Test timing)
- All-time totals across all tasks
- Task history log

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Send task |
| `Ctrl+P` | Pause agent |
| `Ctrl+.` | Stop agent |
| `Ctrl+E` | Export workspace |
| `Ctrl+,` | Open Settings |
| `Ctrl+D` | Open Dashboard |

### Multi-Language Support
- English, Hindi, Urdu UI translations
- Language switcher in Settings

### Plugin System
- **Custom tools** — write Python plugins that add new agent tools
- **Plugin templates** — auto-generate plugin boilerplate
- **MCP Server support** — connect external MCP servers for additional tools

### Project Templates
- **Pre-built templates**: React App, FastAPI, Express.js, Chrome Extension, ML Project, Docker Compose
- One-click project scaffolding from the UI

### Docker Compose Support
- **Generate, manage, and monitor** multi-container setups
- `docker-compose up/down/stop/restart/logs/ps` from the UI
- Auto-generate compose files from service definitions

### Auto-Update
- **Check for updates** from GitHub releases
- Notification when new version available

### Terminal
- **Live terminal** (xterm.js) — full shell access in the UI
- WebSocket-connected to backend

---

## Prerequisites

- **Docker Desktop** or **WSL2** with Docker (for the sandbox)
- **Python 3.10+** (for dev mode or building the .exe)
- **Node.js 18+** and **npm** (for dev mode or building the .exe)

> The final .exe does NOT require Python or Node — only Docker/WSL2.

---

## Quick Start (Dev Mode)

### 1. Install Dependencies

```bash
cd devin-clone
npm run install:all
```

### 2. Build the Sandbox Docker Image

```bash
npm run sandbox:build
```

### 3. Run in Dev Mode

```bash
npm run dev
```

This starts:
- Backend: `http://127.0.0.1:18900` (FastAPI + WebSocket)
- Desktop UI: `http://localhost:5173` (Vite + React)

---

## Building the Single .exe

### Step 1: Build the Python Backend

```bash
cd devin-clone
npm run build:backend
```

This creates `dist/backend.exe` using PyInstaller.

### Step 2: Build the Electron App

```bash
npm run build:desktop
```

This creates a Windows installer/portable .exe with `backend.exe` bundled inside.

### Or Build Everything at Once

```bash
npm run build:all
```

The final .exe is in `desktop/dist/` or `desktop/release/`.

---

## In-UI Setup Guide

### Provider Setup

1. Open **Settings** from the sidebar (or press `Ctrl+,`)
2. Select a provider (OpenAI, DeepSeek, Groq, etc.)
3. Paste your API key → Click **Save** → Click **Test**
4. Select a model from the dropdown
5. Toggle **"Show free models only"** to filter free options

### Browser Login (Experimental)

For OpenAI/DeepSeek, you can also use browser login:
1. In Settings → select the provider
2. Click **"Login with Browser"**
3. Complete the login in the browser (Playwright opens a headed browser)
4. The session token is captured automatically

> ⚠️ Browser login is unofficial and may break when providers change their sites. API-key auth is always the reliable default.

### Web Search Keys

1. In Settings → Web Search Keys section
2. Enter your Tavily or Brave API key → Save → Test
3. Select which backend to use as the active search provider

### Connecting a Workspace

1. Click **Workspace** in the sidebar
2. Click **Connect** → select a folder
3. The agent reads and edits files in this folder locally

### Using Git

1. Click **Git** tab in the right panel
2. Click **Init** if not a git repo, or view existing status
3. Type commit message → press Enter or click Commit
4. Agent auto-commits after each workflow phase

### Templates

1. Agent can use templates when creating new projects
2. Available: React App, FastAPI, Express.js, Chrome Extension, ML Project, Docker Compose

### Plugins

1. Create a plugin template from Settings → Plugins
2. Edit the generated `.py` file in `~/.devin-clone/plugins/`
3. Load/unload plugins from the UI
4. Custom tools appear in the agent's tool list

---

## Sandbox (Live Desktop)

The Ubuntu sandbox with XFCE desktop + VNC is started **on demand** when the agent needs to:
- Run/test code
- Install packages
- Use a browser (e.g., check browser extensions)

### Build the Image

```bash
docker build -t devin-sandbox:latest ./sandbox
```

### Auto-Start

The app starts the sandbox automatically when needed. You can also start it manually from the **Desktop** tab.

### User Takeover

1. PAUSE the agent (click ⏸ or press `Ctrl+P`)
2. The VNC stream is shared-control — you can click/type in the live desktop
3. RESUME when done (click ▶)

---

## Architecture

```
devin-clone/
├── backend/                  # Python FastAPI agent server
│   ├── providers.py          # LLM provider adapters (OpenAI, Anthropic, Ollama)
│   ├── models_catalog.py     # Model listing with free/paid + tool-calling flags
│   ├── keystore.py           # Encrypted key storage (Fernet)
│   ├── agent_loop.py         # Agent reasoning loop with error recovery
│   ├── agents/               # Multi-agent orchestration
│   │   ├── planner.py
│   │   ├── architect.py
│   │   ├── coder.py
│   │   ├── reviewer.py
│   │   ├── tester.py
│   │   └── orchestrator.py
│   ├── workspace.py          # Local workspace management (Codex-style)
│   ├── tools.py              # Tool definitions + dispatch (local + sandbox)
│   ├── git_tools.py          # Git integration tools
│   ├── sandbox_manager.py    # Docker sandbox lifecycle
│   ├── browser_auth.py       # Browser/OAuth login (Playwright)
│   ├── memory.py             # Conversation history + context trimming
│   ├── memory_search.py      # Semantic search over past conversations
│   ├── session_manager.py    # Session save/resume
│   ├── stats_tracker.py      # Progress dashboard + cost tracking
│   ├── diff_engine.py        # Code diff computation
│   ├── template_manager.py   # Project templates
│   ├── plugin_manager.py     # Plugin system + MCP server support
│   ├── docker_compose.py     # Docker Compose management
│   ├── auto_update.py        # GitHub release update checker
│   ├── api_check.py          # Key/model testing
│   ├── server.py             # FastAPI + WebSocket server
│   └── requirements.txt
├── desktop/                  # Electron + React UI
│   ├── electron/             # Electron main process
│   ├── src/                  # React app (TypeScript + Chakra UI)
│   │   ├── App.tsx           # Main app with all panels
│   │   ├── api.ts            # API client
│   │   ├── i18n.json         # Translations (EN/HI/UR)
│   │   └── hooks/useI18n.ts  # Translation hook
│   └── package.json
├── sandbox/                  # Docker Ubuntu sandbox
│   ├── Dockerfile            # Ubuntu + XFCE + VNC + noVNC + Chromium
│   └── start.sh
├── package.json              # Root scripts (build:all, dev, etc.)
└── README.md
```

---

## Key Configuration

| Setting | Location | Notes |
|---------|----------|-------|
| API keys | Settings UI → Provider | Encrypted via Fernet in OS user data dir |
| Model selection | Settings UI → Provider dropdown | Filter by free/paid |
| Tavily/Brave keys | Settings UI → Web Search | Each with Test button |
| Active search backend | Settings UI → Web Search | Tavily or Brave |
| Workspace path | Workspace panel → Connect | Local folder on your PC |
| Sandbox auto-start | Automatic | Only when run/test tools are needed |
| Language | Settings UI | English, Hindi, Urdu |
| Plugins | `~/.devin-clone/plugins/` | Python files with TOOL_INFO |
| Templates | Settings → Templates | Pre-built or custom |

---

## Troubleshooting

### "Docker is not available"
- Start Docker Desktop or ensure WSL2 + Docker is running

### "No models available"
- Check that your API key is saved and valid (use the Test button)
- Free models may have rate limits — try switching providers

### Sandbox won't start
- Run `docker build -t devin-sandbox:latest ./sandbox` first
- Ensure Docker has permission to create containers

### Browser login broken
- This is expected — browser login is experimental
- Use API key authentication instead (always reliable)

### Plugin not loading
- Check the plugin Python file syntax
- View plugin errors in the Plugins panel

---

## License

MIT
