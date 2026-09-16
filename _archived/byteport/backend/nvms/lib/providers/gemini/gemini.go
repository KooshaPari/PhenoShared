package gemini

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	lib "nvms/lib/providers"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
)

const geminiEndpoint = "https://generativelanguage.googleapis.com/v1beta/models"

type geminiMessage struct {
	Role  string `json:"role"`
	Parts []struct {
		Text string `json:"text"`
	} `json:"parts"`
}

type geminiChatRequest struct {
	Contents []geminiMessage `json:"contents"`
}

type geminiCandidate struct {
	Content struct {
		Parts []struct {
			Text string `json:"text"`
		} `json:"parts"`
	} `json:"content"`
}

type geminiChatResponse struct {
	Candidates []geminiCandidate `json:"candidates"`
}

func RequestChatCompletion(reqBody lib.ChatRequest, key string, modal string) (string, error) {
	// Construct the full endpoint with API key
	endpoint := fmt.Sprintf("%s/%s:generateContent?key=%s", geminiEndpoint, modal, key)

	// Build the request body
	reqBase := geminiChatRequest{
		Contents: []geminiMessage{
			{
				Role: "user",
				Parts: []struct {
					Text string `json:"text"`
				}{
					{Text: reqBody.Prompt},
				},
			},
		},
	}

	jsonBody, err := json.Marshal(reqBase)
	if err != nil {
		return "", fmt.Errorf("error marshaling request: %v", err)
	}

	req, err := http.NewRequest("POST", endpoint, bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", fmt.Errorf("error creating request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := spinhttp.Send(req)
	if err != nil {
		return "", fmt.Errorf("error sending request: %v", err)
	}
	defer resp.Body.Close()

	var response geminiChatResponse
	fmt.Printf("Gemini Response: %v\n", resp)
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return "", fmt.Errorf("error decoding response: %v", err)
	}
	fmt.Printf("Gemini Response: %v\n", response)

	if len(response.Candidates) == 0 {
		return "", fmt.Errorf("no response candidates returned")
	}

	if len(response.Candidates[0].Content.Parts) == 0 {
		return "", fmt.Errorf("no content in response")
	}

	return response.Candidates[0].Content.Parts[0].Text, nil
}
