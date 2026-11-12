package models

import (
	"encoding/json"
	"testing"
)

// TestAIProviderUnmarshalAcceptsCredentialSpellings pins the wire contract for
// the provider credential. AIProvider tags the field `api_key`, but clients
// have shipped camelCase `apiKey`; encoding/json matches names exactly (case
// folding only covers names that are otherwise identical), so the camelCase
// value used to be dropped and the credential validated as empty.
func TestAIProviderUnmarshalAcceptsCredentialSpellings(t *testing.T) {
	cases := []struct {
		name string
		body string
		key  string
	}{
		{"canonical api_key", `{"modal":"gpt-4o","api_key":"k1"}`, "k1"},
		{"camelCase apiKey", `{"modal":"gpt-4o","apiKey":"k2"}`, "k2"},
		{"upper APIKey", `{"modal":"gpt-4o","APIKey":"k3"}`, "k3"},
		{"lower apikey", `{"modal":"gpt-4o","apikey":"k4"}`, "k4"},
		{"missing credential stays empty", `{"modal":"gpt-4o"}`, ""},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var provider AIProvider
			if err := json.Unmarshal([]byte(tc.body), &provider); err != nil {
				t.Fatalf("unmarshal %s: %v", tc.body, err)
			}
			if provider.APIKey != tc.key {
				t.Fatalf("APIKey = %q, want %q", provider.APIKey, tc.key)
			}
			if provider.Modal != "gpt-4o" {
				t.Fatalf("Modal = %q, want %q", provider.Modal, "gpt-4o")
			}
		})
	}
}

// TestAIProviderMarshalEmitsCanonicalSpelling keeps the outbound spelling
// stable: the backend always writes `api_key`, whichever spelling came in.
func TestAIProviderMarshalEmitsCanonicalSpelling(t *testing.T) {
	payload, err := json.Marshal(AIProvider{Modal: "gpt-4o", APIKey: "secret"})
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var decoded map[string]string
	if err := json.Unmarshal(payload, &decoded); err != nil {
		t.Fatalf("unmarshal marshalled value: %v", err)
	}
	if decoded["api_key"] != "secret" {
		t.Fatalf("marshalled %s, want an api_key field", payload)
	}
	if _, drifted := decoded["apiKey"]; drifted {
		t.Fatalf("marshalled %s, must not emit camelCase apiKey", payload)
	}
}

// TestLLMProviderLookupIsCaseInsensitive covers the second half of the casing
// bug: the providers map key arrived as "openAI" while the handler looked up
// "openai", so the entry was missed even when the credential decoded correctly.
func TestLLMProviderLookupIsCaseInsensitive(t *testing.T) {
	llm := LLM{
		Provider: "openAI",
		Providers: map[string]AIProvider{
			"openAI": {Modal: "gpt-4o", APIKey: "sk-drifted"},
		},
	}

	provider, ok := llm.ProviderKey("openai")
	if !ok {
		t.Fatal("ProviderKey(\"openai\") did not find the \"openAI\" entry")
	}
	if provider.APIKey != "sk-drifted" {
		t.Fatalf("APIKey = %q, want %q", provider.APIKey, "sk-drifted")
	}

	key, entry, ok := llm.ProviderEntry("OpenAI")
	if !ok {
		t.Fatalf("ProviderEntry(\"OpenAI\") = (%q, %v, %v), want a hit", key, entry, ok)
	}
	if key != "openAI" {
		t.Fatalf("ProviderEntry key = %q, want the stored key %q", key, "openAI")
	}
	if entry.APIKey != "sk-drifted" {
		t.Fatalf("ProviderEntry APIKey = %q, want %q", entry.APIKey, "sk-drifted")
	}

	if _, ok := llm.ProviderKey("anthropic"); ok {
		t.Fatal("ProviderKey(\"anthropic\") matched an unrelated provider")
	}
}

// TestLLMProvidersRoundTripThroughJSON covers the gorm serializer path: the
// map is stored as JSON, so the tolerant decode must also survive a
// marshal/unmarshal round trip without losing the credential.
func TestLLMProvidersRoundTripThroughJSON(t *testing.T) {
	original := LLM{
		Provider: "openai",
		Providers: map[string]AIProvider{
			"openai": {Modal: "gpt-4o", APIKey: "sk-round-trip"},
		},
	}

	payload, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var restored LLM
	if err := json.Unmarshal(payload, &restored); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	provider, ok := restored.ProviderKey("openai")
	if !ok {
		t.Fatalf("restored providers = %v, want an openai entry", restored.Providers)
	}
	if provider.APIKey != "sk-round-trip" {
		t.Fatalf("APIKey = %q, want %q", provider.APIKey, "sk-round-trip")
	}
}
