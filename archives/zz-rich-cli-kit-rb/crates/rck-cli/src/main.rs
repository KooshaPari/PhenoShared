//! rck — Rich-CLI Kit CLI.
//!
//! One-shot inline renderer:
//!   `rck detect | image | progress | panel | demo`
//!   `rck link | copy | task-start | task-end`
//!   `rck ask | pick | input`
//!   `rck shader install`

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use rck_core::{
    ask, detect, emit_clipboard, emit_hyperlink, emit_image, emit_panel, emit_progress,
    emit_task_markers, in_tmux, input, pick, shader, BorderStyle, Capabilities, ImageData, Outcome,
    ProgressStyle, TaskPhase,
};
use std::fs;
use std::io::{self, Read, Write};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    name = "rck",
    version,
    about = "Rich-CLI Kit — inline images, progress bars, status panels, OSC 8 links, OSC 52 clipboard, OSC 133 task markers, and alt-screen interactive primitives"
)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand, Debug)]
enum Cmd {
    /// Print detected terminal capabilities as JSON.
    Detect,
    /// Render an image inline (PNG/JPG via kitty graphics; text fallback otherwise).
    Image {
        path: PathBuf,
        #[arg(long)]
        alt: Option<String>,
    },
    /// Render a one-shot progress bar.
    Progress {
        ratio: f32,
        #[arg(long)]
        label: Option<String>,
        #[arg(long)]
        ascii: bool,
    },
    /// Render a titled status panel from a file or stdin.
    Panel {
        #[arg(long)]
        title: String,
        #[arg(long)]
        file: Option<PathBuf>,
        #[arg(long, default_value = "rounded")]
        border: String,
    },
    /// Emit an OSC 8 hyperlink (clickable in Ghostty / kitty / WezTerm / iTerm2).
    Link { url: String, text: String },
    /// Copy content to the system clipboard via OSC 52. With --stdin, reads stdin.
    Copy {
        /// Content to copy. Use --stdin to read from stdin instead.
        content: Option<String>,
        #[arg(long)]
        stdin: bool,
    },
    /// Emit an OSC 133 task marker indicating the start of an agent task.
    TaskStart {
        /// Optional identifier (currently informational; not encoded in OSC 133).
        #[arg(long)]
        id: Option<String>,
    },
    /// Emit an OSC 133;D task end marker with an exit code.
    TaskEnd {
        #[arg(long, default_value_t = 0)]
        exit: i32,
    },
    /// Yes/no confirm (alt-screen + kitty-kbd, plain-stdin fallback). Exits 0=yes, 1=no, 2=cancel.
    Ask { question: String },
    /// Single-choice picker. Prints selection on stdout.
    Pick {
        prompt: String,
        choices: Vec<String>,
    },
    /// Single-line input. Prints entered value on stdout.
    Input { prompt: String },
    /// Manage the bundled Ghostty shader pack.
    Shader {
        #[command(subcommand)]
        action: ShaderCmd,
    },
    /// Show all four renderers as a self-test.
    Demo,
}

