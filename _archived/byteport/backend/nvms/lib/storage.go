// lib/storage.go - Local storage management for BytePort Windows
package lib

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/google/uuid"
)

type StorageManager struct {
	basePath string
	mutex    sync.RWMutex
}

type LocalStorageInfo struct {
	Path       string `json:"path"`
	ProjectID  string `json:"project_id"`
	BucketARN  string `json:"bucket_arn"`  // For compatibility
	Region     string `json:"region"`      // For compatibility
	BucketName string `json:"bucket_name"` // For compatibility
}

var storageManagerInstance *StorageManager
var storageManagerOnce sync.Once

func GetStorageManager() (*StorageManager, error) {
	var err error
	storageManagerOnce.Do(func() {
		basePath := os.Getenv("PROJECTS_PATH")
		if basePath == "" {
			basePath = "C:\\BytePort\\projects"
		}
		storageManagerInstance, err = NewStorageManager(basePath)
	})
	return storageManagerInstance, err
}

func NewStorageManager(basePath string) (*StorageManager, error) {
	sm := &StorageManager{
		basePath: basePath,
	}

	// Ensure base directory exists
	err := os.MkdirAll(basePath, 0755)
	if err != nil {
		return nil, fmt.Errorf("failed to create base directory: %w", err)
	}

	return sm, nil
}

// PushToLocalStorage - Replaces PushToS3 for local storage
func (sm *StorageManager) PushToLocalStorage(zipBall []byte, projectName string) (LocalStorageInfo, error) {
	sm.mutex.Lock()
	defer sm.mutex.Unlock()

	fmt.Println("Storing project locally...")

	// Create unique project directory
	projectID := uuid.New().String()
	projectPath := filepath.Join(sm.basePath, fmt.Sprintf("%s-%s", projectName, projectID))

	err := os.MkdirAll(projectPath, 0755)
	if err != nil {
		return LocalStorageInfo{}, fmt.Errorf("failed to create project directory: %w", err)
	}

	// Extract zip file to project directory
	err = sm.extractZip(zipBall, projectPath)
	if err != nil {
		return LocalStorageInfo{}, fmt.Errorf("failed to extract project files: %w", err)
	}

	fmt.Println("Project stored locally at:", projectPath)

	return LocalStorageInfo{
		Path:       projectPath,
		ProjectID:  projectID,
		BucketARN:  projectPath,                                  // For compatibility
		Region:     "local",                                      // For compatibility
		BucketName: fmt.Sprintf("%s-%s", projectName, projectID), // For compatibility
	}, nil
}

func (sm *StorageManager) extractZip(zipData []byte, destPath string) error {
	reader, err := zip.NewReader(bytes.NewReader(zipData), int64(len(zipData)))
	if err != nil {
		return fmt.Errorf("failed to create zip reader: %w", err)
	}

	for _, file := range reader.File {
		// Clean the file path to prevent directory traversal
		cleanPath := filepath.Clean(file.Name)
		if strings.Contains(cleanPath, "..") {
			continue // Skip files with .. in path
		}

		destFile := filepath.Join(destPath, cleanPath)

		// Create directory if needed
		if file.FileInfo().IsDir() {
			err := os.MkdirAll(destFile, file.FileInfo().Mode())
			if err != nil {
				return fmt.Errorf("failed to create directory %s: %w", destFile, err)
			}
			continue
		}

		// Create parent directory
		err := os.MkdirAll(filepath.Dir(destFile), 0755)
		if err != nil {
			return fmt.Errorf("failed to create parent directory for %s: %w", destFile, err)
		}

		// Extract file
		err = sm.extractFile(file, destFile)
		if err != nil {
			return fmt.Errorf("failed to extract file %s: %w", file.Name, err)
		}
	}

	return nil
}

func (sm *StorageManager) extractFile(file *zip.File, destPath string) error {
	rc, err := file.Open()
	if err != nil {
		return err
	}
	defer rc.Close()

	outFile, err := os.OpenFile(destPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, file.FileInfo().Mode())
	if err != nil {
		return err
	}
	defer outFile.Close()

	_, err = io.Copy(outFile, rc)
	return err
}

