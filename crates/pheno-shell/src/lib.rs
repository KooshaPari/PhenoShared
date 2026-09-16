//! PhenoShell - CLI Shell Framework

use anyhow::Result;
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, Mutex};
use tokio::io::BufReader;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt};

/// Shell state
pub struct Shell<S: ShellState = InMemoryShellState> {
    name: String,
    #[allow(dead_code)]
    state: Arc<tokio::sync::RwLock<S>>,
    commands: Vec<CommandDef>,
    history: Arc<Mutex<Vec<String>>>,
}

impl Shell {
    pub fn new(name: impl Into<String>) -> Result<Self> {
        Ok(Self {
            name: name.into(),
            state: Arc::new(tokio::sync::RwLock::new(InMemoryShellState::new())),
            commands: Vec::new(),
            history: Arc::new(Mutex::new(Vec::new())),
        })
    }

    pub fn register_command(&mut self, cmd: CommandDef) {
        self.commands.push(cmd);
    }

    pub async fn run(&self) -> Result<()> {
        println!("{} shell v{}", self.name, env!("CARGO_PKG_VERSION"));

        let stdin = BufReader::new(tokio::io::stdin());
        let mut lines = stdin.lines();
        let mut stdout = tokio::io::stdout();

        while let Ok(Some(line)) = lines.next_line().await {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            self.history.lock().unwrap().push(line.to_string());

            match self.execute_line(line).await {
                Ok(Some(output)) => {
                    stdout.write_all(output.as_bytes()).await?;
                    stdout.write_all(b"\n").await?;
                }
                Ok(None) => {}
                Err(e) => {
                    stdout
                        .write_all(format!("Error: {}\n", e).as_bytes())
                        .await?;
                }
            }
        }

        Ok(())
    }

    async fn execute_line(&self, line: &str) -> Result<Option<String>, ShellError> {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.is_empty() {
            return Ok(None);
        }

        match parts[0] {
            "exit" | "quit" => std::process::exit(0),
            "help" => Ok(Some(self.help_text())),
            "history" => Ok(Some(self.history.lock().unwrap().join("\n"))),
            "completions" => {
                let shell = parts.get(1).copied().unwrap_or("bash");
                match self.generate_completions(shell) {
                    Ok(script) => Ok(Some(script)),
                    Err(e) => {
                        eprintln!("Error: {} ({})", e, e.recovery_hint());
                        Ok(None)
                    }
                }
            }
            cmd => {
                if let Some(cmd_def) = self.commands.iter().find(|c| c.name == cmd) {
                    (cmd_def.handler)(&parts[1..]).await
                } else {
                    Err(ShellError::UnknownCommand(cmd.to_string()))
                }
            }
        }
    }

    fn help_text(&self) -> String {
        let mut text = String::from("Available commands:\n");
        text.push_str("  exit, quit              - Exit the shell\n");
        text.push_str("  help                    - Show this help\n");
        text.push_str("  history                 - Show command history\n");
        text.push_str("  completions [shell]     - Print shell completion script\n");

        for cmd in &self.commands {
            text.push_str(&format!("  {:24} - {}\n", cmd.name, cmd.description));
        }
        text
    }

    /// Generate shell completion script for the given shell (bash, zsh, fish, powershell).
    ///
    /// Returns a shell completion script as a string that provides tab-completion
    /// for registered commands.
    pub fn generate_completions(&self, shell: &str) -> Result<String, ShellError> {
        match shell.to_ascii_lowercase().as_str() {
            "bash" => Ok(self.gen_bash_completions()),
            "zsh" => Ok(self.gen_zsh_completions()),
            "fish" => Ok(self.gen_fish_completions()),
            "powershell" => Ok(self.gen_powershell_completions()),
            _ => Err(ShellError::InvalidArgs(format!(
                "unsupported shell: {shell}. Supported: bash, zsh, fish, powershell"
            ))),
        }
    }

    fn gen_bash_completions(&self) -> String {
        let mut script = format!(
            "_{name}_completions() {{\n  local cur=${{COMP_WORDS[COMP_CWORD]}}\n",
            name = &self.name
        );
        let cmds: Vec<&str> = self
            .commands
            .iter()
            .map(|c| c.name)
            .chain(["exit", "help", "history", "completions"])
            .collect();
        script.push_str(&format!(
            "  COMPREPLY=( $(compgen -W \"{}\" -- \"$cur\") )\n",
            cmds.join(" ")
        ));
        script.push_str("}}\n");
        script.push_str(&format!(
            "complete -F _{name}_completions {name}\n",
            name = &self.name
        ));
        script
    }

