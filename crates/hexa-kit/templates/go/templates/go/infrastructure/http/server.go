package adapters

import (
	"net/http"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"

	"{{ module_path }}/application/commands"
	"{{ module_path }}/domain/ports/inbound"
)

func NewEchoServer(service inbound.UseCase) *echo.Echo {
	e := echo.New()

	// Middleware
	e.Use(middleware.Logger())
	e.Use(middleware.Recover())
	e.Use(middleware.CORS())

	// Health check
	e.GET("/health", healthCheck)

	// API routes
	api := e.Group("/api/v1")
	RegisterHandlers(api, service)

	return e
}

// healthCheck returns server health status
func healthCheck(c echo.Context) error {
	return c.JSON(http.StatusOK, map[string]string{
		"status": "healthy",
	})
}
