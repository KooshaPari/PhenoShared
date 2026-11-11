# typed: false
# frozen_string_literal: true

# Homebrew formula template for SessionLedger.
#
# Status: in-repo template. Publish to a tap (or homebrew-core PR) after a
# tagged GitHub Release exists and the sha256 values below are filled from
# that Release's SHA256SUMS.
#
# Suggested tap path after publish:
#   Formula/sessionledger.rb
#
# Install (once published to a tap):
#   brew install koosha/sessionledger/sessionledger
#
# Until then, prefer:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.sh | sh
#   cargo install --git https://github.com/KooshaPari/SessionLedger --locked --path crates/sl-daemon

class Sessionledger < Formula
  desc "OKF-native session compiler — capture, archive, and replay AI agent sessions"
  homepage "https://github.com/KooshaPari/SessionLedger"
  license any_of: ["MIT", "Apache-2.0"]
  head "https://github.com/KooshaPari/SessionLedger.git", branch: "main"

  on_macos do
    on_arm do
      url "https://github.com/KooshaPari/SessionLedger/releases/download/v0.1.0/sl-viewer-v0.1.0-aarch64-apple-darwin.tar.gz"
      # Fill from SHA256SUMS for sl-viewer-v0.1.0-aarch64-apple-darwin.tar.gz
      sha256 "0000000000000000000000000000000000000000000000000000000000000000"
    end
    on_intel do
      url "https://github.com/KooshaPari/SessionLedger/releases/download/v0.1.0/sl-viewer-v0.1.0-x86_64-apple-darwin.tar.gz"
      # Fill from SHA256SUMS for sl-viewer-v0.1.0-x86_64-apple-darwin.tar.gz
      sha256 "0000000000000000000000000000000000000000000000000000000000000000"
    end
  end

  on_linux do
    on_intel do
      url "https://github.com/KooshaPari/SessionLedger/releases/download/v0.1.0/sl-viewer-v0.1.0-x86_64-unknown-linux-gnu.tar.gz"
      # Fill from SHA256SUMS for sl-viewer-v0.1.0-x86_64-unknown-linux-gnu.tar.gz
      sha256 "0000000000000000000000000000000000000000000000000000000000000000"
    end
  end

  def install
    # Release archives contain: sl-viewer-vX.Y.Z-<triple>/sl-viewer
    viewer = Dir["**/sl-viewer"].reject { |p| File.directory?(p) }.first
    odie "sl-viewer binary missing from release archive" if viewer.nil?
    bin.install viewer => "sl-viewer"
  end

  def caveats
    <<~EOS
      This formula installs the sl-viewer desktop binary from GitHub Releases.

      The long-running sl-daemon is not bottled here yet. Install it with Cargo:

        cargo install --git https://github.com/KooshaPari/SessionLedger --locked --path crates/sl-daemon

      Then start it with native local-session auto-discovery:

        sl-daemon serve \\
          --out "$HOME/.local/share/sessionledger/out" \\
          --http-bind 127.0.0.1:8080

      Add --watch <path> only when overriding discovery for a custom transcript root.

      Before publishing this formula to a tap, replace each sha256 placeholder
      with the matching digest from the Release SHA256SUMS file.
    EOS
  end

  test do
    assert_path_exists bin/"sl-viewer"
  end
end
