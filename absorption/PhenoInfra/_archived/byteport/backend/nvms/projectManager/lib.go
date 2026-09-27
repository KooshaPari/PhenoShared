package projectManager

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"nvms/models"
)

type ProvisionerResponse struct {
	Nvms    string   `json:"nvmsFile"`
	Readme  string   `json:"Readme"`
	ZipBall []byte   `json:"zipball"`
	FileMap []string `json:"fileMap"`
}

func readBody(w http.ResponseWriter, r *http.Request) (models.Project, models.User, error) {
	var user models.User
	var project models.Project
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Error reading request body", http.StatusInternalServerError)
		return project, user, err
	}
	defer r.Body.Close()

	err = json.Unmarshal(body, &project)
	if err != nil {
		http.Error(w, "Error parsing JSON", http.StatusBadRequest)
		return project, user, err
	}

	user = project.User
	// sec 2
	if err := project.BeforeSave(); err != nil {
		http.Error(w, "Error saving project", http.StatusInternalServerError)
		return project, user, err
	}
	return project, user, nil
}
func ProvisionFiles(w http.ResponseWriter, r *http.Request, project models.Project) (string, string, []byte, []string, error) {
	var nvmsString string
	var readMeString string
	var codebase []byte
	var files []string
	reqBody, err := json.Marshal(project)
	if err != nil {
		http.Error(w, "Error parsing JSON", http.StatusBadRequest)
		return nvmsString, readMeString, codebase, files, err
	}
	req, err := http.NewRequest("GET", "/provision", bytes.NewReader(reqBody))
	if err != nil {
		http.Error(w, "Error creating request", http.StatusInternalServerError)
		return nvmsString, readMeString, codebase, files, err
	}
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil || http.StatusOK != resp.StatusCode {
		http.Error(w, "Error sending request", http.StatusInternalServerError)
		return nvmsString, readMeString, codebase, files, err
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "Error reading response body", http.StatusInternalServerError)
		return nvmsString, readMeString, codebase, files, err
	}
	var response ProvisionerResponse
	err = json.Unmarshal(body, &response)
	if err != nil {
		http.Error(w, "Error parsing JSON", http.StatusBadRequest)
		return nvmsString, readMeString, codebase, files, err
	}
	nvmsString = response.Nvms
	readMeString = response.Readme
	codebase = response.ZipBall
	files = response.FileMap
	return nvmsString, readMeString, codebase, files, nil
}
