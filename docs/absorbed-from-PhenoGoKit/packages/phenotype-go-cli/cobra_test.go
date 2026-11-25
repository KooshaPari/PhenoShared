package cli_test

import (
	"errors"
	"testing"

	"github.com/KooshaPari/phenotype-go-cli"
	"github.com/spf13/cobra"
)

func TestExitCodeConstants(t *testing.T) {
	tests := []struct {
		name string
		code cli.ExitCode
		want int
	}{
		{"ExitSuccess", cli.ExitSuccess, 0},
		{"ExitError", cli.ExitGeneral, 1},
		{"ExitBadArgs", cli.ExitBadArgs, 2},
		{"ExitIOError", cli.ExitIOError, 3},
		{"ExitTimeout", cli.ExitTimeout, 4},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := int(tt.code); got != tt.want {
				t.Errorf("ExitCode = %d, want %d", got, tt.want)
			}
		})
	}
}

func TestNewExitError(t *testing.T) {
	cause := errors.New("underlying cause")
	ee := cli.NewExitError(cli.ExitBadArgs, "invalid flag value", cause)

	if ee == nil {
		t.Fatal("NewExitError returned nil")
	}

	t.Run("Code", func(t *testing.T) {
		if got, want := int(ee.Code), 2; got != want {
			t.Errorf("Code = %d, want %d", got, want)
		}
	})

	t.Run("Error returns message", func(t *testing.T) {
		if got, want := ee.Error(), "invalid flag value"; got != want {
			t.Errorf("Error() = %q, want %q", got, want)
		}
	})

	t.Run("Unwrap returns cause", func(t *testing.T) {
		if !errors.Is(ee, cause) {
			t.Error("errors.Is(ee, cause) should be true")
		}
	})
}

func TestExitErrorNoMsg(t *testing.T) {
	cause := errors.New("disk full")
	ee := cli.NewExitError(cli.ExitIOError, "", cause)

	t.Run("Error falls back to cause", func(t *testing.T) {
		if got, want := ee.Error(), "disk full"; got != want {
			t.Errorf("Error() = %q, want %q", got, want)
		}
	})
}

func TestExitErrorNoMsgNoCause(t *testing.T) {
	ee := cli.NewExitError(cli.ExitGeneral, "", nil)

	t.Run("Error returns fallback", func(t *testing.T) {
		if got, want := ee.Error(), "unknown error"; got != want {
			t.Errorf("Error() = %q, want %q", got, want)
		}
	})
}

func TestStandardErrorHandler(t *testing.T) {
	cmd := &cobra.Command{Use: "test"}

	t.Run("nil error returns 0", func(t *testing.T) {
		if got := cli.StandardErrorHandler(cmd, nil); got != 0 {
			t.Errorf("StandardErrorHandler(nil) = %d, want 0", got)
		}
	})

	t.Run("plain error returns 1", func(t *testing.T) {
		err := errors.New("something broke")
		if got := cli.StandardErrorHandler(cmd, err); got != 1 {
			t.Errorf("StandardErrorHandler(plain) = %d, want 1", got)
		}
	})

	t.Run("ExitError returns its code", func(t *testing.T) {
		err := cli.NewExitError(cli.ExitBadArgs, "bad flag", nil)
		if got := cli.StandardErrorHandler(cmd, err); got != 2 {
			t.Errorf("StandardErrorHandler(ExitError) = %d, want 2", got)
		}
	})

	t.Run("ExitError wrapped via errors.Join", func(t *testing.T) {
		inner := cli.NewExitError(cli.ExitTimeout, "timed out", nil)
		wrapped := errors.Join(inner)
		// errors.As walks Unwrap() []error so it finds the ExitError.
		if got := cli.StandardErrorHandler(cmd, wrapped); got != 4 {
			t.Errorf("StandardErrorHandler(wrapped) = %d, want 4", got)
		}
	})
}

func TestVersionFlagValue(t *testing.T) {
	v := &cli.VersionFlagValue{}

	t.Run("initial state", func(t *testing.T) {
		if v.IsCalled() {
			t.Error("IsCalled() should be false initially")
		}
	})

	t.Run("Set marks called", func(t *testing.T) {
		if err := v.Set("1.0.0"); err != nil {
			t.Fatalf("Set() error = %v", err)
		}
		if !v.IsCalled() {
			t.Error("IsCalled() should be true after Set")
		}
	})

	t.Run("String returns version", func(t *testing.T) {
		if got, want := v.String(), "1.0.0"; got != want {
			t.Errorf("String() = %q, want %q", got, want)
		}
	})

	t.Run("Type returns version", func(t *testing.T) {
		if got, want := v.Type(), "version"; got != want {
			t.Errorf("Type() = %q, want %q", got, want)
		}
	})
}

func TestCommandBuilder(t *testing.T) {
	t.Run("fluent builder produces command", func(t *testing.T) {
		cmd := cli.NewCommandBuilder("mycmd").
			Short("short desc").
			Long("long desc").
			Example("  mycmd --help").
			StringFlag("output", "o", "stdout", "output file").
			BoolFlag("verbose", "v", false, "verbose logging").
			IntFlag("retries", "r", 3, "retry count").
			Build()

		if cmd.Use != "mycmd" {
			t.Errorf("Use = %q, want %q", cmd.Use, "mycmd")
		}
		if cmd.Short != "short desc" {
			t.Errorf("Short = %q, want %q", cmd.Short, "short desc")
		}
	})

	t.Run("AddSubcommand", func(t *testing.T) {
		root := cli.NewCommandBuilder("root").Build()
		sub := cli.NewCommandBuilder("sub").Build()
		cli.AddCommand(root, sub)

		if len(root.Commands()) != 1 {
			t.Errorf("expected 1 subcommand, got %d", len(root.Commands()))
		}
	})
}

func TestCreateCommand(t *testing.T) {
	cmd := cli.CreateCommand("hello", "say hello", "long help", "  hello world",
		func(cmd *cobra.Command, args []string) error {
			return nil
		})

	if cmd.Use != "hello" {
		t.Errorf("Use = %q, want %q", cmd.Use, "hello")
	}
}

func TestCreateRootCommand(t *testing.T) {
	config := cli.RootCommandConfig{
		Name:    "myapp",
		Short:   "my app",
		Long:    "long description",
		Version: "1.0.0",
		Examples: "  myapp --help",
	}

	cmd := cli.CreateRootCommand(config, func(cmd *cobra.Command, args []string) error {
		return nil
	})

	if cmd.Use != "myapp" {
		t.Errorf("Use = %q, want %q", cmd.Use, "myapp")
	}
	if cmd.Version != "1.0.0" {
		t.Errorf("Version = %q, want %q", cmd.Version, "1.0.0")
	}
}