    fn gen_zsh_completions(&self) -> String {
        let mut script = format!(
            "#compdef {name}\n_{name}() {{\n  local -a commands\n",
            name = &self.name
        );
        script.push_str("  commands=(\n");
        for c in &self.commands {
            script.push_str(&format!(
                "    '{}:{}'\n",
                c.name,
                c.description.replace('\'', "'\\''")
            ));
        }
        script.push_str("    'exit:Exit the shell'\n");
        script.push_str("    'help:Show this help'\n");
        script.push_str("    'history:Show command history'\n");
        script.push_str("    'completions:Print shell completion script'\n");
        script.push_str("  )\n");
        script.push_str("  _describe 'command' commands\n");
        script.push_str("}\n");
        script.push_str(&format!("_{name}\n", name = &self.name));
        script
    }

    fn gen_fish_completions(&self) -> String {
        let mut script = String::new();
        script.push_str(&format!("complete -c {name} -f\n", name = &self.name));
        for c in &self.commands {
            script.push_str(&format!(
                "complete -c {name} -n '__fish_use_subcommand' -a '{cname}' -d '{desc}'\n",
                name = &self.name,
                cname = c.name,
                desc = c.description
            ));
        }
        script.push_str(&format!(
            "complete -c {name} -n '__fish_use_subcommand' -a 'exit' -d 'Exit the shell'\n",
            name = &self.name
        ));
        script.push_str(&format!(
            "complete -c {name} -n '__fish_use_subcommand' -a 'help' -d 'Show this help'\n",
            name = &self.name
        ));
        script.push_str(&format!(
            "complete -c {name} -n '__fish_use_subcommand' -a 'history' -d 'Show command history'\n",
            name = &self.name
        ));
        script.push_str(&format!(
            "complete -c {name} -n '__fish_use_subcommand' -a 'completions' -d 'Print shell completion script'\n",
            name = &self.name
        ));
        script
    }

    fn gen_powershell_completions(&self) -> String {
        let mut script = format!(
            "Register-ArgumentCompleter -Native -CommandName {name} -ScriptBlock {{\n  param($wordToComplete, $commandAst, $cursorPosition)\n",
            name = &self.name
        );
        let cmds: Vec<&str> = self
            .commands
            .iter()
            .map(|c| c.name)
            .chain(["exit", "help", "history", "completions"])
            .collect();
        let cmds_str = cmds
            .iter()
            .map(|c| format!("'{}'", c))
            .collect::<Vec<_>>()
            .join(", ");
        script.push_str(&format!(
            "  $commands = @({cmds_str})\n",
            cmds_str = cmds_str
        ));
        script.push_str("  return $commands | Where-Object { $_ -like \"$wordToComplete*\" }\n}");
        script
    }
}

/// Command definition
#[allow(clippy::type_complexity)]
pub struct CommandDef {
    pub name: &'static str,
    pub description: &'static str,
    pub handler:
        fn(&[&str]) -> Pin<Box<dyn Future<Output = Result<Option<String>, ShellError>> + Send>>,
}

/// Shell state trait
pub trait ShellState: Send + Sync {
    fn get(&self, key: &str) -> Option<String>;
    fn set(&mut self, key: &str, value: String);
}

/// In-memory shell state
pub struct InMemoryShellState {
    data: std::collections::HashMap<String, String>,
}

impl InMemoryShellState {
    pub fn new() -> Self {
        Self {
            data: std::collections::HashMap::new(),
        }
    }
}

impl Default for InMemoryShellState {
    fn default() -> Self {
        Self::new()
    }
}

impl ShellState for InMemoryShellState {
    fn get(&self, key: &str) -> Option<String> {
        self.data.get(key).cloned()
    }

    fn set(&mut self, key: &str, value: String) {
        self.data.insert(key.to_string(), value);
    }
}

#[derive(thiserror::Error, Debug)]
pub enum ShellError {
    #[error("unknown command: {0}")]
    UnknownCommand(String),
    #[error("invalid arguments: {0}")]
    InvalidArgs(String),
}

impl ShellError {
    /// Return a user-facing recovery hint for this error.
    pub fn recovery_hint(&self) -> &str {
        match self {
            ShellError::UnknownCommand(_) => "type 'help' to see available commands",
            ShellError::InvalidArgs(_) => "check the command syntax with 'help'",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generate_completions_works_for_bash() {
        let mut shell = Shell::new("testcli").unwrap();
        shell.register_command(CommandDef {
            name: "deploy",
            description: "Deploy a service",
            handler: |_args| Box::pin(async { Ok(Some("deployed".into())) }),
        });
        let script = shell.generate_completions("bash").unwrap();
        assert!(
            script.contains("deploy"),
            "completions should mention registered commands"
        );
        assert!(
            script.contains("testcli"),
            "completions should mention the shell name"
        );
    }

    #[test]
    fn generate_completions_rejects_unknown_shell() {
        let shell = Shell::new("testcli").unwrap();
        assert!(shell.generate_completions("noshell").is_err());
    }

    #[test]
    fn error_recovery_hints() {
        let err = ShellError::UnknownCommand("foo".into());
        assert!(err.recovery_hint().contains("help"));
        let err = ShellError::InvalidArgs("bad".into());
        assert!(err.recovery_hint().contains("help"));
    }
}
