#!/bin/bash
echo "NetWeave Traffic Simulation Installer"
echo "====================================="
echo


if ! command -v go &> /dev/null; then
    echo "Error: Go is not installed or not in PATH"
    echo "Please install Go 1.18 or higher from https://golang.org/dl/"
    exit 1
fi


GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
GO_MAJOR=$(echo $GO_VERSION | cut -d. -f1)
GO_MINOR=$(echo $GO_VERSION | cut -d. -f2)

if [ "$GO_MAJOR" -lt 1 ] || ([ "$GO_MAJOR" -eq 1 ] && [ "$GO_MINOR" -lt 18 ]); then
    echo "Error: Go version 1.18 or higher is required"
    echo "Current version: $GO_VERSION"
    echo "Please upgrade Go from https://golang.org/dl/"
    exit 1
fi

echo "Go version $GO_VERSION detected"


mkdir -p web/static/saved


echo "Downloading dependencies..."
go mod download
if [ $? -ne 0 ]; then
    echo "Error: Failed to download dependencies"
    exit 1
fi


echo "Building NetWeave..."
go build -o netweave ./cmd/netweave
if [ $? -ne 0 ]; then
    echo "Error: Build failed"
    exit 1
fi

echo "NetWeave built successfully!"
echo


echo "Installation complete!"
echo "To run NetWeave, use: ./netweave --port=8080"
echo "Then open your browser to: http://localhost:8080/main.html"
echo
echo "Thank you for installing NetWeave Traffic Simulation!"
