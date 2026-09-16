package docslib

// Version is the current version
const Version = "0.1.0"

// Doc represents a parsed documentation document
type Doc struct {
	Title   string
	Content []Node
	Meta    Metadata
}

// Metadata contains document metadata
type Metadata struct {
	Author   string
	Date     string
	Version  string
	Language string
	Template string
}

// Node represents a document node
type Node interface {
	NodeType() string
}

// TextNode represents text content
type TextNode struct {
	Content string
}

func (TextNode) NodeType() string {
	return "text"
}

// HeadingNode represents a heading
type HeadingNode struct {
	Level   int
	Content string
	ID      string
}

func (HeadingNode) NodeType() string {
	return "heading"
}

// CodeNode represents a code block
type CodeNode struct {
	Language string
	Content  string
}

func (CodeNode) NodeType() string {
	return "code"
}

// ListNode represents a list
type ListNode struct {
	Ordered bool
	Items   [][]Node
}

func (ListNode) NodeType() string {
	return "list"
}

// TableNode represents a table
type TableNode struct {
	Headers []string
	Rows    [][]string
}

func (TableNode) NodeType() string {
	return "table"
}

// Parser is the interface for document parsers
type Parser interface {
	Parse(content string) (*Doc, error)
}

// Renderer is the interface for document renderers
type Renderer interface {
	Render(doc *Doc) (string, error)
}
