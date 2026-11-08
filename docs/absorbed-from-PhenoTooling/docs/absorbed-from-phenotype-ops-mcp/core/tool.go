package core

import "encoding/json"

// ToolContent is a strongly typed content item emitted by a tool result.
type ToolContent struct {
	Type string          `json:"type"`
	Text string          `json:"text,omitempty"`
	Data json.RawMessage `json:"data,omitempty"`
}

// ToolResult is the typed envelope for tool output content.
type ToolResult struct {
	Content []ToolContent `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// MarshalJSON keeps ToolResult serialization explicit and strongly typed.
func (tr ToolResult) MarshalJSON() ([]byte, error) {
	type toolResultJSON struct {
		Content []ToolContent `json:"content"`
		IsError bool          `json:"isError,omitempty"`
	}

	content := tr.Content
	if content == nil {
		content = []ToolContent{}
	}

	return json.Marshal(toolResultJSON{
		Content: content,
		IsError: tr.IsError,
	})
}

// NewTextResult constructs a successful text-only tool result.
func NewTextResult(text string) ToolResult {
	return ToolResult{
		Content: []ToolContent{
			{
				Type: "text",
				Text: text,
			},
		},
	}
}

// NewErrorResult constructs an error tool result with a text payload.
func NewErrorResult(err error) ToolResult {
	message := ""
	if err != nil {
		message = err.Error()
	}

	result := NewTextResult(message)
	result.IsError = true
	return result
}
