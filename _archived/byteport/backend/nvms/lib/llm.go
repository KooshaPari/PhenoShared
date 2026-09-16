package lib

import (
	"errors"
	"fmt"
	lib "nvms/lib/providers"
	"nvms/lib/providers/anthropic"
	"nvms/lib/providers/gemini"
	"nvms/lib/providers/local"
	"nvms/lib/providers/openai"
	"nvms/models"
)

// Provider-specific errors
var (
	ErrProviderNotImplemented = errors.New("provider not implemented")
)

const (
	ProviderOpenAI    = "openai"
	ProviderAnthropic = "anthropic"
	ProviderGemini    = "gemini" // Gemini provider implemented (lib/providers/gemini/gemini.go)
	ProviderLocal     = "local"
)

func RequestCompletion(prompt string, strStruct string, config models.LLM) (string, error) {
	fmt.Println("Strcut: ", strStruct)
	var response string
	var err error

	reqBody := lib.ChatRequest{
		Model:     config.Providers[config.Provider].Modal,
		Prompt:    prompt,
		ObjStruct: strStruct,
	}

	switch config.Provider {
	case ProviderOpenAI:
		fmt.Println("OpenAI")
		response, err = openai.RequestChatCompletion(reqBody, config.Providers[config.Provider].APIKey, config.Providers[config.Provider].Modal)

	case ProviderAnthropic:
		fmt.Println("Anthropic")
		response, err = anthropic.RequestChatCompletion(reqBody, config.Providers[config.Provider].APIKey, config.Providers[config.Provider].Modal)

	case ProviderGemini:
		fmt.Println("Gemini")
		response, err = gemini.RequestChatCompletion(reqBody, config.Providers[config.Provider].APIKey, config.Providers[config.Provider].Modal)

	case ProviderLocal:
		fmt.Println("Local")
		response, err = local.RequestCompletion(reqBody)

	default:
		return "", fmt.Errorf("unknown provider: %s", config.Provider)
	}

	if err != nil {
		return "", fmt.Errorf("error sending request: %v", err)
	}
	return response, nil
}
