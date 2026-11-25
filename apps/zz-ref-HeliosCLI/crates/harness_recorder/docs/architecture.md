# KLA (Kommand Line Automation) Architecture

## Overview
KLA is a Rust-based CLI automation and recording tool that creates beautiful screenshots, videos, and GIFs of terminal interactions.

## Core Components

### 1. Script Engine (`kla-script`)
- **Format**: YAML-based scripting language (inspired by VHS)
- **Features**: 
  - Command execution with timing control
  - Input simulation (typing, key presses)
  - Wait conditions (time, output patterns)
  - Screenshot/recording triggers

### 2. Terminal Control (`kla-pty`)
- **Backend**: `pseudoterminal` crate for cross-platform PTY
- **Features**:
  - Spawn and control terminal processes
  - Capture stdout/stderr in real-time
  - Send input programmatically
  - Handle terminal escape sequences

### 3. Capture Engine (`kla-capture`)
- **Screenshot**: `scap` library for high-performance capture
- **Video/GIF**: Inspired by `t-rec-rs` approach
- **Features**:
  - Frame-by-frame terminal capture
  - Configurable frame rates
  - Optimization (idle frame detection)
  - Multiple output formats (PNG, GIF, MP4)

### 4. CLI Interface (`kla-cli`)
- **Commands**:
  - `kla record <script>` - Execute script and record
  - `kla screenshot <command>` - Single command screenshot
  - `kla demo <script>` - Interactive demo mode
  - `kla convert <input> <output>` - Format conversion

## Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   KLA Script    │───▶│  Terminal PTY   │───▶│  Capture Engine │
│   (.kla.yaml)   │    │   Controller    │    │   (PNG/GIF/MP4) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Timing &      │    │   Process       │    │   Media         │
│   Coordination  │    │   Management    │    │   Generation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Script Format Example

```yaml
name: "Git Workflow Demo"
settings:
  width: 120
  height: 30
  shell: "zsh"
  theme: "dracula"

steps:
  - type: command
    text: "git init demo-repo"
    wait: 1s
    
  - type: command  
    text: "cd demo-repo"
    
  - type: type
    text: "echo 'Hello World' > README.md"
    speed: 50ms
    
  - type: screenshot
    name: "readme-created"
    
  - type: command
    text: "git add ."
    
  - type: command
    text: "git commit -m 'Initial commit'"
    wait_for: "create mode"
    
  - type: record_gif
    duration: 5s
    name: "git-workflow"
```

## Dependencies

```toml
[dependencies]
pseudoterminal = "0.1"
scap = "0.1" 
tokio = { version = "1.0", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_yaml = "0.9"
clap = { version = "4.0", features = ["derive"] }
anyhow = "1.0"
image = "0.24"
```

## Module Structure

```
src/
├── main.rs              # CLI entry point
├── lib.rs               # Library exports
├── script/              # Script parsing and execution
│   ├── mod.rs
│   ├── parser.rs        # YAML script parsing
│   ├── executor.rs      # Script execution engine
│   └── types.rs         # Script type definitions
├── pty/                 # Terminal control
│   ├── mod.rs
│   ├── controller.rs    # PTY management
│   └── capture.rs       # Terminal output capture
├── media/               # Media generation
│   ├── mod.rs
│   ├── screenshot.rs    # Screenshot functionality
│   ├── gif.rs           # GIF generation
│   └── video.rs         # Video recording
└── cli/                 # CLI interface
    ├── mod.rs
    └── commands.rs      # Command implementations
```

## Key Features

1. **Playwright-style Automation**: Script terminal interactions
2. **Multiple Output Formats**: PNG, GIF, MP4
3. **Cross-platform**: Windows (ConPTY), Unix (PTY)
4. **High Performance**: Rust-native with optimized capture
5. **Developer Friendly**: Easy integration into CI/CD
6. **Themeable**: Custom terminal themes and styling