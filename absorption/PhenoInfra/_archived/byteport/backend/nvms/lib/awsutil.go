package lib

import (
	"fmt"
	"log"
	"nvms/models"
	"path/filepath"
	"strings"
)

// S3DeploymentInfo contains information about deployed S3 resources
type S3DeploymentInfo struct {
	BucketName  string // Name of the created bucket
	ObjectKey   string // Key of the uploaded object (e.g., "src.zip")
	Region      string // AWS region where bucket was created
	BucketARN   string // ARN of the bucket
	ObjectURL   string // Full URL to access the object
	ContentHash string // SHA256 hash of uploaded content
}

// EC2InstanceInfo contains information about deployed EC2 instances
type EC2InstanceInfo struct {
	InstanceID     string   // EC2 instance ID
	PublicIP       string   // Public IP address
	PrivateIP      string   // Private IP address
	PublicDNS      string   // Public DNS name
	PrivateDNS     string   // Private DNS name
	State          string   // Current instance state
	KeyPairName    string   // Name of the SSH key pair
	SecurityGroups []string // List of security group IDs
	SubnetID       string   // Subnet ID where instance is launched
	Region         string   // AWS region where instance is launched
}
type BuilderReq struct {
	ZipBall     []byte `json:"zipball"`
	AccessKey   string `json:"accessKey"`
	SecretKey   string `json:"secretKey"`
	ProjectName string `json:"projectName"`
}