#[derive(Subcommand, Debug)]
enum ShaderCmd {
    /// List bundled shader names.
    List,
    /// Copy a bundled shader into Ghostty's shader dir.
    Install {
        name: String,
        /// Override the install directory.
        #[arg(long)]
        dir: Option<PathBuf>,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let caps = detect();
    let mut out = io::stdout().lock();

    match cli.cmd {
        Cmd::Detect => {
            let json = serde_json::to_string_pretty(&caps)?;
            writeln!(out, "{json}")?;
        }
        Cmd::Image { path, alt } => {
            let mut img = ImageData::from_path(&path)
                .with_context(|| format!("loading image {}", path.display()))?;
            if let Some(a) = alt {
                img.alt_text = Some(a);
            }
            emit_image(&mut out, &caps, &img)?;
        }
        Cmd::Progress {
            ratio,
            label,
            ascii,
        } => {
            let style = if ascii {
                ProgressStyle::Ascii
            } else {
                ProgressStyle::Blocks
            };
            emit_progress(&mut out, &caps, ratio, style, label.as_deref())?;
        }
        Cmd::Panel {
            title,
            file,
            border,
        } => {
            let body = read_body(file.as_deref())?;
            let lines: Vec<&str> = body.lines().collect();
            let style = match border.as_str() {
                "square" => BorderStyle::Square,
                "ascii" => BorderStyle::Ascii,
                _ => BorderStyle::Rounded,
            };
            emit_panel(&mut out, &caps, &title, &lines, style)?;
        }
        Cmd::Link { url, text } => {
            let s = emit_hyperlink(caps.hyperlinks, caps.in_tmux, &url, &text);
            writeln!(out, "{s}")?;
        }
        Cmd::Copy { content, stdin } => {
            let data = if stdin {
                let mut s = String::new();
                io::stdin().read_to_string(&mut s)?;
                s
            } else {
                content.context("--stdin not set and no content provided")?
            };
            let seq = emit_clipboard(caps.clipboard, caps.in_tmux, &data);
            if seq.is_empty() {
                eprintln!(
                    "[rck copy] clipboard not supported on this terminal; content not copied"
                );
            } else {
                out.write_all(seq.as_bytes())?;
            }
        }
        Cmd::TaskStart { id } => {
            let seq = emit_task_markers(caps.task_markers, caps.in_tmux, TaskPhase::PromptStart);
            out.write_all(seq.as_bytes())?;
            // Also emit CommandStart so output following this marker is bracketed.
            let seq_c = emit_task_markers(caps.task_markers, caps.in_tmux, TaskPhase::CommandStart);
            out.write_all(seq_c.as_bytes())?;
            if let Some(id) = id {
                // Title-set as informational secondary signal (cheap).
                let title_seq = format!("\x1b]2;rck task: {id}\x1b\\");
                out.write_all(rck_core::wrap_for_tmux_with(&title_seq, in_tmux()).as_bytes())?;
            }
        }
        Cmd::TaskEnd { exit } => {
            let seq =
                emit_task_markers(caps.task_markers, caps.in_tmux, TaskPhase::CommandEnd(exit));
            out.write_all(seq.as_bytes())?;
        }
        Cmd::Ask { question } => {
            drop(out);
            match ask(&caps, &question)? {
                Outcome::Selected(true) => std::process::exit(0),
                Outcome::Selected(false) => std::process::exit(1),
                Outcome::Cancelled => std::process::exit(2),
            }
        }
        Cmd::Pick { prompt, choices } => {
            drop(out);
            match pick(&caps, &prompt, &choices)? {
                Outcome::Selected(s) => {
                    let mut o = io::stdout().lock();
                    writeln!(o, "{s}")?;
                }
                Outcome::Cancelled => std::process::exit(2),
            }
        }
        Cmd::Input { prompt } => {
            drop(out);
            match input(&caps, &prompt)? {
                Outcome::Selected(s) => {
                    let mut o = io::stdout().lock();
                    writeln!(o, "{s}")?;
                }
                Outcome::Cancelled => std::process::exit(2),
            }
        }
        Cmd::Shader { action } => match action {
            ShaderCmd::List => {
                for n in shader::list() {
                    writeln!(out, "{n}")?;
                }
            }
            ShaderCmd::Install { name, dir } => {
                let path = shader::install(&name, dir.as_deref())?;
                writeln!(out, "installed: {}", path.display())?;
                writeln!(out, "add to ~/.config/ghostty/config:")?;
                writeln!(out, "    custom-shader = shaders/{name}.glsl")?;
                writeln!(out, "    custom-shader-animation = true")?;
            }
        },
        Cmd::Demo => demo(&mut out, &caps)?,
    }
    Ok(())
}

fn read_body(file: Option<&std::path::Path>) -> Result<String> {
    match file {
        None => Ok(String::new()),
        Some(p) if p == std::path::Path::new("-") => {
            let mut s = String::new();
            io::stdin().read_to_string(&mut s)?;
            Ok(s)
        }
        Some(p) => Ok(fs::read_to_string(p).with_context(|| format!("reading {}", p.display()))?),
    }
}

fn demo<W: Write>(out: &mut W, caps: &Capabilities) -> Result<()> {
    writeln!(out, "rck demo\n")?;
    writeln!(out, "1) capabilities:")?;
    writeln!(out, "{}\n", serde_json::to_string_pretty(caps)?)?;

    writeln!(out, "2) progress bars:")?;
    for r in [0.15f32, 0.5, 0.85, 1.0] {
        emit_progress(out, caps, r, ProgressStyle::Blocks, Some("task"))?;
    }
    writeln!(out)?;

    writeln!(out, "3) status panel:")?;
    emit_panel(
        out,
        caps,
        "status",
        &["build: ok", "tests: 12 passed", "graphics: detected"],
        BorderStyle::Rounded,
    )?;
    writeln!(out)?;

    writeln!(out, "4) hyperlink: ")?;
    let s = emit_hyperlink(
        caps.hyperlinks,
        caps.in_tmux,
        "https://ghostty.org",
        "Ghostty",
    );
    writeln!(out, "{s}")?;

    writeln!(
        out,
        "5) image: (skipped — pass `rck image <path>` to render)"
    )?;
    Ok(())
}