func (sm *StorageManager) RemoveProject(projectName string) error {
	sm.mutex.Lock()
	defer sm.mutex.Unlock()

	// Find and remove all directories that start with the project name
	entries, err := os.ReadDir(sm.basePath)
	if err != nil {
		return fmt.Errorf("failed to read base directory: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() && strings.HasPrefix(entry.Name(), projectName+"-") {
			projectPath := filepath.Join(sm.basePath, entry.Name())
			err := os.RemoveAll(projectPath)
			if err != nil {
				fmt.Printf("Warning: failed to remove project directory %s: %v\n", projectPath, err)
			} else {
				fmt.Printf("Removed project directory: %s\n", projectPath)
			}
		}
	}

	return nil
}

func (sm *StorageManager) GetProjectPath(projectName, projectID string) string {
	return filepath.Join(sm.basePath, fmt.Sprintf("%s-%s", projectName, projectID))
}

func (sm *StorageManager) ListProjects() ([]string, error) {
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()

	entries, err := os.ReadDir(sm.basePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read base directory: %w", err)
	}

	var projects []string
	for _, entry := range entries {
		if entry.IsDir() {
			projects = append(projects, entry.Name())
		}
	}

	return projects, nil
}

func (sm *StorageManager) ProjectExists(projectName, projectID string) bool {
	projectPath := sm.GetProjectPath(projectName, projectID)
	_, err := os.Stat(projectPath)
	return !os.IsNotExist(err)
}

func (sm *StorageManager) GetProjectSize(projectName, projectID string) (int64, error) {
	projectPath := sm.GetProjectPath(projectName, projectID)

	var size int64
	err := filepath.Walk(projectPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			size += info.Size()
		}
		return nil
	})

	return size, err
}

func (sm *StorageManager) CreateBackup(projectName, projectID string) (string, error) {
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()

	projectPath := sm.GetProjectPath(projectName, projectID)
	if _, err := os.Stat(projectPath); os.IsNotExist(err) {
		return "", fmt.Errorf("project not found: %s", projectPath)
	}

	// Create backup directory
	backupDir := filepath.Join(sm.basePath, "backups")
	err := os.MkdirAll(backupDir, 0755)
	if err != nil {
		return "", fmt.Errorf("failed to create backup directory: %w", err)
	}

	// Create backup zip file
	backupFile := filepath.Join(backupDir, fmt.Sprintf("%s-%s-backup.zip", projectName, projectID))

	err = sm.createZipArchive(projectPath, backupFile)
	if err != nil {
		return "", fmt.Errorf("failed to create backup archive: %w", err)
	}

	return backupFile, nil
}

func (sm *StorageManager) createZipArchive(sourcePath, destPath string) error {
	zipFile, err := os.Create(destPath)
	if err != nil {
		return err
	}
	defer zipFile.Close()

	zipWriter := zip.NewWriter(zipFile)
	defer zipWriter.Close()

	return filepath.Walk(sourcePath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Skip directories
		if info.IsDir() {
			return nil
		}

		// Get relative path
		relPath, err := filepath.Rel(sourcePath, path)
		if err != nil {
			return err
		}

		// Create zip file header
		header, err := zip.FileInfoHeader(info)
		if err != nil {
			return err
		}
		header.Name = filepath.ToSlash(relPath)

		// Create writer for file
		writer, err := zipWriter.CreateHeader(header)
		if err != nil {
			return err
		}

		// Copy file content
		file, err := os.Open(path)
		if err != nil {
			return err
		}
		defer file.Close()

		_, err = io.Copy(writer, file)
		return err
	})
}

// Compatibility function to match existing S3 interface
func PushToS3(zipBall []byte, accessKey, secretKey, projectName string) (LocalStorageInfo, error) {
	sm, err := GetStorageManager()
	if err != nil {
		return LocalStorageInfo{}, err
	}
	return sm.PushToLocalStorage(zipBall, projectName)
}

// Type alias for compatibility
type S3DeploymentInfo = LocalStorageInfo
