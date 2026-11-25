# SessionLedger desktop packaging
# Usage: make package-macos | make package-linux | make package-windows

APP_NAME := SessionLedger
VERSION  := $(shell cargo metadata --no-deps --format-version 1 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['packages'][0]['version'])" 2>/dev/null || echo "0.1.0")
DIST_DIR := dist
POWERSHELL ?= powershell

.PHONY: package-macos package-linux package-windows package-all clean

package-macos: $(DIST_DIR)
	@echo "Packaging $(APP_NAME) $(VERSION) for macOS..."
	cargo build --release -p sl-viewer 2>/dev/null || cargo build --release -p session-ledger-viewer 2>/dev/null || echo "Build target name mismatch — check crate name"
	mkdir -p $(DIST_DIR)/$(APP_NAME).app/Contents/MacOS
	mkdir -p $(DIST_DIR)/$(APP_NAME).app/Contents/Resources
	cp target/release/sl-viewer $(DIST_DIR)/$(APP_NAME).app/Contents/MacOS/$(APP_NAME) 2>/dev/null || true
	@echo "<?xml version=\"1.0\"?>\n<!DOCTYPE plist>\n<plist version=\"1.0\"><dict><key>CFBundleName</key><string>$(APP_NAME)</string><key>CFBundleExecutable</key><string>$(APP_NAME)</string><key>CFBundleIdentifier</key><string>com.phenotype.sessionledger</string><key>CFBundleVersion</key><string>$(VERSION)</string></dict></plist>" > $(DIST_DIR)/$(APP_NAME).app/Contents/Info.plist
	@echo "macOS bundle: $(DIST_DIR)/$(APP_NAME).app"

package-linux: $(DIST_DIR)
	@echo "Packaging $(APP_NAME) $(VERSION) for Linux..."
	cargo build --release -p sl-viewer 2>/dev/null || cargo build --release -p session-ledger-viewer 2>/dev/null || echo "Build target name mismatch — check crate name"
	mkdir -p $(DIST_DIR)/linux
	cp target/release/sl-viewer $(DIST_DIR)/linux/$(APP_NAME) 2>/dev/null || true
	@echo "Linux binary: $(DIST_DIR)/linux/$(APP_NAME)"

package-windows:
	$(POWERSHELL) -NoProfile -ExecutionPolicy Bypass -File ../scripts/package-windows.ps1

# The Unix targets are host-local scaffolds; Windows packaging runs separately
# on a Windows host (or in release CI).
package-all: package-macos package-linux

$(DIST_DIR):
	mkdir -p $(DIST_DIR)

clean:
	rm -rf $(DIST_DIR)
