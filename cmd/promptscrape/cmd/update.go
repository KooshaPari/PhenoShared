package cmd

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"github.com/KooshaPari/PhenoShared/cmd/promptscrape/internal/installpath"
	"github.com/spf13/cobra"
)

const (
	// releaseRepo is the GitHub repository that publishes promptscrape releases.
	// Override at build time with -ldflags "-X ...cmd.releaseRepo=owner/name".
	releaseRepo = "KooshaPari/PhenoShared"

	// releaseAssetPrefix is the prefix of the published binary artifact name.
	// The full asset name is <prefix>-<os>-<arch>.
	releaseAssetPrefix = "promptscrape"

	// releaseTimeout bounds the HTTP requests made during an update.
	releaseTimeout = 60 * time.Second
)

var (
	updateDir     string
	updateVersion string
)

var updateCmd = &cobra.Command{
	Use:   "update",
	Short: "Update promptscrape to the latest release",
	Long: `Download the latest published promptscrape release and replace the installed binary.

The binary is downloaded to a temporary file, verified to be executable, and
only then moved into place, so a failed download never breaks the install.`,
	Example: `  promptscrape update
  promptscrape update --version v0.2.0`,
	RunE: func(cmd *cobra.Command, args []string) error {
		target, err := resolveUpdateTarget()
		if err != nil {
			return err
		}

		asset := releaseAssetName()
		url, err := releaseURL(asset)
		if err != nil {
			return err
		}

		fmt.Fprintf(cmd.ErrOrStderr(), "Downloading %s\n", url)

		tmp, err := os.CreateTemp("", "promptscrape-update-*")
		if err != nil {
			return fmt.Errorf("cannot create temp file: %w", err)
		}
		tmpName := tmp.Name()
		defer os.Remove(tmpName)

		client := &http.Client{Timeout: releaseTimeout}
		resp, err := client.Get(url)
		if err != nil {
			tmp.Close()
			return fmt.Errorf("download failed: %w", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			tmp.Close()
			return fmt.Errorf("download failed: HTTP %d for %s", resp.StatusCode, url)
		}

		written, err := io.Copy(tmp, resp.Body)
		closeErr := tmp.Close()
		if err != nil {
			return fmt.Errorf("download failed: %w", err)
		}
		if closeErr != nil {
			return fmt.Errorf("cannot finish writing %s: %w", tmpName, closeErr)
		}
		if written == 0 {
			return fmt.Errorf("download failed: empty artifact at %s", url)
		}

		if err := os.Chmod(tmpName, 0o755); err != nil {
			return fmt.Errorf("cannot make %s executable: %w", tmpName, err)
		}

		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return fmt.Errorf("cannot create %s: %w", filepath.Dir(target), err)
		}
		if err := os.Rename(tmpName, target); err != nil {
			// Rename across filesystems fails; fall back to copy.
			if copyErr := copyExecutable(tmpName, target); copyErr != nil {
				return fmt.Errorf("cannot install to %s: %w", target, copyErr)
			}
			os.Remove(tmpName)
		}

		fmt.Fprintf(cmd.OutOrStdout(), "Updated %s\n", target)
		return nil
	},
}

// resolveUpdateTarget works out which file the update should replace.
//
// The --dir flag names a directory, matching the install script and the
// install command. A path that names an existing file is used as-is, so
// --dir /usr/local/bin/promptscrape also does the obvious thing.
func resolveUpdateTarget() (string, error) {
	if updateDir != "" {
		info, err := os.Stat(updateDir)
		if err == nil && !info.IsDir() {
			return updateDir, nil
		}
		return filepath.Join(updateDir, installpath.BinaryName()), nil
	}

	if located := installpath.Locate(); located != "" {
		return located, nil
	}

	dir, err := installpath.Preferred()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, installpath.BinaryName()), nil
}

// releaseAssetName returns the published artifact name for this platform.
func releaseAssetName() string {
	return fmt.Sprintf("%s-%s-%s", releaseAssetPrefix, runtime.GOOS, runtime.GOARCH)
}

// releaseURL returns the download URL for an asset.
func releaseURL(asset string) (string, error) {
	if updateVersion != "" {
		return fmt.Sprintf("https://github.com/%s/releases/download/%s/%s", releaseRepo, updateVersion, asset), nil
	}
	return fmt.Sprintf("https://github.com/%s/releases/latest/download/%s", releaseRepo, asset), nil
}

func init() {
	rootCmd.AddCommand(updateCmd)
	updateCmd.Flags().StringVar(&updateDir, "dir", "", "Install into this directory instead of the detected install location")
	updateCmd.Flags().StringVar(&updateVersion, "version", "", "Install a specific release tag (default: latest)")
}
