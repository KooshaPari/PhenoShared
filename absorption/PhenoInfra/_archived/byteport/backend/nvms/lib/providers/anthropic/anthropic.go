package anthropic

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	lib "nvms/lib/providers"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
)

const anthroEndpoint = "https://api.anthropic.com/v1/chat/completions"

type anthMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type anthChatRequest struct {
	Model    string        `json:"model"`
	Messages []anthMessage `json:"messages"`
	stream   bool          `json:"stream"`
	//ResponseFormat FormatSchema `json:"response_format"`
}
type anthChoice struct {
	Message struct {
		Content string `json:"content"`
	} `json:"message"`
}

type anthChatResponse struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	Choices []struct {
		Index   int         `json:"index"`
		Message anthMessage `json:"message"`
	} `json:"choices"`
}

func RequestChatCompletion(reqBody lib.ChatRequest, key string, modal string) (string, error) {

	reqBase := anthChatRequest{
		Model: modal,
		Messages: []anthMessage{
			{
				Role:    "user",
				Content: reqBody.Prompt,
			},
		},
		stream: false,
	}

	jsonBody, err := json.Marshal(reqBase)
	if err != nil {
		return "", fmt.Errorf("error marshaling request: %v", err)
	}

	req, err := http.NewRequest("POST", anthroEndpoint, bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", fmt.Errorf("error creating request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+key)

	resp, err := spinhttp.Send(req)
	if err != nil {
		return "", fmt.Errorf("error sending request: %v", err)
	}
	defer resp.Body.Close()

	var response anthChatResponse
	fmt.Println("Response: ", resp)
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return "", fmt.Errorf("error decoding response: %v", err)
	}
	fmt.Println("Response: ", response)

	if len(response.Choices) == 0 {
		return "", fmt.Errorf("no response choices returned")
	}

	return response.Choices[0].Message.Content, nil
}
