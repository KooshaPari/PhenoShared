package adapters

import (
	"errors"
	"net/http"

	"github.com/labstack/echo/v4"

	"{{ module_path }}/application/commands"
	"{{ module_path }}/domain/errors"
	"{{ module_path }}/domain/ports/inbound"
)

// Handler holds the HTTP handlers
type Handler struct {
	service inbound.UseCase
}

// RegisterHandlers registers all HTTP handlers
func RegisterHandlers(g *echo.Group, service inbound.UseCase) {
	h := &Handler{service: service}

	g.POST("/examples", h.Create)
	g.GET("/examples", h.List)
	g.GET("/examples/:id", h.GetByID)
	g.PUT("/examples/:id", h.Update)
	g.DELETE("/examples/:id", h.Delete)
}

// Create handles POST /api/v1/examples
func (h *Handler) Create(c echo.Context) error {
	var input inbound.CreateInput
	if err := c.Bind(&input); err != nil {
		return c.JSON(http.StatusBadRequest, ErrorResponse{Error: "invalid request body"})
	}

	entity, err := h.service.Create(c.Request().Context(), input)
	if err != nil {
		return handleError(c, err)
	}

	return c.JSON(http.StatusCreated, entity)
}

// List handles GET /api/v1/examples
func (h *Handler) List(c echo.Context) error {
	entities, err := h.service.List(c.Request().Context())
	if err != nil {
		return handleError(c, err)
	}

	return c.JSON(http.StatusOK, entities)
}

// GetByID handles GET /api/v1/examples/:id
func (h *Handler) GetByID(c echo.Context) error {
	id := c.Param("id")
	if id == "" {
		return c.JSON(http.StatusBadRequest, ErrorResponse{Error: "id is required"})
	}

	entity, err := h.service.GetByID(c.Request().Context(), id)
	if err != nil {
		return handleError(c, err)
	}

	return c.JSON(http.StatusOK, entity)
}

// Update handles PUT /api/v1/examples/:id
func (h *Handler) Update(c echo.Context) error {
	id := c.Param("id")
	if id == "" {
		return c.JSON(http.StatusBadRequest, ErrorResponse{Error: "id is required"})
	}

	var input inbound.UpdateInput
	if err := c.Bind(&input); err != nil {
		return c.JSON(http.StatusBadRequest, ErrorResponse{Error: "invalid request body"})
	}
	input.ID = id

	entity, err := h.service.Update(c.Request().Context(), input)
	if err != nil {
		return handleError(c, err)
	}

	return c.JSON(http.StatusOK, entity)
}

// Delete handles DELETE /api/v1/examples/:id
func (h *Handler) Delete(c echo.Context) error {
	id := c.Param("id")
	if id == "" {
		return c.JSON(http.StatusBadRequest, ErrorResponse{Error: "id is required"})
	}

	if err := h.service.Delete(c.Request().Context(), id); err != nil {
		return handleError(c, err)
	}

	return c.NoContent(http.StatusNoContent)
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error string `json:"error"`
}

func handleError(c echo.Context, err error) error {
	var domainErr *errors.DomainError
	if errors.As(err, &domainErr) {
		switch {
		case errors.IsNotFound(err):
			return c.JSON(http.StatusNotFound, ErrorResponse{Error: domainErr.Message})
		case errors.IsValidation(err):
			return c.JSON(http.StatusBadRequest, ErrorResponse{Error: domainErr.Message})
		case errors.IsInternal(err):
			return c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
		}
	}

	if errors.Is(err, errors.ErrInvalidInput) {
		return c.JSON(http.StatusBadRequest, ErrorResponse{Error: "invalid input"})
	}

	return c.JSON(http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
}