func getServiceEndpoint(service string) string {
	if AWSEndpointBase == "http://localhost.localstack.cloud:4566" {
		// LocalStack uses a single endpoint for all services
		return AWSEndpointBase
	}
	// AWS uses service-specific endpoints
	return fmt.Sprintf(AWSEndpointBase, service)
}
func DetectBuildPack(files []string, service models.Service) (*models.BuildPack, error) {
	if service.BuildPack != nil {
		fmt.Println("Service has buildpack")
		// check if buildpack has required fields
		if service.BuildPack.Name == "" || len(service.BuildPack.Build) == 0 || service.BuildPack.Start == "" || len(service.BuildPack.Packages) == 0 || len(service.BuildPack.PreBuild) == 0 {
			fmt.Println("Buildpack is missing required parameters")
			return nil, fmt.Errorf("buildpack is missing required parameters")
		}
		return service.BuildPack, nil
	}
	buildpacks := []models.BuildPack{
		{
			Name:        "Spin",
			DetectFiles: []string{"spin.toml"},
			Packages:    []string{"rust", "cargo", "golang", "spin"}, // Base requirements
			PreBuild: []string{
				// Install Spin CLI
				"curl -fsSL https://developer.fermyon.com/downloads/install.sh | bash",
				"mv spin /usr/local/bin/",
				// Set up environment
				"export SPIN_HOME=/root/.spin",
				"mkdir -p $SPIN_HOME",
			},
			Build: []string{
				// Build all components regardless of language
				"spin build",
			},
			Start: "spin up --listen 0.0.0.0", // Expose on port 80
			RuntimeVersions: map[string]string{
				"spin.toml": `spin_version = ["'](\d+\.\d+\.\d+)["']`,
			},
			EnvVars: map[string]string{
				"SPIN_HOME":      "/root/.spin",
				"RUST_BACKTRACE": "1",        // Helpful for debugging
				"GOPATH":         "/root/go", // For Go components
				// Necessary for TinyGo compilation
				"GOROOT":      "/usr/local/go",
				"TINYGO_ROOT": "/usr/local/tinygo",
			},
		},
		{
			Name:        "Go",
			DetectFiles: []string{"go.mod", "go.sum"},
			Packages:    []string{"golang"},
			PreBuild: []string{
				"export HOME=/root",
				"export XDG_CACHE_HOME=/root/go",
				"export GOCACHE=/root/go/cache",
				"export GOPATH=/root/go",
				"export GOMODCACHE=$GOPATH/pkg/mod",
				"mkdir -p $GOPATH",
				"mkdir -p $GOCACHE",
				"mkdir -p $XDG_CACHE_HOME",
			},
			Build: []string{
				"go mod download",
				"go build -o app",
			},
			Start: "/app/$EXTRACT_DIR/$SERVICE_PATH/app",
			RuntimeVersions: map[string]string{
				"go.mod": `go (\d+\.\d+)`, // Regex to extract version
			},
			EnvVars: map[string]string{
				"GOPATH":         "/root/go",
				"GOMODCACHE":     "/root/go/pkg/mod",
				"GOCACHE":        "/root/go/cache",
				"HOME":           "/root",
				"XDG_CACHE_HOME": "/root/go",
			},
		},
		{
			Name:        "Node.js",
			DetectFiles: []string{"package.json", "yarn.lock", "npm-shrinkwrap.json"},
			Packages:    []string{"nodejs", "npm"},
			PreBuild: []string{
				"npm install -g rollup",
				"npm install -g yarn", // If yarn.lock exists
				// Suppress npm update notification
				"npm config set update-notifier false",
			},
			Build: []string{
				"npm install",
				"npm run build",
			},
			Start: "npm start",
			RuntimeVersions: map[string]string{
				"package.json": `"node": "(\d+\.\d+\.\d+)"`,
				".nvmrc":       `^v?(\d+\.\d+\.\d+)$`,
			},
			EnvVars: map[string]string{
				//"NPM_CONFIG_PRODUCTION": "true",
				//"NODE_ENV": "production",
				// Suppress npm update messages
				"NO_UPDATE_NOTIFIER": "1",
			},
		},
		{
			Name:        "Python",
			DetectFiles: []string{"requirements.txt", "Pipfile", "pyproject.toml"},
			Packages:    []string{"python3", "python3-pip", "python3-venv"},
			PreBuild: []string{
				"python3 -m venv venv",
				"source venv/bin/activate",
			},
			Build: []string{
				"pip install -r requirements.txt",
			},
			Start: "python app.py",
			RuntimeVersions: map[string]string{
				"runtime.txt": `python-(\d+\.\d+\.\d+)`,
				"Pipfile":     `python_version = "(\d+\.\d+)"`,
			},
			EnvVars: map[string]string{
				"PYTHONPATH": "/app",
			},
		},
		{
			Name:        "Java",
			DetectFiles: []string{"pom.xml", "build.gradle", ".mvn"},
			Packages:    []string{"java-11-openjdk", "maven"},
			PreBuild:    []string{},
			Build: []string{
				"mvn clean install",
			},
			Start: "java -jar target/*.jar",
			RuntimeVersions: map[string]string{
				"system.properties": `java.runtime.version=(\d+)`,
			},
			EnvVars: map[string]string{
				"JAVA_OPTS": "-Xmx300m -Xss512k -XX:CICompilerCount=2",
			},
		},
		{
			Name:        "Ruby",
			DetectFiles: []string{"Gemfile", "config.ru", "Rakefile"},
			Packages:    []string{"ruby", "ruby-devel", "gcc", "make"},
			PreBuild: []string{
				"gem install bundler",
			},
			Build: []string{
				"bundle install",
			},
			Start: "bundle exec ruby app.rb",
			RuntimeVersions: map[string]string{
				"Gemfile":       `ruby ['\"](\d+\.\d+\.\d+)['\"]`,
				".ruby-version": `^(\d+\.\d+\.\d+)`,
			},
			EnvVars: map[string]string{
				"RACK_ENV": "production",
			},
		},
		{
			Name:        "PHP",
			DetectFiles: []string{"composer.json", "index.php", "artisan"},
			Packages:    []string{"php", "php-fpm", "php-mysql", "composer"},
			PreBuild:    []string{},
			Build: []string{
				"composer install --no-dev",
			},
			Start: "php-fpm",
			RuntimeVersions: map[string]string{
				"composer.json": `"php": ["']>=?(\d+\.\d+)`,
			},
			EnvVars: map[string]string{
				"PHP_FPM_PM": "dynamic",
			},
		},
		{
			Name:        "Rust",
			DetectFiles: []string{"Cargo.toml", "Cargo.lock"},
			Packages:    []string{"rust", "cargo"},
			PreBuild:    []string{},
			Build: []string{
				"cargo build --release",
			},
			Start: "./target/release/app",
			RuntimeVersions: map[string]string{
				"rust-toolchain.toml": `channel = ["'](\d+\.\d+)["']`,
			},
			EnvVars: map[string]string{
				"RUST_BACKTRACE": "1",
			},
		},
	}
	fmt.Println("Checking buildpacks")
	tree, rootDir, err := AnalyzeBuildpackPaths(files)
	if err != nil {
		fmt.Println("Error analyzing buildpack paths: ", err)
		return nil, err
	}

	// Check files in memory instead of on disk
	for _, bp := range buildpacks {
		if matchesBuildpackInMemory(tree, bp.DetectFiles, service.Path, rootDir) {
			return &bp, nil
		}
	}
	fmt.Println("No buildpack detected")

	return nil, fmt.Errorf("no buildpack detected for provided files")
}
func matchesBuildpackInMemory(tree map[string][]string, detectFiles []string, servicePath string, rootDir string) bool {
	normalizedPath := filepath.Base(strings.Trim(servicePath, "/")) // Get just 'backend' or 'frontend'
	//fmt.Printf("Checking buildpacks for path: %s\n", normalizedPath)
	//fmt.Printf("Files to detect: %v\n", detectFiles)
	//fmt.Printf("Tree: %+v\n", tree)

	// Get files in the service directory
	dirFiles, exists := tree[normalizedPath]
	if !exists {
		fmt.Printf("Directory %s not found in tree\n", normalizedPath)
		return false
	}

	//fmt.Printf("Files in %s: %v\n", normalizedPath, dirFiles)

	// Check each detect file
	for _, file := range detectFiles {
		for _, f := range dirFiles {
			if f == file {
				fmt.Printf("Found matching file %s in %s\n", file, normalizedPath)
				return true
			}
		}
	}

	fmt.Printf("No matching files found in %s\n", normalizedPath)
	return false
}
func AnalyzeBuildpackPaths(paths []string) (map[string][]string, string, error) {
	// Extract root directory
	rootDir := findCommonPrefix(paths)
	if rootDir == "" {
		return nil, "", fmt.Errorf("no common root directory found")
	}

	// Create file tree
	tree := make(map[string][]string)
	for _, path := range paths {
		relativePath := strings.TrimPrefix(path, rootDir)
		dir := filepath.Dir(relativePath)
		tree[dir] = append(tree[dir], filepath.Base(relativePath))
	}

	return tree, rootDir, nil
}

func findCommonPrefix(paths []string) string {
	if len(paths) == 0 {
		return ""
	}

	prefix := paths[0]
	for _, path := range paths[1:] {
		for !strings.HasPrefix(path, prefix) {
			prefix = prefix[:strings.LastIndex(prefix, "/")]
		}
	}
	return prefix
}
func GetAWSCredentials(user models.User) (string, string, error) {
	eAccKey := user.AwsCreds.AccessKeyID
	eSecKey := user.AwsCreds.SecretAccessKey

	accesskey, err := DecryptSecret(eAccKey)
	if err != nil {

		return "", "", fmt.Errorf("Error decrypting access key")
	}
	secretkey, err := DecryptSecret(eSecKey)
	if err != nil {

		return "", "", fmt.Errorf("Error decrypting secret key")
	}
	return accesskey, secretkey, nil

}
