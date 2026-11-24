package adapters

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// RestAdapter handles HTTP requests
type RestAdapter struct {
	mux *http.ServeMux
}

// NewRestAdapter creates a new REST adapter
func NewRestAdapter() *RestAdapter {
	return &RestAdapter{
		mux: http.NewServeMux(),
	}
}

// Handle registers a route handler
func (a *RestAdapter) Handle(method, path string, handler http.HandlerFunc) {
	a.mux.HandleFunc(path, func(w http.ResponseWriter, r *http.Request) {
		if r.Method != method {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handler(w, r)
	})
}

// ServeHTTP implements http.Handler
func (a *RestAdapter) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	a.mux.ServeHTTP(w, r)
}

// RestRequest represents an HTTP request
type RestRequest struct {
	Method      string
	Path        string
	Headers     map[string]string
	Body        json.RawMessage
	QueryParams map[string]string
	PathParams  map[string]string
}

// RestResponse represents an HTTP response
type RestResponse struct {
	Status  int
	Headers map[string]string
	Body    any
	Error   *RestError
}

// RestError represents a REST error
type RestError struct {
	Code    string      `json:"code"`
	Message string      `json:"message"`
	Details interface{} `json:"details,omitempty"`
}

// NewRestError creates a new REST error
func NewRestError(code, message string) *RestError {
	return &RestError{Code: code, Message: message}
}

// WithDetails adds details to the error
func (e *RestError) WithDetails(details interface{}) *RestError {
	e.Details = details
	return e
}

// WriteJSON writes a JSON response
func WriteJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(data); err != nil {
		http.Error(w, fmt.Sprintf("failed to encode response: %v", err), http.StatusInternalServerError)
	}
}

// WriteError writes an error response
func WriteError(w http.ResponseWriter, status int, err *RestError) {
	WriteJSON(w, status, map[string]interface{}{
		"error": err,
	})
}

// ParseBody parses the request body into the target type
func ParseBody[T any](r *http.Request) (*T, error) {
	var body T
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		return nil, fmt.Errorf("failed to parse body: %w", err)
	}
	return &body, nil
}

// QueryParam gets a query parameter
func QueryParam(r *http.Request, name string) string {
	return r.URL.Query().Get(name)
}

// PathParam gets a path parameter
func PathParam(r *http.Request, name string) string {
	return r.Context().Value("path." + name).(string)
}
