package main

import (
	"flag"
	"log"
	"os"
	"path/filepath"

	"github.com/netweave/netweave/internal/ui"
)

const (
	defaultPort = 8080
)

func main() {
	
	port := flag.Int("port", defaultPort, "Port to run the server on")
	flag.Parse()

	
	execPath, err := os.Executable()
	if err != nil {
		log.Fatalf("Error getting executable path: %v", err)
	}
	execDir := filepath.Dir(execPath)
	staticDir := filepath.Join(execDir, "web", "static")

	
	if _, err := os.Stat(staticDir); os.IsNotExist(err) {
		
		cwd, err := os.Getwd()
		if err != nil {
			log.Fatalf("Error getting current directory: %v", err)
		}
		staticDir = filepath.Join(cwd, "web", "static")
		if _, err := os.Stat(staticDir); os.IsNotExist(err) {
			log.Fatalf("Static directory not found: %s", staticDir)
		}
	}

	log.Printf("Using static directory: %s", staticDir)

	
	server := ui.NewUIServer(*port, staticDir)
	
	
	log.Printf("Starting NetWeave on port %d...", *port)
	err = server.Start()
	if err != nil {
		log.Fatalf("Error starting server: %v", err)
	}
}
