# dagrun build and check targets.
#
# `make check` is the gate that runs before a commit: formatting, vet, the full
# test suite, and the template lint that keeps the shipped plans honest.

GO ?= go
NODE ?= node
TIMEOUT ?= 300s
# The commit a binary was built from. `go build` cannot know it, so `make build`
# stamps it in as build metadata: without this every binary reports 1.2.0 for
# the life of the 1.2 line and a bug report cannot name the commit behind it.
#
# A short SHA rather than `git describe --tags`: this repository's tags version
# other things, so describing against them reports `v0.3.10-129-g<sha>` for a
# module that calls itself 1.2.0. The module's own version stays in main.go,
# where the code that changes with it lives; only the identity is stamped.
COMMIT ?= $(shell sha=$$(git rev-parse --short=12 HEAD 2>/dev/null || echo unknown); \
	if [ -n "$$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then \
		echo "$$sha.dirty"; else echo "$$sha"; fi)
LDFLAGS ?= -X main.Commit=$(COMMIT)

.PHONY: build test test-scale test-ui fuzz lint fmt templates check

## build: a binary that reports the version it was built from. `bin/` is
## gitignored, so this never adds an artifact to the tree.
build:
	$(GO) build -ldflags "$(LDFLAGS)" -o bin/dagrun .

## test: the full suite, everything under the module.
test:
	$(GO) test -timeout $(TIMEOUT) ./...

## test-scale: the store's scale tests, which are behind a build tag.
test-scale:
	$(GO) test -tags scale -timeout 600s ./internal/store/

## test-ui: the viewer's script under a DOM shim. No browser, no screenshot:
## it asserts on the markup and panel content the viewer builds, not on pixels.
## Needs node (no network, no dependencies); skipped when node is absent.
test-ui:
	@command -v $(NODE) >/dev/null 2>&1 || { \
		echo "node not found; skipping the viewer UI test (npm-free by design)"; exit 0; \
	}
	$(NODE) internal/viz/ui/viewer_test.mjs

## fuzz: a short parse fuzz run, enough to catch a parser regression locally.
fuzz:
	$(GO) test -fuzz FuzzParse -fuzztime 30s ./internal/plan/

## lint: vet only; it never rewrites anything.
lint:
	$(GO) vet ./...

## fmt: fails when any file is not gofmt-clean. It never rewrites: formatting is
## a decision for the author, and a check that edits files cannot be trusted as
## a gate.
fmt:
	@unformatted="$$(gofmt -l .)"; \
	if [ -n "$$unformatted" ]; then \
		echo "gofmt needed on:"; echo "$$unformatted"; exit 1; \
	fi

## templates: every shipped plan against both linters, verbosely, so advisory
## findings (allowed but printed) stay visible.
templates:
	$(GO) test ./internal/plan/ -run Template -v

## check: the full gate.
check: fmt lint test test-ui templates
