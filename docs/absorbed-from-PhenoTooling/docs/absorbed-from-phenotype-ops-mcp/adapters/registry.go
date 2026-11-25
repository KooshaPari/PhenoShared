package adapters

import (
	"sort"
	"sync"

	"github.com/nanovms/ops-mcp/core"
)

// ToolRegistry stores tools behind a thread-safe map.
type ToolRegistry struct {
	mu    sync.RWMutex
	tools map[string]core.Tool
}

// NewToolRegistry constructs an empty tool registry.
func NewToolRegistry() *ToolRegistry {
	return &ToolRegistry{
		tools: make(map[string]core.Tool),
	}
}

// Register stores or replaces a tool definition by name.
func (r *ToolRegistry) Register(name string, tool core.Tool) {
	r.mu.Lock()
	defer r.mu.Unlock()

	r.tools[name] = tool
}

// Get loads a tool definition by name.
func (r *ToolRegistry) Get(name string) (core.Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	tool, ok := r.tools[name]
	return tool, ok
}

// Names returns the registered tool names in sorted order.
func (r *ToolRegistry) Names() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()

	names := make([]string, 0, len(r.tools))
	for name := range r.tools {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}
