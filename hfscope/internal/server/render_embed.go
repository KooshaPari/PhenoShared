package server

import (
	"net/http"

	"github.com/<REDACTED>/hfscope/internal/server/templ"
	"github.com/<REDACTED>/hfscope/internal/views"
)

func renderEmbedResults(w http.ResponseWriter, r *http.Request, data views.PageData) error {
	return templ.EmbedResults(data).Render(r.Context(), w)
}

func renderEmbedModel(w http.ResponseWriter, r *http.Request, data views.PageData) error {
	return templ.EmbedModel(data).Render(r.Context(), w)
}
