package application

import "time"

// DTO represents a Data Transfer Object
type DTO[T any] struct {
	Data      T          `json:"data"`
	Meta      DtoMeta    `json:"meta,omitempty"`
	Paginated *Paginated `json:"paginated,omitempty"`
}

// NewDTO creates a new DTO
func NewDTO[T any](data T) *DTO[T] {
	return &DTO[T]{
		Data: data,
		Meta: DtoMeta{
			Timestamp: time.Now(),
		},
	}
}

// DtoMeta contains metadata for DTOs
type DtoMeta struct {
	Version   string    `json:"version,omitempty"`
	Timestamp time.Time `json:"timestamp"`
	RequestID string    `json:"request_id,omitempty"`
}

// Paginated contains pagination information
type Paginated struct {
	Page       int   `json:"page"`
	PageSize   int   `json:"page_size"`
	Total      int64 `json:"total"`
	TotalPages int   `json:"total_pages"`
}

// NewPaginated creates a new paginated result
func NewPaginated(page, pageSize int, total int64) *Paginated {
	totalPages := int(total) / pageSize
	if int(total)%pageSize > 0 {
		totalPages++
	}
	return &Paginated{
		Page:       page,
		PageSize:   pageSize,
		Total:      total,
		TotalPages: totalPages,
	}
}

// Command represents a command DTO
type Command struct {
	Type     string                 `json:"type"`
	Payload  map[string]interface{} `json:"payload"`
	Metadata map[string]string      `json:"metadata,omitempty"`
}

// NewCommand creates a new command
func NewCommand(commandType string, payload map[string]interface{}) *Command {
	return &Command{
		Type:     commandType,
		Payload:  payload,
		Metadata: make(map[string]string),
	}
}

// WithMetadata adds metadata to the command
func (c *Command) WithMetadata(key, value string) *Command {
	c.Metadata[key] = value
	return c
}

// Query represents a query DTO
type Query struct {
	Type       string        `json:"type"`
	Filters    []QueryFilter `json:"filters,omitempty"`
	Pagination *Pagination   `json:"pagination,omitempty"`
}

// NewQuery creates a new query
func NewQuery(queryType string) *Query {
	return &Query{
		Type:       queryType,
		Filters:    make([]QueryFilter, 0),
		Pagination: nil,
	}
}

// WithFilter adds a filter to the query
func (q *Query) WithFilter(filter QueryFilter) *Query {
	q.Filters = append(q.Filters, filter)
	return q
}

// QueryFilter represents a query filter
type QueryFilter struct {
	Field    string      `json:"field"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
}

// Pagination represents pagination input
type Pagination struct {
	Page     int `json:"page"`
	PageSize int `json:"page_size"`
}

// NewPagination creates a new pagination
func NewPagination(page, pageSize int) *Pagination {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	}
	if pageSize > 100 {
		pageSize = 100
	}
	return &Pagination{
		Page:     page,
		PageSize: pageSize,
	}
}
