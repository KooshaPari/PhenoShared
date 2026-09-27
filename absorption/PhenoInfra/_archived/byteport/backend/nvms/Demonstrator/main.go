package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"nvms/lib"
	"nvms/models"
	"strings"

	spinhttp "github.com/fermyon/spin-go-sdk/http"
)

func init() {
	spinhttp.Handle(func(w http.ResponseWriter, r *http.Request) {

		var user models.User
		var project *models.Project

		project, err := getRequestDetails(w, r)
		if err != nil {
			fmt.Println("err getting dets: ", err)
			http.Error(w, "Error Reading Request", http.StatusInternalServerError)
			return
		}
		//fmt.Println("Proj: ",project)
		fmt.Println("User: ", project.User.LLMConfig)
		user = project.User
		// decrypt portDets
		decryptedPortEndpoint, err := lib.DecryptSecret(user.Portfolio.RootEndpoint)
		if err != nil {
			fmt.Println("Error decrypting endpoint:", err)
			http.Error(w, "Error decrypting endpoint", http.StatusInternalServerError)
			return
		}
		decryptedPortKey, err := lib.DecryptSecret(user.Portfolio.APIKey)
		if err != nil {
			fmt.Println("Error decrypting key:", err)
			http.Error(w, "Error decrypting key", http.StatusInternalServerError)
			return
		}
		fmt.Println("Dets: " + decryptedPortEndpoint + " ||| " + decryptedPortKey)
		templateStruct, err := getTemplate(decryptedPortEndpoint, decryptedPortKey)
		// pull Portfolio API Format
		if err != nil {
			fmt.Println("error getting template: ", err)
			http.Error(w, "error getting template", http.StatusInternalServerError)
		}
		//fmt.Println("Struct : ", templateStruct)
		genRequest := generatePrompt(templateStruct, project)
		//fmt.Println("Prompt: ", genRequest)
		var credsObj models.LLM = user.LLMConfig
		if credsObj.Provider != "local" {
			decryptedOAI, err := lib.DecryptSecret(credsObj.Providers[credsObj.Provider].APIKey)
			if err != nil {
				fmt.Println("Error decrypting key:", err)
				http.Error(w, "Error decrypting key", http.StatusInternalServerError)
				return
			}

			provider := credsObj.Providers[credsObj.Provider]
			provider.APIKey = decryptedOAI
			credsObj.Providers[credsObj.Provider] = provider
		}
		filledObject, err := requestFilledTemplate(genRequest, templateStruct, credsObj)
		// Generate Response (hand info above to ai langchain)
		if err != nil {
			fmt.Println("Bad Prompt Req: ", err)
			http.Error(w, "Bad Prompt Req", http.StatusInternalServerError)
			return
		}
		fmt.Println("Success , OBJ: ", filledObject)
		err = sendToPortfolio(filledObject, decryptedPortEndpoint, decryptedPortKey)
		if err != nil {
			fmt.Println("Error sending to portfolio: ", err)
			http.Error(w, "Error sending to portfolio", http.StatusInternalServerError)
			return
		}
		// post to portfolio
		// return\
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintln(w, "Hello Fermyon!")
	})
}

