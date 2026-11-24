// Package cli provides shared CLI utilities for Phenotype services.
package cli

import (
	"github.com/spf13/cobra"
)

// CommandBuilder provides a fluent interface for building Cobra commands.
type CommandBuilder struct {
	cmd *cobra.Command
}

// NewCommandBuilder creates a new CommandBuilder instance.
func NewCommandBuilder(use string) *CommandBuilder {
	return &CommandBuilder{
		cmd: &cobra.Command{
			Use: use,
		},
	}
}

// Short sets the short description for the command.
func (cb *CommandBuilder) Short(short string) *CommandBuilder {
	cb.cmd.Short = short
	return cb
}

// Long sets the long description for the command.
func (cb *CommandBuilder) Long(long string) *CommandBuilder {
	cb.cmd.Long = long
	return cb
}

// RunE sets the RunE function for the command.
func (cb *CommandBuilder) RunE(runFunc func(cmd *cobra.Command, args []string) error) *CommandBuilder {
	cb.cmd.RunE = runFunc
	return cb
}

// Build returns the constructed cobra command.
func (cb *CommandBuilder) Build() *cobra.Command {
	return cb.cmd
}

// AddStringFlag adds a string flag to the command.
func (cb *CommandBuilder) AddStringFlag(name string, shorthand string, defaultValue string, usage string) *CommandBuilder {
	cb.cmd.Flags().StringP(name, shorthand, defaultValue, usage)
	return cb
}

// AddBoolFlag adds a boolean flag to the command.
func (cb *CommandBuilder) AddBoolFlag(name string, shorthand string, defaultValue bool, usage string) *CommandBuilder {
	cb.cmd.Flags().BoolP(name, shorthand, defaultValue, usage)
	return cb
}

// AddIntFlag adds an integer flag to the command.
func (cb *CommandBuilder) AddIntFlag(name string, shorthand string, defaultValue int, usage string) *CommandBuilder {
	cb.cmd.Flags().IntP(name, shorthand, defaultValue, usage)
	return cb
}

// AddSubcommand adds a subcommand to the command.
func (cb *CommandBuilder) AddSubcommand(subCmd *cobra.Command) *CommandBuilder {
	cb.cmd.AddCommand(subCmd)
	return cb
}
