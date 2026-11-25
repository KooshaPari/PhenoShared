.PHONY: all build test lint format clean

# Default target
all: test

# Build the project
build:
	go build -v ./...

# Run tests
test:
	go test -v -race ./...

# Run tests with coverage
test-cover:
	go test -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

# Run linter
lint:
	golangci-lint run ./...

# Format code
format:
	go fmt ./...
	gofmt -s -w .

# Run go vet
vet:
	go vet ./...

# Clean build artifacts
clean:
	rm -rf bin/
	rm -f coverage.out coverage.html

# Run all checks (CI pipeline)
ci: format vet lint test

# Install dependencies
deps:
	go mod download
	go mod verify

# Generate documentation
doc:
	godoc -http=:6060 &

# Security audit
security:
	go run golang.org/x/vulncheck/cmd/govulncheck@latest ./...
