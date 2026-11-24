/***
 *  YAML NVMS FORMAT
 *  NVMS Acts as a AWS Parse layer that uses resources from your git repo and information in this config to deploy reproducible apps of any size in efficient microvms
 *  For a typical config we have the following syntax'
 *  To start off we need the base image, you should always use a :minimal variant to get the full benefits of the microvm
 *  Then You'll name the whole project, this is the name of the project that will be used in the AWS Console
 *  Next we'll define services, these can be split by the actual services of your project (e.g. frontend, backend, etc), with different configs for each to allow concurrent deployment
 *  Each one requires a path to the service, a build script / command, a port, and environment variables (optional)
 *  We also have present scalability rules, (Min, MAx, CPU Threshold, Memory Threshold) that will allow you to set a range of resources and a threshold to increment(decr = thresh/2)
 *  If you have a distributed system you'll need to additionally configur a cluster, this will allow you to deploy multiple instances of the same service on different microvms
 *  furtherore we can directly specify our entire aws infra through the SERVICES: section incl MODE and Engine (e.g. ECS, EKS, etc) to allow for a more complex deployment, 
 *  Network options while mostly self contained are also present to allow for more complex networking options
 *  AWS Service Config
 *  Type, This is the specvific service that we are using
 *  Name, This is the name of the service
 * Engine, This is the engine that we are using
 * Mode: This is the mode that we are using cluster is typically uncommon unless you're building a distributed system
 */
use std::collections::HashMap;
use yaml2::Yaml;
use thiserror::Error;
use std::str::FromStr;
#[derive(Error, Debug)]
pub enum NVMSError {
    #[error("YAML parsing error: {0}")]
    YamlError(String),
    #[error("Missing required field: {0}")]
    MissingField(String),
    #[error("Invalid value for field {field}: {message}")]
    InvalidValue {
        field: String,
        message: String,
    },
}

// Core Types
#[derive(Debug, Clone)]
pub struct ResourceSize {
    pub size: u32,
    pub unit: ResourceUnit,
}

#[derive(Debug, Clone)]
pub enum ResourceUnit {
    GB,
    MB,
    KB,
}

#[derive(Debug, Clone)]
pub struct ScaleRange {
    pub min: u32,
    pub max: u32,
}

// Main Configuration
#[derive(Debug)]
pub struct NVMS {
    pub from: String,
    pub name: String,
    pub services: Option<HashMap<String, ServiceConfig>>,
    pub cluster: Option<HashMap<String, ClusterConfig>>,
    pub aws: Option<AWSConfig>,
    pub network: Option<NetworkConfig>,
    pub scale: Option<HashMap<String, ScaleConfig>>,
    pub monitoring: Option<MonitoringConfig>,
    pub backup: Option<BackupConfig>,
}

// Service Configurations
#[derive(Debug)]
pub struct ServiceConfig {
    pub path: String,
    pub build: BuildCommand,
    pub port: Option<u16>,
    pub env: Option<HashMap<String, ConfigValue>>,
    pub resources: Option<ResourceConfig>,
}

#[derive(Debug)]
pub enum BuildCommand {
    Single(String),
    Multiple(Vec<String>),
}

#[derive(Debug)]
pub struct ClusterConfig {
    pub instances: ScaleRange,
    pub path: String,
    pub build: BuildCommand,
    pub scale: Option<ScaleRules>,
    pub resources: Option<ResourceConfig>,
}

#[derive(Debug)]
pub struct ScaleRules {
    pub cpu_threshold: Option<f32>,
    pub memory_threshold: Option<f32>,
    pub queue_threshold: Option<u32>,
    pub connection_count: Option<u32>,
    pub player_count: Option<u32>,
    pub message_rate: Option<u32>,
    pub gpu_utilization: Option<f32>,
    pub latency_threshold: Option<String>,
}

// Resource Configuration
#[derive(Debug)]
pub struct ResourceConfig {
    pub cpu: u32,
    pub memory: ResourceSize,
    pub storage: Option<ResourceSize>,
    pub gpu: Option<bool>,
}

// AWS Configuration
#[derive(Debug)]
pub struct AWSConfig {
    pub region: String,
    pub services: Vec<AWSService>,
}

