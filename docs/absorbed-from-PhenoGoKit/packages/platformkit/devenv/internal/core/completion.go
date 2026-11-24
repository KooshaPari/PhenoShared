// Package completion provides shell completion generation
package completion

import (
	"fmt"
	"html/template"
	"os"
	"path/filepath"
	"strings"
)
// Shell represents a supported shell
type Shell string

const (
	Bash Shell = "bash"
	Zsh  Shell = "zsh"
	Fish Shell = "fish"
)

// Command represents a CLI command for completion
type Command struct {
	Name        string
	Aliases     []string
	Description string
	Subcommands []*Command
	Flags       []Flag
}

// Flag represents a CLI flag
type Flag struct {
	Name        string
	Short       string
	Description string
	Type        FlagType
	Required    bool
	Default     string
}

// FlagType represents the type of a flag
type FlagType string

const (
	FlagTypeBool   FlagType = "bool"
	FlagTypeString FlagType = "string"
	FlagTypeInt    FlagType = "int"
	FlagTypeFloat  FlagType = "float"
	FlagTypeSlice  FlagType = "slice"
)

// Generator generates shell completion scripts
type Generator struct {
	Commands []*Command
	Name    string
}

// NewGenerator creates a new completion generator
func NewGenerator(name string) *Generator {
	return &Generator{
		Name:    name,
		Commands: []*Command{},
	}
}

// AddCommand adds a command to the generator
func (g *Generator) AddCommand(cmd *Command) {
	g.Commands = append(g.Commands, cmd)
}

// Generate generates the completion script for the specified shell
func (g *Generator) Generate(shell Shell) (string, error) {
	switch shell {
	case Bash:
		return g.generateBash()
	case Zsh:
		return g.generateZsh()
	case Fish:
		return g.generateFish()
	default:
		return "", fmt.Errorf("unsupported shell: %s", shell)
	}
}

// Write writes the completion script to a file
func (g *Generator) Write(shell Shell, path string) error {
	script, err := g.Generate(shell)
	if err != nil {
		return err
	}
	return os.WriteFile(path, []byte(script), 0755)
}

func (g *Generator) generateBash() (string, error) {
	tmpl := `#!/bin/bash
# bash completion for {{.Name}}

_{{name}}_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Main commands
    opts="{{range .Commands}}{{.Name}} {{end}}"

    case "${prev}" in
{{range .Commands}}        {{.Name}})
            opts="{{range .Subcommands}}{{.Name}} {{end}}"
            ;;
{{end}}    esac

    COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
    return 0
}

complete -F _{{name}}_completion {{.Name}}
`

	data := struct {
		Name    string
		Commands []*Command
	}{
		Name:    g.Name,
		Commands: g.Commands,
	}

	return executeTemplate(tmpl, data, g.Name)
}

func (g *Generator) generateZsh() (string, error) {
	tmpl := `#!/bin/zsh
# zsh completion for {{.Name}}

#compdef {{.Name}}

_{{- .Name}}() {
    local -a commands
    commands=(
{{range .Commands}}        "{{.Name}}:{{.Description}}"
{{end}}    )

    _arguments -C \
        '-h[show help]' \
        '--help[show help]' \
        '-v[verbose]' \
        '--verbose[verbose]' \
        '*::subcommand:->subcommand' \
        '*::args:->args'

    case "$state" in
        subcommand)
            _describe 'command' commands
            ;;
    esac
}

_{{- .Name}} "$@"
`

	data := struct {
		Name    string
		Commands []*Command
	}{
		Name:    g.Name,
		Commands: g.Commands,
	}

	return executeTemplate(tmpl, data, g.Name)
}

func (g *Generator) generateFish() (string, error) {
	tmpl := `#!/usr/bin/env fish
# fish completion for {{.Name}}

function __complete_{{.Name}}
    set -l cmd (commandline -opc)
    if test (count $cmd) -eq 1
        echo "{{range .Commands}}{{.Name}}\t{{.Description}}
{{end}}"
    end
end

complete -c {{.Name}} -f -a "(__complete_{{.Name}})"
`

	data := struct {
		Name    string
		Commands []*Command
	}{
		Name:    g.Name,
		Commands: g.Commands,
	}

	return executeTemplate(tmpl, data, g.Name)
}

func executeTemplate(tmpl string, data interface{}, name string) (string, error) {
	t, err := template.New(name).Parse(tmpl)
	if err != nil {
		return "", fmt.Errorf("failed to parse template: %w", err)
	}

	var buf strings.Builder
	if err := t.Execute(&buf, data); err != nil {
		return "", fmt.Errorf("failed to execute template: %w", err)
	}

	return buf.String(), nil
}
