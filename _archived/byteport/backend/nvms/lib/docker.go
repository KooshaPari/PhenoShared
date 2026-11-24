// lib/docker.go - Docker CLI management for BytePort Windows.
package lib

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"nvms/models"
)

type DockerManager struct {
	networkName string
	mutex       sync.RWMutex
}

type DockerInstanceInfo struct {
	ContainerID string `json:"container_id"`
	Name        string `json:"name"`
	Port        int    `json:"port"`
	Status      string `json:"status"`
	ProjectName string `json:"project_name"`
	ServiceName string `json:"service_name"`
	ImageTag    string `json:"image_tag"`
	InstanceID  string `json:"instance_id"`
	Region      string `json:"region"`
}

var dockerManagerInstance *DockerManager
var dockerManagerOnce sync.Once

func GetDockerManager() (*DockerManager, error) {
	var err error
	dockerManagerOnce.Do(func() {
		dockerManagerInstance, err = NewDockerManager()
	})
	return dockerManagerInstance, err
}

func NewDockerManager() (*DockerManager, error) {
	dm := &DockerManager{networkName: "byteport-network"}
	return dm, nil
}

func (dm *DockerManager) ensureNetwork() error {
	return nil
}

func (dm *DockerManager) CreateAndStartContainer(service models.Service, projectPath string) (*DockerInstanceInfo, error) {
	dm.mutex.Lock()
	defer dm.mutex.Unlock()

	imageTag := fmt.Sprintf("byteport-%s-%s:latest", service.ProjectName, service.Name)
	if err := dm.buildImage(projectPath, service.Path, imageTag, service); err != nil {
		return nil, fmt.Errorf("failed to prepare Docker image inputs: %w", err)
	}

	containerName := fmt.Sprintf("byteport-%s-%s", service.ProjectName, service.Name)
	return &DockerInstanceInfo{
		ContainerID: containerName,
		Name:        containerName,
		Port:        service.Port,
		Status:      "prepared",
		ProjectName: service.ProjectName,
		ServiceName: service.Name,
		ImageTag:    imageTag,
		InstanceID:  containerName,
		Region:      "local",
	}, nil
}

func (dm *DockerManager) removeExistingContainer(containerName string) {
}

func (dm *DockerManager) buildImage(projectPath, servicePath, imageTag string, service models.Service) error {
	fullServicePath := filepath.Join(projectPath, servicePath)
	dockerfilePath := filepath.Join(fullServicePath, "Dockerfile")
	if _, err := os.Stat(dockerfilePath); os.IsNotExist(err) {
		dockerfile := dm.generateDockerfile(fullServicePath, service)
		if err := os.WriteFile(dockerfilePath, []byte(dockerfile), 0644); err != nil {
			return fmt.Errorf("failed to create Dockerfile: %w", err)
		}
	}

	return dm.writeDockerCommandFile(fullServicePath, imageTag, service)
}

func (dm *DockerManager) generateDockerfile(servicePath string, service models.Service) string {
	if dm.fileExists(filepath.Join(servicePath, "package.json")) {
		return dm.generateNodeDockerfile(service.Port)
	}
	if dm.fileExists(filepath.Join(servicePath, "go.mod")) {
		return dm.generateGoDockerfile(service.Port)
	}
	if dm.fileExists(filepath.Join(servicePath, "requirements.txt")) {
		return dm.generatePythonDockerfile(service.Port)
	}
	if dm.fileExists(filepath.Join(servicePath, "Cargo.toml")) {
		return dm.generateRustDockerfile(service.Port)
	}
	return dm.generateNodeDockerfile(service.Port)
}

func (dm *DockerManager) generateNodeDockerfile(port int) string {
	return fmt.Sprintf(`FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE %d
CMD ["npm", "start"]`, port)
}

func (dm *DockerManager) generateGoDockerfile(port int) string {
	return fmt.Sprintf(`FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE %d
CMD ["./main"]`, port)
}

func (dm *DockerManager) generatePythonDockerfile(port int) string {
	return fmt.Sprintf(`FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE %d
CMD ["python", "app.py"]`, port)
}

func (dm *DockerManager) generateRustDockerfile(port int) string {
	return fmt.Sprintf(`FROM rust:1.70 AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/target/release/app .
EXPOSE %d
CMD ["./app"]`, port)
}

func (dm *DockerManager) StopContainer(containerID string) error {
	return nil
}

func (dm *DockerManager) RemoveContainer(containerID string) error {
	return nil
}

func (dm *DockerManager) GetContainerStatus(containerID string) (string, error) {
	return "prepared", nil
}

func (dm *DockerManager) ListProjectContainers(projectName string) ([]DockerInstanceInfo, error) {
	return []DockerInstanceInfo{}, nil
}

func (dm *DockerManager) fileExists(filename string) bool {
	_, err := os.Stat(filename)
	return !os.IsNotExist(err)
}

func (dm *DockerManager) Close() error {
	return nil
}

func (dm *DockerManager) writeDockerCommandFile(servicePath, imageTag string, service models.Service) error {
	containerName := fmt.Sprintf("byteport-%s-%s", service.ProjectName, service.Name)
	commandText := fmt.Sprintf(`docker network create %[1]s 2>$null
docker build --tag %[2]s .
docker rm --force %[3]s 2>$null
docker run --detach --name %[3]s --network %[1]s --restart unless-stopped --publish %[4]d:%[4]d --workdir /app %[2]s
`, dm.networkName, imageTag, containerName, service.Port)

	commandPath := filepath.Join(servicePath, "byteport-docker.ps1")
	return os.WriteFile(commandPath, []byte(commandText), 0644)
}