func sendToPortfolio(object string, endpoint string, key string) error {
	// Clean endpoint and properly join path
	uri := strings.TrimRight(endpoint, "/") + "/byteport"
	var body *bytes.Buffer
	// Check if object is already JSON string
	var jsonData interface{}
	if err := json.Unmarshal([]byte(object), &jsonData); err != nil {
		// If not valid JSON, try to marshal it

		Reqbytes, err := json.Marshal(object)
		if err != nil {
			return fmt.Errorf("error marshaling object: %v", err)
		}
		body = bytes.NewBuffer(Reqbytes)
		err = json.Indent(body, []byte(object), "", "")
		if err != nil {
			return fmt.Errorf("error formatting JSON: %v", err)
		}
		fmt.Println("Marshalled: ", body)
	} else {
		// If already JSON, use as is
		body = bytes.NewBuffer([]byte(object))
	}

	req, err := http.NewRequest("POST", uri, body)
	if err != nil {
		return fmt.Errorf("error building request: %v", err)
	}

	// Add necessary headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+key)

	fmt.Printf("Sending request to: %s\n", uri)
	resp, err := spinhttp.Send(req)
	if err != nil {
		return fmt.Errorf("error sending request: %v", err)
	}
	defer resp.Body.Close()

	// Check response status
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("unexpected status code %d: %s", resp.StatusCode, string(body))
	}

	fmt.Println("Successfully sent to portfolio")
	return nil
}
func generatePrompt(template string, project *models.Project) string {
	base := `Given a project template and project information, generate a filled portfolio project object.

Input format:
1. Template: A object with empty fields representing the portfolio project structure
2. Project info: Object containing details about the application being deployed

Rules:
Dummy Data should always be taking data from the given sample api, if inferring always strictly maintain format e.g for date or colors(hex to hex, etc)
1. For complex array fields (), use a single item following these priority rules:
   - If example data exists in the sample filled template, copy the first item's structure, for referential or date values if not calculable use the template value, else calculate your own. Date formats must be in same form as shown.
   - If no example exists, use appropriate dummy data
   

3. For technical references:
   - logo: Use technology's logo if available, otherwise placeholder
   - skills: Include main technologies used
   - descriptions: Deep description showing off features catering to both impressing users and potential employers
   - type: Map project type to standard categories (Website, Mobile App, CLI Tool, etc.)

4. For dates:
   - Use actual project dates when available
   - Default to current date for "from" if not specified

5. For metadata fields ():
   - Use provided info if available
   - Leave empty if not relevant
6. In General You're writing a portfolio entry, eccentuate the project's strengths and features, and make it appealing to potential employers or clients.
Sample API call (Filled Example with Unfilled template in template{} (do not include template attribute in response)):
%s

Project Information:

Name: %s
Description: %s
Platform: %s
Type: %s
AccessURL(Must include for User access to project): %s 
Readme: 
%s
User Information:
Name: %s
 
Expected response: A filled template object matching the required structure. String-Representable Object usable as response body without modification`
	prompt := fmt.Sprintf(base, template, project.Name, project.Description, project.Platform, project.Type, project.AccessURL, project.Readme, project.User.Name)
	return prompt
}
func getTemplate(endpoint string, key string) (string, error) {
	uri := strings.TrimRight(endpoint, "/") + "/byteport"

	req, err := http.NewRequest("GET", uri, nil)
	if err != nil {
		return "", fmt.Errorf("error building request: %v", err)
	}

	req.Header.Set("Authorization", "Bearer "+key)

	resp, err := spinhttp.Send(req)
	if err != nil {
		return "", fmt.Errorf("error sending request: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("error reading response body: %v", err)
	}

	// Try to parse as is first
	var jsonTest interface{}
	if err := json.Unmarshal(body, &jsonTest); err == nil {
		// It's already valid JSON
		return string(body), nil
	}

	// If not valid JSON, try base64 decode
	decoded, err := base64.StdEncoding.DecodeString(string(body))
	if err != nil {
		// If both attempts fail, return original with error context
		return "", fmt.Errorf("response is neither valid JSON nor base64: %v", err)
	}

	return string(decoded), nil
}
func getRequestDetails(w http.ResponseWriter, r *http.Request) (*models.Project, error) {
	fmt.Println("Getting Template Dets")
	var project models.Project
	body, err := io.ReadAll(r.Body)
	if err != nil {
		fmt.Println("Error reading request body: ", err)
		http.Error(w, "Error reading request body", http.StatusInternalServerError)
		return nil, err
	}
	defer r.Body.Close()
	fmt.Println("Parsing JSON...")
	err = json.Unmarshal(body, &project)
	if err != nil {
		http.Error(w, "Error parsing JSON", http.StatusBadRequest)
		return nil, err
	}
	return &project, nil
}
func requestFilledTemplate(prompt string, strStruct string, config models.LLM) (string, error) {

	response, err := lib.RequestCompletion(prompt, strStruct, config)
	if err != nil {
		return "", fmt.Errorf("error getting chat completion: %v", err)
	}
	return response, nil
}
func main() {}
