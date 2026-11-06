"""YAML validator using PyYAML and JSON Schema"""
import yaml
import json
from .json_validator import JsonSchemaValidator, ValidationResult

class YamlValidator:
    """YAML validator that converts to JSON for validation"""
    
    def __init__(self, json_validator: JsonSchemaValidator = None):
        self._json_validator = json_validator or JsonSchemaValidator()
    
    def validate(self, schema: str, document: str) -> ValidationResult:
        """Validate YAML document against JSON schema"""
        try:
            # Parse YAML
            yaml_obj = yaml.safe_load(document)
            # Convert to JSON
            json_str = json.dumps(yaml_obj)
            # Validate
            return self._json_validator.validate(schema, json_str)
        except yaml.YAMLError as e:
            return ValidationResult(False, [f"Invalid YAML: {e}"])
    
    def add_schema(self, name: str, schema_content: str) -> None:
        """Add a named schema"""
        self._json_validator.add_schema(name, schema_content)
