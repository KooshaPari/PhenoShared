package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"{{ module_path }}/application/commands"
	"{{ module_path }}/infrastructure/adapters/persistence"
	"{{ module_path }}/infrastructure/http"
)

func main() {
	// Initialize dependencies
	repo := persistence.NewInMemoryRepository()
	service := commands.NewService(repo)
	server := adapters.NewEchoServer(service)

	// Start server in goroutine
	go func() {
		addr := ":8080"
		log.Printf("Starting server on %s", addr)
		if err := server.Start(addr); err != nil {
			log.Printf("Server stopped: %v", err)
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exited")
}
