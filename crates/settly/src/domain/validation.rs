//! Configuration validation.

use super::config::{Config, ConfigValue};
use super::errors::ConfigError;

/// Validation rule.
pub trait Validator: Send + Sync {
    /// Validate a configuration.
    fn validate(&self, config: &Config) -> Result<(), ConfigError>;

    /// Get the validator name.
    fn name(&self) -> &str;
}

/// Required key validator.
pub struct RequiredKeys {
    keys: Vec<String>,
}

impl RequiredKeys {
    pub fn new(keys: Vec<String>) -> Self {
        Self { keys }
    }
}

impl Validator for RequiredKeys {
    fn validate(&self, config: &Config) -> Result<(), ConfigError> {
        for key in &self.keys {
            if !config.contains_key(key) {
                return Err(ConfigError::ValidationFailed {
                    validator: self.name().to_string(),
                    message: format!("Missing required key: {key}"),
                });
            }
        }
        Ok(())
    }

    fn name(&self) -> &str {
        "required_keys"
    }
}

/// Type validator.
pub struct TypeValidator {
    key: String,
    expected_type: &'static str,
}

impl TypeValidator {
    pub fn new(key: impl Into<String>, expected_type: &'static str) -> Self {
        Self { key: key.into(), expected_type }
    }
}

impl Validator for TypeValidator {
    fn validate(&self, config: &Config) -> Result<(), ConfigError> {
        let value = config.get(&self.key).ok_or_else(|| ConfigError::ValidationFailed {
            validator: self.name().to_string(),
            message: format!("Key not found: {}", self.key),
        })?;

        let actual_type = match value {
            ConfigValue::Null => "null",
            ConfigValue::Bool(_) => "bool",
            ConfigValue::Number(_) => "number",
            ConfigValue::String(_) => "string",
            ConfigValue::Array(_) => "array",
            ConfigValue::Object(_) => "object",
        };

        if actual_type != self.expected_type {
            return Err(ConfigError::ValidationFailed {
                validator: self.name().to_string(),
                message: format!(
                    "Type mismatch for {key}: expected {expected}, got {actual}",
                    key = self.key,
                    expected = self.expected_type,
                    actual = actual_type
                ),
            });
        }

        Ok(())
    }

    fn name(&self) -> &str {
        "type_validator"
    }
}

/// Range validator for numbers.
pub struct RangeValidator {
    key: String,
    min: Option<f64>,
    max: Option<f64>,
}

impl RangeValidator {
    pub fn new(key: impl Into<String>) -> Self {
        Self { key: key.into(), min: None, max: None }
    }

    pub fn with_min(mut self, min: f64) -> Self {
        self.min = Some(min);
        self
    }

    pub fn with_max(mut self, max: f64) -> Self {
        self.max = Some(max);
        self
    }
}

impl Validator for RangeValidator {
    fn validate(&self, config: &Config) -> Result<(), ConfigError> {
        let value = config.get(&self.key).ok_or_else(|| ConfigError::ValidationFailed {
            validator: self.name().to_string(),
            message: format!("Key not found: {}", self.key),
        })?;

        let num = match value {
            ConfigValue::Number(n) => *n,
            _ => {
                return Err(ConfigError::ValidationFailed {
                    validator: self.name().to_string(),
                    message: format!("Expected number for {}", self.key),
                })
            }
        };

        if let Some(min) = self.min {
            if num < min {
                return Err(ConfigError::ValidationFailed {
                    validator: self.name().to_string(),
                    message: format!("{key} must be >= {min}", key = self.key),
                });
            }
        }

        if let Some(max) = self.max {
            if num > max {
                return Err(ConfigError::ValidationFailed {
                    validator: self.name().to_string(),
                    message: format!("{key} must be <= {max}", key = self.key),
                });
            }
        }

        Ok(())
    }

    fn name(&self) -> &str {
        "range_validator"
    }
}

/// Composite validator - runs multiple validators.
pub struct CompositeValidator {
    validators: Vec<Box<dyn Validator>>,
}

impl CompositeValidator {
    pub fn new() -> Self {
        Self { validators: Vec::new() }
    }

    pub fn push<V: Validator + 'static>(mut self, validator: V) -> Self {
        self.validators.push(Box::new(validator));
        self
    }
}

impl Default for CompositeValidator {
    fn default() -> Self {
        Self::new()
    }
}

impl Validator for CompositeValidator {
    fn validate(&self, config: &Config) -> Result<(), ConfigError> {
        for validator in &self.validators {
            validator.validate(config)?;
        }
        Ok(())
    }

    fn name(&self) -> &str {
        "composite"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_required_keys() {
        let validator = RequiredKeys::new(vec!["a".to_string(), "b".to_string()]);

        let mut config = Config::new();
        config.set("a", 1);

        assert!(validator.validate(&config).is_err());

        config.set("b", 2);
        assert!(validator.validate(&config).is_ok());
    }

    #[test]
    fn test_range_validator() {
        let validator = RangeValidator::new("port").with_min(1.0).with_max(65535.0);

        let mut config = Config::new();
        config.set("port", 8080);
        assert!(validator.validate(&config).is_ok());

        config.set("port", 0);
        assert!(validator.validate(&config).is_err());

        config.set("port", 70000);
        assert!(validator.validate(&config).is_err());
    }
}