#[derive(Debug)]
pub enum AWSService {
    RDS(RDSConfig),
    ElastiCache(ElastiCacheConfig),
    SQS(SQSConfig),
    S3(S3Config),
    DynamoDB(DynamoDBConfig),
    OpenSearch(OpenSearchConfig),
    MSK(MSKConfig),
    Lambda(LambdaConfig),
    SageMaker(SageMakerConfig),
}

#[derive(Debug)]
pub struct RDSConfig {
    pub name: Option<String>,
    pub engine: String,
    pub mode: ServiceMode,
    pub size: Option<String>,
    pub replicas: Option<u32>,
}

#[derive(Debug)]
pub enum ServiceMode {
    Single,
    Cluster,
}

#[derive(Debug)]
pub struct DynamoDBConfig {
    pub tables: Vec<DynamoDBTable>,
}

#[derive(Debug)]
pub struct DynamoDBTable {
    pub name: String,
    pub rcu: Option<u32>,
    pub wcu: Option<u32>,
}

// Network Configuration
#[derive(Debug)]
pub struct NetworkConfig {
    pub domain: Option<String>,
    pub ssl: bool,
    pub load_balancer: Option<LoadBalancerConfig>,
    pub cdn: Option<CDNConfig>,
    pub security: SecurityConfig,
}

#[derive(Debug)]
pub struct LoadBalancerConfig {
    pub lb_type: LoadBalancerType,
    pub ssl: bool,
}

#[derive(Debug)]
pub enum LoadBalancerType {
    ALB,
    NLB,
}

#[derive(Debug)]
pub struct CDNConfig {
    pub enabled: bool,
    pub cache_policy: Option<String>,
}

#[derive(Debug)]
pub struct SecurityConfig {
    pub vpc: bool,
    pub private_subnets: bool,
    pub waf: Option<bool>,
    pub ddos_protection: Option<bool>,
    pub rules: Option<SecurityRules>,
}

#[derive(Debug)]
pub struct SecurityRules {
    pub inbound: Option<Vec<String>>,
    pub outbound: Option<Vec<String>>,
    pub latency_threshold: Option<String>,
}

// Monitoring Configuration
#[derive(Debug)]
pub struct MonitoringConfig {
    pub metrics: Vec<String>,
    pub alerts: Vec<AlertConfig>,
}

#[derive(Debug)]
pub struct AlertConfig {
    pub alert_type: String,
    pub threshold: ConfigValue,
    pub window: String,
}

// Backup Configuration
#[derive(Debug)]
pub struct BackupConfig {
    pub enabled: bool,
    pub retention: String,
    pub schedule: String,
}

// Scale Configuration
#[derive(Debug)]
pub struct ScaleConfig {
    pub min: u32,
    pub max: u32,
    pub cpu_threshold: Option<f32>,
    pub memory_threshold: Option<f32>,
    pub queue_threshold: Option<u32>,
}

// Config Value handling
#[derive(Debug, Clone)]
pub enum ConfigValue {
    String(String),
    Number(f64),
    EnvRef(String),
    AWSRef { service: String, resource: String },
}

// Reference parsing
impl FromStr for ConfigValue {
    type Err = NVMSError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        if s.starts_with("${env:") {
            let var = s.trim_start_matches("${env:")
                      .trim_end_matches("}");
            Ok(ConfigValue::EnvRef(var.to_string()))
        } else if s.starts_with("${aws:") {
            let parts: Vec<&str> = s.trim_start_matches("${aws:")
                                   .trim_end_matches("}")
                                   .split(':')
                                   .collect();
            if parts.len() != 2 {
                return Err(NVMSError::InvalidValue {
                    field: "aws_ref".to_string(),
                    message: "Invalid AWS reference format".to_string(),
                });
            }
            Ok(ConfigValue::AWSRef {
                service: parts[0].to_string(),
                resource: parts[1].to_string(),
            })
        } else {
            Ok(ConfigValue::String(s.to_string()))
        }
    }
}
fn locateNVMS(path: String) -> String {
    // Locate nvms.yaml in targetDirectory
    
    todo!()
}