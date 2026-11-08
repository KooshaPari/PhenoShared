package plugins

// Manifest represents a plugin manifest file.
// Used for declarative plugin configuration.
//
// The struct supports two complementary shapes:
//   - Multi-plugin loader shape: Version + Plugins []ManifestPlugin
//     (used by registry/loader code that discovers and boots a fleet)
//   - Single-plugin author shape: Name + Description + Author + License
//     + Tags + Requires + Provides (used by adapter/embedding authors
//     that publish one plugin's metadata)
//
// The fields are additive; existing loader callers that only set
// Version + Plugins continue to compile and behave the same.
type Manifest struct {
	// Version is the manifest version.
	Version string `json:"manifest_version"`

	// Plugins contains the list of plugins to load (multi-plugin shape).
	Plugins []ManifestPlugin `json:"plugins"`

	// Name identifies the plugin (single-plugin shape).
	Name string `json:"name,omitempty"`

	// Description is a human-readable description of the plugin.
	Description string `json:"description,omitempty"`

	// Author identifies the plugin author.
	Author string `json:"author,omitempty"`

	// License is the plugin license (e.g. "Apache-2.0").
	License string `json:"license,omitempty"`

	// Tags categorize the plugin (e.g. "embeddings", "auth", "cache").
	Tags []string `json:"tags,omitempty"`

	// Requires maps plugin requirements (e.g. ports, capabilities) to versions.
	Requires map[string]string `json:"requires,omitempty"`

	// Provides lists ports/capabilities this plugin offers.
	Provides []string `json:"provides,omitempty"`
}

// ManifestPlugin represents a plugin in the manifest.
type ManifestPlugin struct {
	// ID is the unique identifier of the plugin.
	ID string `json:"id"`

	// Type is the type of the plugin.
	Type PluginType `json:"type"`

	// Source is the source of the plugin (file path, URL, or registry reference).
	Source string `json:"source"`

	// Version is the version constraint.
	Version string `json:"version,omitempty"`

	// Enabled indicates if the plugin is enabled.
	Enabled bool `json:"enabled,omitempty"`

	// Config contains the plugin configuration.
	Config map[string]any `json:"config,omitempty"`

	// Dependencies are the plugin dependencies.
	Dependencies []Dependency `json:"dependencies,omitempty"`

	// Priority is the plugin priority for loading order.
	Priority int `json:"priority,omitempty"`
}

// DefaultManifest returns a default manifest structure.
func DefaultManifest() *Manifest {
	return &Manifest{
		Version: "1.0.0",
		Plugins: []ManifestPlugin{},
	}
}

// Validate validates the manifest structure.
func (m *Manifest) Validate() error {
	if m.Version == "" {
		m.Version = "1.0.0"
	}

	for i, p := range m.Plugins {
		if p.ID == "" {
			return &ManifestError{
				Field:   "plugins",
				Index:   i,
				Message: "plugin ID is required",
			}
		}
		if p.Type == "" {
			return &ManifestError{
				Field:   "type",
				Index:   i,
				Message: "plugin type is required",
			}
		}
	}

	return nil
}

// ManifestError represents a manifest validation error.
type ManifestError struct {
	Field   string
	Index   int
	Message string
}

func (e *ManifestError) Error() string {
	if e.Index >= 0 {
		return "manifest: " + e.Field + "[" + string(rune(e.Index)) + "]: " + e.Message
	}
	return "manifest: " + e.Field + ": " + e.Message
}
