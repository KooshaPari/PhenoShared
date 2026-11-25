// Package cloud — Utility functions for cloud providers.
package cloud

import "time"

// parseRFC3339OrNow parses an RFC3339 timestamp string, returning current time if parsing fails.
func parseRFC3339OrNow(s string) time.Time {
	if s == "" {
		return time.Now()
	}
	t, err := time.Parse(time.RFC3339, s)
	if err != nil {
		return time.Now()
	}
	return t
}
