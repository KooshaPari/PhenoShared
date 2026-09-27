package models

/*
	A Basic NVMS IAC Config to run say FixIt (Svelte/Gin) we'd need 2 running services for our system to function, actually, ideally 3. Our frontend hosted on an open public port, our backend similarly, and our postgres privately. We want to host all of this on a single microvm instance wherever compute is needed,

and moreover this configuration needs to be such that any other program with the same file structure and build commands could theoretically be deployed on aws via this file, as such this config also needs to directly map to the aws services we need so that each application is fully configured on deploy.

Fixit is a todolist app built on svelte, gin, and a sqlite DB (postgres in byteport)
This is a basic crud app with a minimal ui letting us statically build it, and our backend does not require persistence, which is left to our postgres instance.
As such if we wanted to deploy we would need a firecracker mvm, and a postgres instance alone, with network and security configs declaring our connections between them and end users.

firecracker actions are assumed to be handled by byteport,
(there is the question of when to prefer more mvms when services require more compute or isolation etc, this may be created as an extra spec)

# This is very much a WIP configuration

As a result we would need to provide the following in our config, a header with mostly identifying/descriptive info, a declaration of each service with its path build com and port, as well as env vars.
After this your AWSConfig declaring needed services outside of mvms, and the netsec config.
*/
type BuildPack struct {
	Name            string            `yaml:"NAME"`                       // Name of the buildpack
	DetectFiles     []string          `yaml:"DETECT_FILES,omitempty"`     // Files that indicate this buildpack should be used
	Packages        []string          `yaml:"PACKAGES"`                   // System packages needed
	PreBuild        []string          `yaml:"PRE_BUILD"`                  // Commands to run before building
	Build           []string          `yaml:"BUILD"`                      // Build commands
	Start           string            `yaml:"START"`                      // Command to start the application
	RuntimeVersions map[string]string `yaml:"RUNTIME_VERSIONS,omitempty"` // Maps language version files to install commands
	EnvVars         map[string]string `yaml:"ENV_VARS"`                   // Required environment variables
}
type NVMS struct {
	Name        string    `yaml:"NAME"`
	Description string    `yaml:"DESCRIPTION"`
	Services    []Service `yaml:"SERVICES"`
	//AWS      AWSConfig
}
type Service struct {
	Name      string            `yaml:"NAME"`
	Path      string            `yaml:"PATH"`
	Port      int               `yaml:"PORT"`
	Build     []string          `yaml:"BUILD,omitempty"`     // Keep for custom build overrides
	Env       map[string]string `yaml:"ENV,omitempty"`       // Additional environment variables
	BuildPack *BuildPack        `yaml:"BUILDPACK,omitempty"` // Optional, will use auto-detection if not specified
	Runtime   string            `yaml:"RUNTIME,omitempty"`   // Optional version override
}
type AWSConfig struct {
	Region   string
	Services []AWSServiceConfig
}
type AWSServiceConfig struct {
	Type       string
	Engine     string
	Mode       string
	Replicas   int
	Size       string
	Name       string
	Partitions int
}

type AWSResource struct {
	ID         string                   `json:"id"`
	Type       string                   `json:"type"` // e.g., "ec2", "alb", "targetgroup"
	Name       string                   `json:"name"`
	ARN        string                   `json:"arn"`
	Status     string                   `json:"status"`
	Region     string                   `json:"region"`
	Tags       map[string]string        `json:"tags"`
	Properties map[string]interface{}   `json:"properties"`
	Associates []AWSResourceAssociation `json:"associates"`
	Service    string                   `json:"service"`
}

type AWSResourceAssociation struct {
	ResourceID string `json:"resource_id"`
	Type       string `json:"type"` // e.g., "attachment", "dependency"
	Role       string `json:"role"` // e.g., "target", "source"
}
