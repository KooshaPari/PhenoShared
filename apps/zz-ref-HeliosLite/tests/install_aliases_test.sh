#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
fixture="$(mktemp -d)"
trap 'rm -rf "$fixture"' EXIT

cp "$repo_root/install.sh" "$fixture/install.sh"
chmod +x "$fixture/install.sh"
mkdir -p "$fixture/fake-bin" "$fixture/install" "$fixture/stable-bin"

cat > "$fixture/fake-bin/cargo" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" > "$CARGO_ARGS_FILE"
mkdir -p target/release
printf '#!/usr/bin/env bash\necho "helioslite 2.13.21"\n' > target/release/helioslite
chmod +x target/release/helioslite
EOF
chmod +x "$fixture/fake-bin/cargo"

printf '#!/usr/bin/env bash\necho stable-forge\n' > "$fixture/stable-bin/forge"
chmod +x "$fixture/stable-bin/forge"
printf 'stable forge in shared install directory\n' > "$fixture/install/forge"
printf 'stable forge-dev target\n' > "$fixture/stable-forge-dev"
ln -s "$fixture/stable-forge-dev" "$fixture/install/forge-dev"

(
    cd "$fixture"
    PATH="$fixture/stable-bin:$fixture/fake-bin:$PATH" CARGO_ARGS_FILE="$fixture/cargo-args" \
        HELIOSLITE_INSTALL_DIR="$fixture/install" ./install.sh --local
)

test "$(cat "$fixture/cargo-args")" = "build --release --bin helioslite"
test -x "$fixture/install/helioslite"
test "$(cat "$fixture/install/forge")" = "stable forge in shared install directory"
test "$(cat "$fixture/stable-forge-dev")" = "stable forge-dev target"
test -L "$fixture/install/forge-dev"
test "$(PATH="$fixture/stable-bin:$fixture/install:$PATH" command -v forge)" = "$fixture/stable-bin/forge"
test "$(PATH="$fixture/stable-bin:$fixture/install:$PATH" forge)" = "stable-forge"

# Download installs must preserve regular files and symlinks, and must not
# introduce a forge command in an earlier PATH directory that shadows stable.
cat > "$fixture/fake-bin/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "$2" in
    *.sha256) shasum -a 256 "$DOWNLOAD_BINARY" > "$4" ;;
    *) cp "$DOWNLOAD_BINARY" "$4" ;;
esac
EOF
chmod +x "$fixture/fake-bin/curl"
for mode in regular symlink absent; do
    install_dir="$fixture/download-$mode"
    mkdir -p "$install_dir"
    case "$mode" in
        regular) cp "$fixture/stable-bin/forge" "$install_dir/forge" ;;
        symlink) ln -s "$fixture/stable-bin/forge" "$install_dir/forge" ;;
    esac
    test_path="$install_dir:$fixture/stable-bin:$fixture/fake-bin:$PATH"
    before="$(PATH="$test_path" command -v forge)"
    for compatibility_flag in '' --skip-forge; do
        PATH="$test_path" CARGO_ARGS_FILE="$fixture/cargo-args" \
            HELIOSLITE_INSTALL_DIR="$install_dir" \
            "$fixture/install.sh" --local ${compatibility_flag:+"$compatibility_flag"}
        test "$(cat "$fixture/cargo-args")" = "build --release --bin helioslite"
        test "$(PATH="$test_path" command -v forge)" = "$before"
        test "$(PATH="$test_path" forge)" = "stable-forge"
        test ! -e "$install_dir/forge-dev"
        PATH="$test_path" DOWNLOAD_BINARY="$fixture/target/release/helioslite" \
            HELIOSLITE_INSTALL_DIR="$install_dir" HELIOSLITE_TARGET=x86_64-apple-darwin \
            "$fixture/install.sh" 2.13.21 ${compatibility_flag:+"$compatibility_flag"}
        test "$(PATH="$test_path" command -v forge)" = "$before"
        test "$(PATH="$test_path" forge)" = "stable-forge"
        test ! -e "$install_dir/forge-dev"
        test -x "$install_dir/helioslite"
    done
    case "$mode" in
        regular) cmp "$fixture/stable-bin/forge" "$install_dir/forge" ;;
        symlink) test "$(readlink "$install_dir/forge")" = "$fixture/stable-bin/forge" ;;
        absent) test ! -e "$install_dir/forge" ;;
    esac
done
